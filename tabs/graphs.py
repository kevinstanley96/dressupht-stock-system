import streamlit as st
import pandas as pd
import altair as alt

def render_tab(tab, supabase, username, role, loc_list, t):
    with tab:
        st.title("📊 Graphs Dashboard")

        # --- Fetch inventory data ---
        response = supabase.table("Master_Inventory").select("*").execute()
        if not response.data:
            st.warning("No inventory data available.")
            return

        df = pd.DataFrame(response.data)

        # --- Create subtabs ---
        subtab_names = [
            "Stock by Category",
            "Inventory Trend",
            "Top 10 Best-Sellers",
            "Location Comparison",
            "Stock Alerts"
        ]
        subtabs = st.tabs(subtab_names)

        # --- 1. Stock by Category ---
        with subtabs[0]:
            st.subheader("Stock by Category")
            if "Category" in df.columns and "Stock" in df.columns:
                category_stock = df.groupby("Category")["Stock"].sum().reset_index()
                chart = alt.Chart(category_stock).mark_bar().encode(
                    x=alt.X("Category", sort="-y"),
                    y="Stock",
                    tooltip=["Category", "Stock"]
                ).properties(width=600, height=400)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("Category/Stock columns not found in data.")

        # --- 2. Inventory Trend Over Time ---
        with subtabs[1]:
            st.subheader("Inventory Trend Over Time")

            # Fetch sync log data
            sync_response = supabase.table("sync_log").select("synced_at, location, type").order("synced_at").execute()
            if sync_response.data:
                sync_df = pd.DataFrame(sync_response.data)
                sync_df["synced_at"] = pd.to_datetime(sync_df["synced_at"], errors="coerce")

                # Count syncs per day
                trend = sync_df.groupby(sync_df["synced_at"].dt.date).size().reset_index(name="Sync Events")
                trend.rename(columns={"synced_at": "Date"}, inplace=True)

                chart = alt.Chart(trend).mark_line(point=True).encode(
                    x="Date:T",
                    y="Sync Events:Q",
                    tooltip=["Date", "Sync Events"]
                ).properties(width=600, height=400)

                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("No sync log data available.")

        # --- 3. Top 10 Best-Sellers (placeholder) ---
        with subtabs[2]:
            st.subheader("Top 10 Best-Selling Items")
            st.info("Horizontal bar chart will go here.")

        # --- 4. Location Comparison (placeholder) ---
        with subtabs[3]:
            st.subheader("Location Comparison")
            st.info("Grouped bar or pie chart will go here.")

        # --- 5. Stock Alerts (placeholder) ---
        with subtabs[4]:
            st.subheader("Stock Alerts")
            st.info("Gauge or highlight chart will go here.")
