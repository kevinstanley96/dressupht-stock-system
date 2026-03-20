here is my sidebar.py

import streamlit as st
import pandas as pd
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
        file_cv = st.file_uploader(
            "Upload Canape-Vert file",
            type=["xlsx"],
            key="file_cv_uploader"
        )
        
        file_pv = st.file_uploader(
            "Upload PV file",
            type=["xlsx"],
            key="file_pv_uploader"
        )

        if file_cv and file_pv:
            combined_df = clean_and_combine(file_cv, file_pv)
            st.info("Preview of combined inventory before overwrite:")
            st.dataframe(combined_df.head(20), key="preview_combined_df")

        if st.button("🚀 Overwrite & Sync", use_container_width=True, key="overwrite_sync_btn") and file_cv and file_pv:
            try:
                progress = st.progress(0)
                progress.progress(20)

                # Combine and clean
                combined_df = clean_and_combine(file_cv, file_pv)
                progress.progress(40)

                # 🔧 Drop unwanted columns like 'Unnamed: 0'
                drop_cols = [c for c in combined_df.columns if c not in [
                    "SKU", "Full Name", "Category", "Stock", "Price", "Location", "Token", "square_item_id"
                ]]
                if drop_cols:
                    combined_df = combined_df.drop(columns=drop_cols)

                # Replace NaN with None
                combined_df = combined_df.where(pd.notnull(combined_df), None)

                # Ensure numeric columns are JSON-safe
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
            except Exception as e:
                st.error(f"❌ Error during overwrite & sync: {e}")

    # --- SYNC BUTTONS ---
    st.header("🔄 Inventory Sync")
    
    if st.button("Sync Inventory - Dressupht Pv", key="sync_pv_btn"):
        sync_inventory("Dressupht Pv")
    
    if st.button("Sync Inventory - Canape-Vert", key="sync_cv_btn"):
        sync_inventory("Canape-Vert")

    # --- LOGOUT (always last) ---
    if st.session_state.get("authenticated", False):
        st.divider()
        if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.role = None
            st.session_state.location = None
            st.rerun()
