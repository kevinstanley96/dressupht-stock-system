import streamlit as st
import pandas as pd
import time
from datetime import datetime
from utils.helpers import search_inventory, safe_dataframe

def render_tab(container, supabase, username, role, loc_list, t, master_inventory=None):
    with container:
        st.header(t["mannequin_header"])

        # 1. FETCH MANNEQUIN DATA
        try:
            m_query = supabase.table("Mannequin").select("*").order("Last_Updated", desc=True).execute()
            m_df = pd.DataFrame(m_query.data) if m_query.data else pd.DataFrame()
        except Exception:
            m_df = pd.DataFrame()

        # 2. LOCATION SELECTOR FOR HISTORY VIEW
        st.subheader("Current Wigs on Display")
        if role in ["Admin","Manager"]:
            view_loc = st.selectbox("Select Display Location", ["All","Pv","Canape-Vert"], key="man_hist_loc")
        else:
            view_loc = loc_list[0] if loc_list else None
            if view_loc:
                st.write(f"📍 Viewing Display for: {view_loc}")

        # Compact view toggle
        compact_view = st.checkbox("📱 Compact view (mobile-friendly)", value=False, key="mannequin_compact")

        # Filter history by location
        if not m_df.empty and view_loc:
            if view_loc != "All":
                m_df = m_df[m_df['location'] == view_loc]

            if compact_view:
                # Compact view: only Full Name + Quantity
                safe_dataframe(m_df, ['Full Name','Quantity'], "No wigs currently on display.")
            else:
                # Full view: all details
                safe_dataframe(m_df, ['SKU','Full Name','Quantity','Last_Updated','location'],
                               "No wigs currently on display.")

            st.caption(f"Total Items on Display: {int(m_df['Quantity'].sum())}")
        else:
            st.info("No wigs currently on display.")

        # 3. LOGGING FORM (Admins/Managers only)
        if role in ["Admin","Manager"]:
            st.divider()
            st.subheader("Add/Update Display")

            m_loc = st.selectbox("Select Location for Entry", ["Pv","Canape-Vert"], key="man_entry_loc")

            m_search = st.text_input("🔍 Search Item to Display", placeholder="Type Name or SKU...").lower()
            if m_search and master_inventory is not None:
                match = search_inventory(master_inventory, m_search)
                if not match.empty:
                    m_item = match.iloc[0]
                    st.success(f"Selected: **{m_item['Full Name']}** ({m_item['SKU']})")

                    with st.form("man_form", clear_on_submit=True):
                        m_qty = st.number_input("Quantity", min_value=1, max_value=2, step=1)
                        if st.form_submit_button("🚀 Set on Mannequin"):
                            man_entry = {
                                "SKU": str(m_item['SKU']),
                                "Full Name": str(m_item['Full Name']),
                                "Quantity": int(m_qty),
                                "location": str(m_loc),
                                "Last_Updated": datetime.now().strftime("%Y-%m-%d %H:%M")
                            }
                            supabase.table("Mannequin").delete().eq("SKU", m_item['SKU']).eq("location", m_loc).execute()
                            supabase.table("Mannequin").insert(man_entry).execute()
                            st.success(f"Updated display for {m_item['Full Name']} at {m_loc}!")
                            time.sleep(1); st.rerun()
                else:
                    st.error("No item found in Master Inventory.")
