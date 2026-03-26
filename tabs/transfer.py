import streamlit as st
import pandas as pd
import time
from datetime import date
from utils.helpers import search_inventory

def render_tab(container, supabase, username, role, loc_list, t, master_inventory=None):
    with container:
        st.header("🔄 Transfer to Canape-Vert")

        # --- Transfer history ---
        try:
            t_query = supabase.table("Transfer").select("*").order("Date", desc=True).execute()
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

        # ✅ Reload Master_Inventory fresh from Supabase
        inv_query = supabase.table("Master_Inventory").select("*").execute()
        master_inventory = pd.DataFrame(inv_query.data) if inv_query.data else pd.DataFrame()

        if master_inventory.empty:
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
                            # 1. Log transfer
                            transfer_entry = {
                                "Date": str(t_date),
                                "SKU": str(t_item['SKU']),
                                "Wig Name": str(t_item['Full Name']),
                                "Quantity": int(t_qty),
                                "from_location": "Pv",
                                "to_location": "Canape-Vert",
                                "User": username
                            }
                            supabase.table("Transfer").insert(transfer_entry).execute()

                            # 2. Deduct from PV
                            supabase.table("Master_Inventory").update({
                                "Stock": int(t_item["Stock"]) - t_qty
                            }).eq("SKU", t_item["SKU"]).eq("Location", "Pv").execute()

                            # 3. Add to Canape-Vert
                            cv_query = supabase.table("Master_Inventory").select("*")\
                                .eq("Full Name", t_item["Full Name"])\
                                .eq("Location", "Canape-Vert").execute()
                            cv_data = cv_query.data

                            if cv_data:
                                # Found by name → update stock
                                current_stock = cv_data[0]["Stock"]
                                supabase.table("Master_Inventory").update({
                                    "Stock": current_stock + t_qty
                                }).eq("SKU", cv_data[0]["SKU"]).eq("Location", "Canape-Vert").execute()
                            else:
                                # No match by name → ask user for SKU
                                st.warning("No matching item in Canape-Vert. Please enter the correct SKU.")
                                new_sku = st.text_input("Enter SKU for Canape-Vert", key="cv_sku_input")

                                if new_sku:
                                    new_entry = {
                                        "SKU": new_sku,
                                        "Full Name": t_item["Full Name"],
                                        "Category": t_item["Category"],
                                        "Location": "Canape-Vert",
                                        "Stock": t_qty,
                                        "Price": t_item["Price"]
                                    }
                                    supabase.table("Master_Inventory").insert(new_entry).execute()
                                    st.success(f"Inserted new SKU {new_sku} for {t_item['Full Name']} at Canape-Vert with {t_qty} units.")

                            # 4. Success message
                            st.success(
                                f"Transferred {t_qty} units of {t_item['Full Name']} from PV to Canape-Vert"
                            )
                            time.sleep(1)
                            st.rerun()
                else:
                    st.error("Item not found in PV inventory.")
