import streamlit as st
import pandas as pd
import time
from datetime import datetime, date
from utils.helpers import normalize_location, safe_dataframe
from pytz import timezone

haiti_tz = timezone("America/Port-au-Prince")

def render_tab(container, supabase, square_client, username, role, loc_list, t):
    with container:
        # --- TODAY-ONLY SALES ---
        st.header("📊 Sales History (Today Only, Product-Level)")

        try:
            # Get Square locations
            locations_response = square_client.locations.list()
            location_lookup = {loc.id: loc.name for loc in locations_response.locations}
            location_ids = list(location_lookup.keys())

            # Fetch orders
            response = square_client.orders.search(location_ids=location_ids, limit=200)

            if response.orders:
                today = date.today()
                data = []

                for order in response.orders:
                    created_dt = datetime.fromisoformat(order.created_at.replace("Z", "+00:00"))
                    created_dt = created_dt.astimezone(haiti_tz)

                    # Only today's sales
                    if created_dt.date() != today:
                        continue

                    if order.line_items:
                        for item in order.line_items:
                            qty_sold = int(item.quantity)
                            product_name = item.name or ""
                            product_token = item.catalog_object_id

                            # Defaults
                            token = "NO_TOKEN"
                            category = "Unknown"
                            location_name = "Unknown"

                            # Match inventory
                            inv_result = supabase.table("Master_Inventory").select(
                                '"Full Name", SKU, Category, Location, Token'
                            ).eq("Token", product_token).execute()
                            if inv_result.data:
                                inv_info = inv_result.data[0]
                                category = inv_info["Category"]
                                location_name = normalize_location(inv_info["Location"])
                                token = inv_info["Token"]
                            elif product_name.strip():
                                inv_result = supabase.table("Master_Inventory").select(
                                    '"Full Name", SKU, Category, Location, Token'
                                ).eq("Full Name", product_name.strip()).execute()
                                if inv_result.data:
                                    inv_info = inv_result.data[0]
                                    category = inv_info["Category"]
                                    location_name = normalize_location(inv_info["Location"])
                                    token = inv_info["Token"] or "NO_TOKEN"
                                else:
                                    raw_loc = location_lookup.get(order.location_id, "Unknown")
                                    location_name = normalize_location(raw_loc)
                            else:
                                raw_loc = location_lookup.get(order.location_id, "Unknown")
                                location_name = normalize_location(raw_loc)

                            data.append({
                                "Time (Haiti)": created_dt.strftime("%H:%M:%S"),
                                "Location": location_name,
                                "Category": category,
                                "Product": f"{qty_sold} × {product_name if product_name else 'Unknown Product'}",
                                "Token": token,
                                "State": order.state
                            })

                if data:
                    df = pd.DataFrame(data)

                    # Filters
                    sel_loc = st.selectbox("Filter by Location", ["All"] + sorted(df["Location"].unique()), key="sales_today_loc_select")
                    if sel_loc != "All":
                        df = df[df["Location"] == sel_loc]

                    sel_cat = st.selectbox("Filter by Category", ["All"] + sorted(df["Category"].unique()), key="sales_today_cat_select")
                    if sel_cat != "All":
                        df = df[df["Category"] == sel_cat]

                    st.success(f"✅ Showing {len(df)} product-level sales for today")

                    # Summary counts
                    summary = df.groupby("Location").size().reset_index(name="Order Count")
                    st.subheader("📍 Orders per Location (Today)")
                    st.table(summary, key="sales_today_summary_table")

                    # Detailed sales
                    st.dataframe(df, width="stretch", hide_index=True, key="sales_today_df")

                    # Download
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="⬇️ Download Sales CSV",
                        data=csv,
                        file_name=f"sales_{date.today().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="sales_today_download_btn"
                    )
                else:
                    st.info("No product-level sales found for today.")

            else:
                st.info("No orders returned from Square.")

        except Exception as e:
            st.error(f"Error fetching today's sales: {e}")

        # --- NEW: HISTORY BY DATE VIEW ---
        st.divider()
        st.header("📅 Sales History by Date (from 03/20/2026 onwards)")
        
        try:
            response = square_client.orders.search(location_ids=location_ids, limit=500)
        
            if response.orders:
                cutoff_date = date(2026, 3, 20)
                data_hist = []
        
                for order in response.orders:
                    created_dt = datetime.fromisoformat(order.created_at.replace("Z", "+00:00"))
                    created_dt = created_dt.astimezone(haiti_tz)
        
                    if created_dt.date() < cutoff_date:
                        continue
        
                    if order.line_items:
                        for item in order.line_items:
                            qty_sold = int(item.quantity)
                            product_name = item.name or ""
                            product_token = item.catalog_object_id
        
                            token = "NO_TOKEN"
                            category = "Unknown"
                            location_name = normalize_location(location_lookup.get(order.location_id, "Unknown"))
        
                            inv_result = supabase.table("Master_Inventory").select(
                                '"Full Name", SKU, Category, Location, Token'
                            ).eq("Token", product_token).execute()
                            if inv_result.data:
                                inv_info = inv_result.data[0]
                                category = inv_info["Category"]
                                location_name = normalize_location(inv_info["Location"])
                                token = inv_info["Token"]
                            elif product_name.strip():
                                inv_result = supabase.table("Master_Inventory").select(
                                    '"Full Name", SKU, Category, Location, Token'
                                ).eq("Full Name", product_name.strip()).execute()
                                if inv_result.data:
                                    inv_info = inv_result.data[0]
                                    category = inv_info["Category"]
                                    location_name = normalize_location(inv_info["Location"])
                                    token = inv_info["Token"] or "NO_TOKEN"
        
                            data_hist.append({
                                "Date": created_dt.date(),
                                "Time (Haiti)": created_dt.strftime("%H:%M:%S"),
                                "Location": location_name,
                                "Category": category,
                                "Product": f"{qty_sold} × {product_name if product_name else 'Unknown Product'}",
                                "SKU": inv_info["SKU"] if inv_result.data else "NO_SKU",
                                "Token": token,
                                "State": order.state
                            })
        
                if data_hist:
                    df_hist = pd.DataFrame(data_hist)
        
                    # Date filter
                    sel_date = st.date_input(
                        "Select Date",
                        value=date.today(),
                        min_value=cutoff_date,
                        key="sales_hist_date_input"
                    )
                    
                    # ✅ Search filter by SKU or Name
                    search_query = st.text_input(
                        "🔍 Search Sales History",
                        placeholder="Enter SKU or Product Name...",
                        key="sales_hist_search_input"
                    ).strip().lower()
                    
                    search_all = st.checkbox("Search across all dates", value=False, key="sales_hist_all_checkbox")
                    
                    df_hist_filtered = df_hist.copy()
                    
                    if search_query:
                        if search_all:
                            # Search across all dates ≥ cutoff
                            df_hist_filtered = df_hist_filtered[
                                df_hist_filtered["SKU"].str.lower().str.contains(search_query) |
                                df_hist_filtered["Product"].str.lower().str.contains(search_query)
                            ]
                        else:
                            # Restrict to selected date first, then search
                            df_hist_filtered = df_hist_filtered[df_hist_filtered["Date"] == sel_date]
                            df_hist_filtered = df_hist_filtered[
                                df_hist_filtered["SKU"].str.lower().str.contains(search_query) |
                                df_hist_filtered["Product"].str.lower().str.contains(search_query)
                            ]
                    else:
                        # No search, just filter by date
                        df_hist_filtered = df_hist_filtered[df_hist_filtered["Date"] == sel_date]
                    
                    st.success(f"✅ Showing {len(df_hist_filtered)} product-level sales for {sel_date if not search_all else 'all dates'}")
                    
                    summary_hist = df_hist_filtered.groupby("Location").size().reset_index(name="Order Count")
                    st.subheader(f"📍 Orders per Location ({sel_date if not search_all else 'All Dates'})")
                    st.table(summary_hist, key="sales_hist_summary_table")
                    
                    st.dataframe(df_hist_filtered, width="stretch", hide_index=True, key="sales_hist_df")
                else:
                    st.info("No sales found after 03/20/2026.")
        
            else:
                st.info("No orders returned from Square.")
        
        except Exception as e:
            st.error(f"Error fetching sales history: {e}")
