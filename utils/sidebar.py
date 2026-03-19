import streamlit as st
from datetime import datetime
import pytz
from utils.helpers import clean_and_combine, sync_inventory

haiti_tz = pytz.timezone("America/Port-au-Prince")

def render_sidebar(username, role, loc_list, supabase):
    # --- Show last sync info ---
    last_syncs = supabase.table("sync_log") \
        .select("location, synced_at, type") \
        .order("synced_at", desc=True) \
        .limit(2) \
        .execute()

    if last_syncs.data:
        st.subheader("📊 Last Syncs")
        for entry in last_syncs.data:
            loc = entry.get("location", "Unknown")
            sync_type = entry.get("type", "Unknown")
            sync_time = entry.get("synced_at", "")
            if sync_time:
                sync_time = datetime.fromisoformat(sync_time).astimezone(haiti_tz).strftime("%Y-%m-%d %H:%M:%S")
            st.write(f"**{sync_type}** → {loc} at {sync_time}")
    else:
        st.info("No syncs logged yet.")

    # --- MISE Upload + Overwrite ---
    if role in ["Admin", "Manager"]:
        st.subheader("📂 Upload Square Export Files")
        file_cv = st.file_uploader("Upload Canape-Vert file", type=["xlsx"])
        file_pv = st.file_uploader("Upload Dressupht Pv file", type=["xlsx"])
    
        if file_cv and file_pv:
            combined_df = clean_and_combine(file_cv, file_pv)
            st.info("Preview of combined inventory before overwrite:")
            st.dataframe(combined_df.head(20))
    
        # ✅ Corrected overwrite block
        if st.button("🚀 Overwrite & Sync", use_container_width=True) and file_cv and file_pv:
            progress = st.progress(0)
            progress.progress(20)
    
            # Combine and clean
            combined_df = clean_and_combine(file_cv, file_pv)
            progress.progress(40)
    
            # 🔧 Ensure JSON-safe values
            combined_df = combined_df.where(pd.notnull(combined_df), None)
            for col in ["Stock", "Price"]:
                if col in combined_df.columns:
                    combined_df[col] = combined_df[col].astype(float).astype(object)
    
            records = combined_df.to_dict(orient="records")
    
            # Replace Master_Inventory with fresh data
            supabase.table("Master_Inventory").delete().neq("id", 0).execute()
            progress.progress(60)
    
            supabase.table("Master_Inventory").insert(records).execute()
            progress.progress(80)
    
            # ✅ Log manual sync time
            now_ht = datetime.now(haiti_tz).isoformat()
            supabase.table("sync_log").insert([
                {"location": "Canape-Vert", "synced_at": now_ht, "type": "MISE"},
                {"location": "Dressupht Pv", "synced_at": now_ht, "type": "MISE"}
            ]).execute()
            progress.progress(100)
    
            st.success("✅ Master_Inventory refreshed and manual sync logged.")

    # --- SYNC BUTTONS ---
    st.header("🔄 Inventory Sync")
    if st.button("Sync Inventory - Dressupht Pv"):
        sync_inventory("Dressupht Pv", supabase)
    if st.button("Sync Inventory - Canape-Vert"):
        sync_inventory("Canape-Vert", supabase)

    # --- LOGOUT (always last) ---
    if st.session_state.get("authenticated", False):
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.role = None
            st.session_state.location = None
            st.rerun()
