import streamlit as st
import pandas as pd
from utils.helpers import safe_dataframe, get_allowed_locations

def render_tab(container, supabase, username, role, loc_list, t):
    with container:
        st.header(t["library_header"])

        # --- Load Master Inventory ---
        try:
            query = supabase.table("Master_Inventory").select("*").execute()
            master_inventory = pd.DataFrame(query.data)
        except Exception as e:
            master_inventory = pd.DataFrame()
            st.error(f"Error loading inventory: {e}")

        if not master_inventory.empty:
            # Apply location filter
            disp_df = master_inventory.copy()
            if role == "Staff":
                disp_df = disp_df[disp_df['Location'].isin(loc_list)]

            # Filters row
            c1, c2, c3, c4, c5, c6 = st.columns([2, 1, 1, 1, 1, 1])
            search_query = c1.text_input(
                "🔍 Search",
                placeholder="Search by name, SKU, token...",
                key="library_search_input"
            )

            # Location filter
            if role != "Staff":
                sel_loc = c2.selectbox(
                    "Location",
                    ["All Locations"] + sorted(master_inventory['Location'].unique()),
                    key="library_location_select"
                )
                if sel_loc != "All Locations":
                    disp_df = disp_df[disp_df['Location'] == sel_loc]
            else:
                c2.write(f"📍 Location(s): {', '.join(loc_list) if loc_list else 'None'}")

            # Category filter
            sel_cat = c3.selectbox(
                "Category",
                ["All Categories"] + sorted(master_inventory['Category'].unique()),
                key="library_category_select"
            )
            if sel_cat != "All Categories":
                disp_df = disp_df[disp_df['Category'] == sel_cat]

            # Sorting
            sort_choice = c4.selectbox(
                "Sort By",
                ["Name", "Category", "Location", "Stock (High-Low)"],
                key="library_sort_select"
            )
            sort_map = {
                "Name": "Full Name",
                "Category": ["Category", "Full Name"],
                "Location": ["Location", "Full Name"],
                "Stock (High-Low)": "Stock"
            }
            ascending = sort_choice != "Stock (High-Low)"

            # Page controls inline
            page_size = c5.selectbox(
                "Rows per page",
                [20, 50, 100],
                index=1,
                key="library_page_size_select"
            )
            total_pages = max(1, (len(disp_df) // page_size) + (1 if len(disp_df) % page_size else 0))
            page_number = c6.number_input(
                "Page",
                min_value=1,
                max_value=total_pages,
                value=1,
                key="library_page_number_input"
            )

            # ✅ Live search across multiple fields
            if search_query and search_query.strip():
                q = search_query.strip().lower()
                disp_df = disp_df[
                    disp_df['Full Name'].str.lower().str.contains(q, na=False) |
                    disp_df['SKU'].str.lower().str.contains(q, na=False) |
                    disp_df['Token'].str.lower().str.contains(q, na=False) |
                    disp_df['Category'].str.lower().str.contains(q, na=False)
                ]

            # Sorting
            disp_df = disp_df.sort_values(by=sort_map[sort_choice], ascending=ascending)

            # Compact view toggle
            compact_view = st.checkbox(
                "📱 Compact view (mobile-friendly)",
                value=False,
                key="library_compact_view_checkbox"
            )

            # Location toggle for multi-location users
            show_location = False
            if role != "Staff" and len(loc_list) > 1:
                show_location = st.checkbox(
                    "Show Location column",
                    value=False,
                    key="library_show_location_checkbox"
                )

            # Pagination slice
            start = (page_number - 1) * page_size
            end = start + page_size
            page_df = disp_df.iloc[start:end]

            # Columns to display
            if compact_view:
                cols = ['Full Name','Stock','Price']
                if show_location:
                    cols.insert(0, 'Location')
            else:
                cols = ['Location','Category','Full Name','SKU','Stock','Price']

def safe_dataframe(df, cols, empty_msg="No data available.", key=None):
    """Safely display a dataframe with selected columns."""
    if df is not None and not df.empty:
        st.dataframe(df[cols], width="stretch", hide_index=True, key=key)
    else: 
        st.info("No data in Master_Inventory.")

