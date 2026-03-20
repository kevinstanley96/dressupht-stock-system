import streamlit as st
import pandas as pd
import time
from datetime import date
from utils.helpers import search_inventory

def render_tab(container, supabase, username, role, loc_list, t, master_inventory=None):
    with tab_dict["Transfer"]:
        st.header("🔄 Transfer to Canape-Vert")

        # --- Transfer history ---
        try:
            t_query = supabase.table("transfer").select("*").order("Date", desc=True).execute()
            t_df = pd.DataFrame(t_query.data) if t_query.data else pd.DataFrame()
        except Exception as e:
            t_df = pd.DataFrame()
            st.error(f"Error loading transfer history: {e}")

        st.subheader("Transfer History")
        if not t_df.empty:
            cols = ["Date", "Wig Name", "Quantity", "from_location", "to_location", "User"]
            st.dataframe(t_df[cols], width="stretch", hide_index=True)
            st.caption(f"Showing {len(t_df)} transfers")
        else:
            st.info("No transfers recorded yet.")

        # --- New transfer form ---
        st.divider()
        st.subheader("Log New Transfer (PV → Canape-Vert)")

        # Ensure master_inventory is loaded
        if master_inventory is None or master_inventory.empty:
            st.error("PV inventory is not loaded yet. Please refresh or sync inventory first.")
        else:
            t_search = st.text_input(
                "🔍 Search PV Inventory",
                placeholder="Search by SKU or Name...",
                key="transfer_search"
            ).lower()

            pv_inventory = master_inventory[master_inventory['Location'] == "Pv"].copy()

            if t_search:
                match = search_inventory(pv_inventory, t_search)
                if not match.empty:
                    options = match[['SKU','Full Name']].apply(
                        lambda x: f"{x['SKU']} - {x['Full Name']}", axis=1
                    ).tolist()
                    selected_sku = st.selectbox("Select Item", options).split(" - ")[0]
                    t_item = match[match['SKU'] == selected_sku].iloc[0]
                    st.success(f"Selected: **{t_item['Full Name']}** ({t_item['SKU']})")

                    with st.form("transfer_form", clear_on_submit=True):
                        t_qty = st.number_input("Quantity to Transfer", min_value=1, step=1)
                        t_date = st.date_input("Date", value=date.today())
                        if st.form_submit_button("Confirm Transfer"):
                            transfer_entry = {
                                "Date": str(t_date),
                                "SKU": str(t_item['SKU']),
                                "Wig Name": str(t_item['Full Name']),
                                "Quantity": int(t_qty),
                                "from_location": "Pv",
                                "to_location": "Canape-Vert",
                                "User": username
                            }
                            supabase.table("transfer").insert(transfer_entry).execute()
                            st.success(
                                f"Transferred {t_qty} units of {t_item['Full Name']} from PV to Canape-Vert"
                            )
                            time.sleep(1)
                            st.rerun()
                else:
                    st.error("Item not found in PV inventory.")
