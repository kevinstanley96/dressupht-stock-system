import streamlit as st
import pandas as pd
import io
import time
from datetime import datetime
from utils.helpers import sanitize_sheet_name, safe_dataframe

def render_tab(container, supabase, username, role, loc_list, t):
    with container:
        st.header(t["inventory_header"])

        # --- ENTRY LOGIC ---
        try:
            query = supabase.table("Master_Inventory").select("*").execute()
            master_inventory = pd.DataFrame(query.data) if query.data else pd.DataFrame()
        except Exception:
            master_inventory = pd.DataFrame()

        if not master_inventory.empty:
            # Location filter
            if role in ["Admin", "Manager"]:
                sel_loc = st.selectbox(
                    t["location"],
                    ["All Locations"] + sorted(master_inventory['Location'].unique()),
                    key="inventory_location_select"
                )
                inv_df = master_inventory if sel_loc == "All Locations" else master_inventory[master_inventory['Location'] == sel_loc]
            else:
                inv_df = master_inventory[master_inventory['Location'] == loc_list[0]]
                st.write(f"📍 {t['location']}: {', '.join(loc_list)}")
                sel_loc = loc_list[0]

            # Category selection
            sel_cat = st.selectbox(
                "Select Category",
                sorted(inv_df['Category'].unique()),
                key="inventory_category_select"
            )
            cat_df = inv_df[inv_df['Category'] == sel_cat].copy()

            # Editable physical counts
            cat_df['Total_Physical'] = 0
            edited_df = st.data_editor(
                cat_df[['Full Name','SKU','Stock','Total_Physical']],
                num_rows="dynamic",
                width='stretch',
                key="inventory_data_editor"
            )

            # Save audit entries
            if st.button("✅ Save Audit", key="inventory_save_audit_btn"):
                for _, row in edited_df.iterrows():
                    audit_entry = {
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Name": row['Full Name'],
                        "Category": sel_cat,
                        "System_Stock": row['Stock'],
                        "Total_Physical": row['Total_Physical'],
                        "Discrepancy": row['Total_Physical'] - row['Stock'],
                        "Counter_Name": username,
                        "location": sel_loc
                    }
                    supabase.table("Inventory").insert(audit_entry).execute()
                st.success("Audit saved successfully!")
                time.sleep(1); st.rerun()
        else:
            st.info("No data in Master_Inventory.")

        st.divider(); st.subheader("📜 Audit History by Category")

        # --- HISTORY + EXCEL EXPORT ---
        try:
            aud_log_res = supabase.table("Inventory").select("*").order("Date", desc=True).execute()
            if aud_log_res.data:
                df_log = pd.DataFrame(aud_log_res.data)

                # Filter by location
                if role == "Staff":
                    df_log = df_log[df_log['location'].isin(loc_list)]
                elif role in ["Admin","Manager"] and sel_loc != "All Locations":
                    df_log = df_log[df_log['location'] == sel_loc]

                output, summary_rows = io.BytesIO(), []
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    for cat in sorted(df_log['Category'].unique()):
                        cat_df = df_log[df_log['Category'] == cat]
                        safe_name = sanitize_sheet_name(cat)
                        cat_df.to_excel(writer, sheet_name=safe_name, index=False)

                        summary_rows.append({
                            "Category": cat,
                            "Sheet Name": safe_name,
                            "Total Records": len(cat_df),
                            "Total Physical": cat_df['Total_Physical'].sum(),
                            "System Stock": cat_df['System_Stock'].sum(),
                            "Total Discrepancy": cat_df['Discrepancy'].sum()
                        })

                        st.markdown(f"### 📂 {cat}")
                        st.dataframe(
                            cat_df[['Date','Name','Total_Physical','System_Stock','Discrepancy','Counter_Name','location']],
                            width='stretch',
                            hide_index=True,
                            key=f"inventory_audit_log_{cat}"
                        )

                    summary_df = pd.DataFrame(summary_rows)
                    summary_df.to_excel(writer, sheet_name="Summary", index=False)

                st.download_button(
                    "⬇️ Download Full Audit History (Excel with Sheets + Summary)",
                    data=output.getvalue(),
                    file_name="audit_history_by_category.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="inventory_download_btn"
                )

                st.divider(); st.subheader("📊 Summary Preview")
                st.dataframe(summary_df, width='stretch', hide_index=True, key="inventory_summary_preview_df")
            else:
                st.info("No audit records found yet.")
        except Exception as e:
            st.error(f"Error fetching history: {e}")
