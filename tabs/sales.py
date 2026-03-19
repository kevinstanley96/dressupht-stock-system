import streamlit as st
import pandas as pd
import time
from datetime import datetime, date
from utils.helpers import normalize_location, safe_dataframe
from pytz import timezone

haiti_tz = timezone("America/Port-au-Prince")

def render_tab(container, supabase, square_client, username, role, loc_list, t):
    with container:
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
                            product_name = item.name or ""   # guard against None
                            product_token = item.catalog_object_id  # Square variation ID

                            # Default values
                            token = "NO_TOKEN"
                            category = "Unknown"
                            location_name = "Unknown"

                            # First try to match by Token (Option 3)
                            inv_result = supabase.table("Master_Inventory").select('"Full Name", SKU, Category, Location, Token').eq("Token", product_token).execute()
                            if inv_result.data:
                                inv_info = inv_result.data[0]
                                category = inv_info["Category"]
                                location_name = normalize_location(inv_info["Location"])
                                token = inv_info["Token"]
                            else:
                                # Fallback by product name
                                if product_name.strip():
                                    inv_result = supabase.table("Master_Inventory").select('"Full Name", SKU, Category, Location, Token').eq("Full Name", product_name.strip()).execute()
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

                            # Append row with guaranteed values
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

                    # Location filter
                    sel_loc = st.selectbox("Filter by Location", ["All"] + sorted(df["Location"].unique()))
                    if sel_loc != "All":
                        df = df[df["Location"] == sel_loc]

                    # Category filter
                    sel_cat = st.selectbox("Filter by Category", ["All"] + sorted(df["Category"].unique()))
                    if sel_cat != "All":
                        df = df[df["Category"] == sel_cat]

                    st.success(f"✅ Showing {len(df)} product-level sales for today")

                    # Summary counts by Location
                    summary = df.groupby("Location").size().reset_index(name="Order Count")
                    st.subheader("📍 Orders per Location (Today)")
                    st.table(summary)

                    # Show detailed product-level sales
                    st.dataframe(df, width="stretch", hide_index=True)

                    # Download button
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="⬇️ Download Sales CSV",
                        data=csv,
                        file_name=f"sales_{date.today().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.info("No product-level sales found for today.")

            else:
                st.info("No orders returned from Square.")

        except Exception as e:
            st.error(f"Error fetching today's sales: {e}")
