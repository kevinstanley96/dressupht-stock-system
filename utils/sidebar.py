import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from utils.helpers import clean_and_combine, sync_inventory
import numpy as np

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

    # --- MISE Upload + Overwrite + Sync (Admin/Manager only) ---
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
        
                # ✅ Sanitize values
                # Replace NaN, inf, -inf with None
                combined_df = combined_df.replace([np.nan, np.inf, -np.inf], None)
        
                # Drop rows with missing SKU (to satisfy NOT NULL constraint)
                combined_df = combined_df.dropna(subset=["SKU"])
        
                # Ensure numeric columns are JSON-safe
                for col in ["Stock", "Price"]:
                    if col in combined_df.columns:
                        combined_df[col] = pd.to_numeric(combined_df[col], errors="coerce").fillna(0).astype(float)
        
                # Convert to records
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

        # --- SYNC BUTTONS (Admin/Manager only) ---
        if role in ["Admin", "Manager"]:
            st.header("🔄 Inventory Sync")
        
            # Manual buttons (still available anytime)
            if st.button("Sync Inventory - Dressupht Pv", key="sync_pv_btn"):
                sync_inventory("Dressupht Pv")
                st.session_state["last_auto_sync"] = datetime.now(haiti_tz)
            if st.button("Sync Inventory - Canape-Vert", key="sync_cv_btn"):
                sync_inventory("Canape-Vert")
                st.session_state["last_auto_sync"] = datetime.now(haiti_tz)
        
            # Ensure session state keys exist
            if "last_auto_sync" not in st.session_state:
                st.session_state["last_auto_sync"] = None
            if "auto_sync_enabled" not in st.session_state:
                st.session_state["auto_sync_enabled"] = True  # default ON
        
            # --- STOP Auto Sync button ---
            if st.button("🛑 STOP Auto Sync", key="stop_auto_sync_btn"):
                st.session_state["auto_sync_enabled"] = False
                st.warning("Auto-sync has been stopped.")
        
            # --- AUTO SYNC EVERY 30 MINUTES (checks on each rerun) ---
            now_ht = datetime.now(haiti_tz)
            last_sync = st.session_state.get("last_auto_sync")
        
            if st.session_state.get("auto_sync_enabled", True):
                if not last_sync or (now_ht - last_sync) >= timedelta(minutes=30):
                    # Run both syncs automatically
                    sync_inventory("Dressupht Pv")
                    sync_inventory("Canape-Vert")
        
                    # Log auto-sync event
                    supabase.table("sync_log").insert([
                        {"location": "Dressupht Pv", "synced_at": now_ht.isoformat(), "type": "AUTO"},
                        {"location": "Canape-Vert", "synced_at": now_ht.isoformat(), "type": "AUTO"}
                    ]).execute()
        
                    st.session_state["last_auto_sync"] = now_ht
                    st.info("✅ Auto-sync triggered (every 30 minutes)")
            else:
                st.info("⏸ Auto-sync is currently disabled.")

    # --- LOGOUT (always last) ---
    if st.session_state.get("authenticated", False):
        st.divider()
        if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.role = None
            st.session_state.location = None
            st.rerun()
