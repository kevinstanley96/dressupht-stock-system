import streamlit as st
import pandas as pd

def render_tab(tab, supabase, username, role, loc_list, t):
    with tab:
        st.title("📑 Inventory vs Square Comparison")

        # --- Fetch Master_Inventory ---
        response = supabase.table("Master_Inventory").select("*").execute()
        if not response.data:
            st.warning("No Master_Inventory data available.")
            return

        master_df = pd.DataFrame(response.data)

        # --- Uploaders for Square files ---
        st.subheader("Upload Square Excel files")
        square_file_cv = st.file_uploader(
            "Square Export - Canapé-Vert",
            type=["xlsx"],
            key="comparison_square_cv"
        )
        square_file_pv = st.file_uploader(
            "Square Export - PV",
            type=["xlsx"],
            key="comparison_square_pv"
        )

        # --- Comparison Logic ---
        if square_file_cv and square_file_pv:
            # Read Square files with headers on row 2 (index=1)
            square_cv = pd.read_excel(square_file_cv, header=1)
            square_pv = pd.read_excel(square_file_pv, header=1)

            # Filter wigs only
            wigs_master = master_df[master_df["Category"].str.contains("wig", case=False, na=False)]
            wigs_cv = square_cv[square_cv["Categories"].str.contains("wig", case=False, na=False)]
            wigs_pv = square_pv[square_pv["Categories"].str.contains("wig", case=False, na=False)]

            # Compare stock per location
            st.subheader("🔍 Inconsistencies - Canapé-Vert")
            merged_cv = wigs_master[wigs_master["Location"] == "Canapé-Vert"].merge(
                wigs_cv, on="SKU", suffixes=("_master", "_square"), how="inner"
            )
            inconsistent_cv = merged_cv[merged_cv["Stock_master"] != merged_cv["Stock_square"]]
            st.dataframe(inconsistent_cv[["SKU", "Full Name", "Stock_master", "Stock_square"]])

            st.subheader("🔍 Inconsistencies - PV")
            merged_pv = wigs_master[wigs_master["Location"] == "PV"].merge(
                wigs_pv, on="SKU", suffixes=("_master", "_square"), how="inner"
            )
            inconsistent_pv = merged_pv[merged_pv["Stock_master"] != merged_pv["Stock_square"]]
            st.dataframe(inconsistent_pv[["SKU", "Full Name", "Stock_master", "Stock_square"]])
        else:
            st.info("Upload both Square Excel files to run comparison.")
