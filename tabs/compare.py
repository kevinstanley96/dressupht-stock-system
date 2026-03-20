import streamlit as st
import pandas as pd
from utils.helpers import search_inventory, safe_dataframe, show_high_stock_alert

def render_tab(container, supabase, username, role, loc_list, t):
    with container:
        st.header(t["compare_header"])

        # ✅ Always reload Master_Inventory fresh
        inv_query = supabase.table("Master_Inventory").select("*").execute()
        master_inventory = pd.DataFrame(inv_query.data) if inv_query.data else pd.DataFrame()

        if not master_inventory.empty:
            # PART A: SIDE-BY-SIDE COMPARISON
            st.subheader("Location Comparison (CV vs PV)")
            df_cv = master_inventory[master_inventory['Location']=="Canape-Vert"][['SKU','Full Name','Stock','Category']]
            df_pv = master_inventory[master_inventory['Location']=="Pv"][['SKU','Full Name','Stock']]

            comparison_df = pd.merge(df_cv, df_pv, on="SKU", how="outer", suffixes=('_CV','_PV'))
            comparison_df['Full Name_CV'] = comparison_df['Full Name_CV'].fillna(comparison_df['Full Name_PV'])
            comparison_df['Stock_CV'] = comparison_df['Stock_CV'].fillna(0).astype(int)
            comparison_df['Stock_PV'] = comparison_df['Stock_PV'].fillna(0).astype(int)

            display_comp = comparison_df[['SKU','Full Name_CV','Stock_CV','Stock_PV']].rename(
                columns={'Full Name_CV':'Wig Name','Stock_CV':'Qty (Canape-Vert)','Stock_PV':'Qty (PV)'}
            )

            # ✅ Library-style search with unique key
            comp_search = st.text_input(
                "🔍 Search Comparison",
                placeholder="Filter by Name, SKU, Token, or Category...",
                key="compare_search_input"
            ).strip().lower()
            if comp_search:
                display_comp = search_inventory(
                    display_comp.rename(columns={'Wig Name':'Full Name'}),
                    comp_search
                )

            safe_dataframe(display_comp, display_comp.columns.tolist(), "No comparison data.", key="compare_df")

            # PART B: HIGH STOCK ALERTS
            st.divider()
            st.subheader("🔥 High Stock Alert (Over 50 Units)")
            col_high1, col_high2 = st.columns(2)

            with col_high1:
                show_high_stock_alert(df_cv, "Canape-Vert", threshold=50, key="compare_highstock_cv")

            with col_high2:
                show_high_stock_alert(df_pv, "PV", threshold=50, key="compare_highstock_pv")

        else:
            st.info("Master_Inventory is empty. Please run MISE or refresh inventory.")
