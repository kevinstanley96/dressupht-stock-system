import streamlit as st
import pandas as pd
import time
from datetime import date
from utils.helpers import search_inventory, safe_dataframe

def render_tab(container, supabase, username, role, loc_list, t):
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

            # Compute running balance per SKU/location
            d_df = d_df.sort_values("Date")
            d_df["Balance"] = d_df.apply(
                lambda row: row["Quantity"] if row["Type"] == "Addition" else -row["Quantity"], axis=1
            )
            d_df["Running Balance"] = d_df.groupby(["SKU","location"])["Balance"].cumsum()

            st.dataframe(
                d_df[['Date','Wig Name','Type','Quantity','User','location','Running Balance']],
                width='stretch', hide_index=True
            )
        else:
            st.info("No activity recorded in the Depot yet.")

        # 3. LOGGING FORM (Admins/Managers only)
        if role in ["Admin","Manager"]:
            st.divider()
            st.subheader("Log Depot Movement")

            d_loc = st.selectbox("Select Location for Entry", ["Pv","Canape-Vert"], key="dep_entry_loc")

            # ✅ Library-style search
            d_search = st.text_input(
                "🔍 Search Item for Depot",
                placeholder="Search by SKU, Name, Token, or Category..."
            ).strip().lower()

            if d_search:
                # Always reload Master_Inventory fresh
                inv_query = supabase.table("Master_Inventory").select("*").execute()
                inv_df = pd.DataFrame(inv_query.data) if inv_query.data else pd.DataFrame()

                match = search_inventory(inv_df, d_search)
                if not match.empty:
                    options = match[['SKU','Full Name']].apply(
                        lambda x: f"{x['SKU']} - {x['Full Name']}", axis=1
                    ).tolist()
                    selected_sku = st.selectbox("Select Item", options).split(" - ")[0]
                    d_item = match[match['SKU'] == selected_sku].iloc[0]
                    st.success(f"Selected: **{d_item['Full Name']}** ({d_item['SKU']})")

                    # Show current depot stock for this SKU/location
                    stock_query = supabase.table("Depot").select("*").eq("SKU", d_item['SKU']).eq("location", d_loc).execute()
                    stock_df = pd.DataFrame(stock_query.data) if stock_query.data else pd.DataFrame()
                    if not stock_df.empty:
                        current_stock = stock_df.apply(
                            lambda row: row["Quantity"] if row["Type"] == "Addition" else -row["Quantity"], axis=1
                        ).sum()
                    else:
                        current_stock = 0
                    st.info(f"📦 Current depot stock for {d_item['Full Name']} at {d_loc}: {current_stock}")

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

                            # Adjust current stock for display
                            new_stock = current_stock + (d_qty if d_type == "Addition" else -d_qty)

                            st.success(
                                f"{d_type} of {d_qty} wigs recorded for {d_item['Full Name']} at {d_loc}. "
                                f"New depot stock: {new_stock}"
                            )
                            time.sleep(1); st.rerun()
                else:
                    st.error("Item not found in inventory.")
