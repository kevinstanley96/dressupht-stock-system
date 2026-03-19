import streamlit as st
import pandas as pd
import time
from datetime import date
from utils.helpers import search_inventory, safe_dataframe

def render_tab(container, supabase, username, role, loc_list, t, master_inventory=None):
    with container:
        st.header(t["depot_header"])

        # 1. FETCH DEPOT DATA
        try:
            d_query = supabase.table("Depot").select("*").order("Date", desc=True).execute()
            d_df = pd.DataFrame(d_query.data) if d_query.data else pd.DataFrame()
        except Exception:
            d_df = pd.DataFrame()

        # 2. LOCATION SELECTOR FOR HISTORY VIEW
        st.subheader("Depot Activity History")
        if role in ["Admin","Manager"]:
            view_loc = st.selectbox("Select Depot Location", ["All","Pv","Canape-Vert"], key="dep_hist_loc")
        else:
            view_loc = loc_list[0] if loc_list else None
            if view_loc:
                st.write(f"📍 Viewing Depot for: {view_loc}")

        # Filter history by location
        if not d_df.empty and view_loc:
            if view_loc != "All":
                d_df = d_df[d_df['location'] == view_loc]
            st.dataframe(d_df[['Date','Wig Name','Type','Quantity','User','location']],
                         width='stretch', hide_index=True)
        else:
            st.info("No activity recorded in the Depot yet.")

        # 3. LOGGING FORM (Admins/Managers only)
        if role in ["Admin","Manager"]:
            st.divider()
            st.subheader("Log Depot Movement")

            d_loc = st.selectbox("Select Location for Entry", ["Pv","Canape-Vert"], key="dep_entry_loc")

            d_search = st.text_input("🔍 Search Item for Depot", placeholder="Search by SKU or Name...").lower()
            if d_search and master_inventory is not None:
                match = search_inventory(master_inventory, d_search)
                if not match.empty:
                    options = match[['SKU','Full Name']].apply(lambda x: f"{x['SKU']} - {x['Full Name']}", axis=1).tolist()
                    selected_sku = st.selectbox("Select Item", options).split(" - ")[0]
                    d_item = match[match['SKU']==selected_sku].iloc[0]
                    st.success(f"Selected: **{d_item['Full Name']}** ({d_item['SKU']})")

                    with st.form("depot_form", clear_on_submit=True):
                        d_type = st.radio("Movement Type", ["Addition","Withdrawal"], horizontal=True)
                        d_qty = st.number_input("Quantity", min_value=1, step=1)
                        d_date = st.date_input("Date", value=date.today())

                        if st.form_submit_button("Confirm Depot Entry"):
                            dep_entry = {
                                "Date": str(d_date),
                                "SKU": str(d_item['SKU']),
                                "Wig Name": str(d_item['Full Name']),
                                "Type": d_type,
                                "Quantity": int(d_qty),
                                "User": username,
                                "location": d_loc
                            }
                            supabase.table("Depot").insert(dep_entry).execute()
                            st.success(f"Recorded {d_type} for {d_item['Full Name']} at {d_loc}")
                            time.sleep(1); st.rerun()
                else:
                    st.error("Item not found in inventory.")
