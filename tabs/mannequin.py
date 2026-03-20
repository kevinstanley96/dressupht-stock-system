import streamlit as st
import pandas as pd
import time
from datetime import datetime
from utils.helpers import search_inventory, safe_dataframe

def render_tab(container, supabase, username, role, loc_list, t):
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
            view_loc = st.selectbox(
                "Select Display Location",
                ["All","Pv","Canape-Vert"],
                key="man_hist_loc"
            )
        else:
            view_loc = loc_list[0] if loc_list else None
            if view_loc:
                st.write(f"📍 Viewing Display for: {view_loc}")

        # Compact view toggle
        compact_view = st.checkbox(
            "📱 Compact view (mobile-friendly)",
            value=False,
            key="man_compact_view"
        )

        # Filter history by location
        if not m_df.empty and view_loc:
            if view_loc != "All":
                m_df = m_df[m_df['location'] == view_loc]

            if compact_view:
                safe_dataframe(m_df, ['Full Name','Quantity'], "No wigs currently on display.")
            else:
                safe_dataframe(m_df, ['SKU','Full Name','Quantity','Last_Updated','location'],
                               "No wigs currently on display.")

            st.caption(f"Total Items on Display: {int(m_df['Quantity'].sum())}")
        else:
            st.info("No wigs currently on display.")

        # 3. LOGGING FORM (Admins/Managers only)
        if role in ["Admin","Manager"]:
            st.divider()
            st.subheader("Add/Update Display")

            m_loc = st.selectbox(
                "Select Location for Entry",
                ["Pv","Canape-Vert"],
                key="man_entry_loc"
            )

            # ✅ Library-style search
            m_search = st.text_input(
                "🔍 Search Item to Display",
                placeholder="Search by SKU, Name, Token, or Category...",
                key="man_search_input"
            ).strip().lower()

            if m_search:
                # Always reload Master_Inventory fresh
                inv_query = supabase.table("Master_Inventory").select("*").execute()
                inv_df = pd.DataFrame(inv_query.data) if inv_query.data else pd.DataFrame()

                match = search_inventory(inv_df, m_search)
                if not match.empty:
                    options = match[['SKU','Full Name']].apply(
                        lambda x: f"{x['SKU']} - {x['Full Name']}", axis=1
                    ).tolist()
                    selected_sku = st.selectbox(
                        "Select Item",
                        options,
                        key="man_item_select"
                    ).split(" - ")[0]
                    m_item = match[match['SKU'] == selected_sku].iloc[0]

                    st.success(f"Selected: **{m_item['Full Name']}** ({m_item['SKU']})")

                    with st.form("man_form", clear_on_submit=True):
                        m_qty = st.number_input("Quantity", min_value=1, max_value=2, step=1, key="man_qty_input")
                        if st.form_submit_button("🚀 Set on Mannequin", key="man_submit_btn"):
                            man_entry = {
                                "SKU": str(m_item['SKU']),
                                "Full Name": str(m_item['Full Name']),
                                "Quantity": int(m_qty),
                                "location": str(m_loc),
                                "Last_Updated": datetime.now().strftime("%Y-%m-%d %H:%M")
                            }
                            # Remove old entry for same SKU/location
                            supabase.table("Mannequin").delete().eq("SKU", m_item['SKU']).eq("location", m_loc).execute()
                            # Insert new entry
                            supabase.table("Mannequin").insert(man_entry).execute()
                            st.success(f"Updated display for {m_item['Full Name']} at {m_loc}!")
                            time.sleep(1); st.rerun()
                else:
                    st.error("No item found in Master Inventory.")
