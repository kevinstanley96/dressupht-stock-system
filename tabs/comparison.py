import streamlit as st
import pandas as pd

def render_tab(tab, supabase, username, role, loc_list, t):
    with tab:
        st.title("📑 Inventory vs Square Comparison (Debug Mode)")

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

            # Debug: show columns and sample rows
            st.write("Square CV columns:", square_cv.columns.tolist())
            st.write(square_cv.head())
            st.write("Square PV columns:", square_pv.columns.tolist())
            st.write(square_pv.head())

            # Normalize names for safer matching
            master_df["Full Name"] = master_df["Full Name"].str.strip().str.lower()
            square_cv["Item Name"] = square_cv["Item Name"].str.strip().str.lower()
            square_pv["Item Name"] = square_pv["Item Name"].str.strip().str.lower()

            # --- Canapé-Vert comparison ---
            st.subheader("🔍 Inconsistencies - Canapé-Vert")
            wigs_master_cv = master_df[
                (master_df["Category"].str.contains("wig", case=False, na=False)) &
                (master_df["Location"] == "Canapé-Vert")
            ]
            merged_cv = wigs_master_cv.merge(
                square_cv[["Item Name", "Current Quantity Dressup Haiti"]],
                left_on="Full Name",
                right_on="Item Name",
                how="inner"
            )
            # Debug: show merged rows before filtering
            st.write("Merged CV sample:", merged_cv.head())

            inconsistent_cv = merged_cv[merged_cv["Stock"] != merged_cv["Current Quantity Dressup Haiti"]]
            st.dataframe(inconsistent_cv[["Full Name", "Stock", "Current Quantity Dressup Haiti"]])

            # --- PV comparison ---
            st.subheader("🔍 Inconsistencies - PV")
            wigs_master_pv = master_df[
                (master_df["Category"].str.contains("wig", case=False, na=False)) &
                (master_df["Location"] == "PV")
            ]
            merged_pv = wigs_master_pv.merge(
                square_pv[["Item Name", "Current Quantity Dressupht Pv"]],
                left_on="Full Name",
                right_on="Item Name",
                how="inner"
            )
            # Debug: show merged rows before filtering
            st.write("Merged PV sample:", merged_pv.head())

            inconsistent_pv = merged_pv[merged_pv["Stock"] != merged_pv["Current Quantity Dressupht Pv"]]
            st.dataframe(inconsistent_pv[["Full Name", "Stock", "Current Quantity Dressupht Pv"]])
        else:
            st.info("Upload both Square Excel files to run comparison.")
