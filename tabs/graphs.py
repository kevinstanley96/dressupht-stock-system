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

        # --- 1. Stock by Category (Bar Chart) ---
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
