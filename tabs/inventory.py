import streamlit as st
import pandas as pd
import io
import time
from datetime import datetime
import httpx
from utils.helpers import sanitize_sheet_name, safe_dataframe

# --- Category merge map ---
CATEGORY_MERGE_MAP = {
    "Bob Lace Frontal Curly": "Bob Lace Frontal",
    "Bob Lace Frontal Droit": "Bob Lace Frontal",
    "Perruque Lace Frontal": "Bob Lace Frontal"
}

# --- Safe batch insert helper ---
def safe_batch_insert(supabase, table_name, records, batch_size=200, max_retries=3, delay=2):
    total = len(records)
    for i in range(0, total, batch_size):
        batch = records[i:i+batch_size]
        attempt = 0
        while attempt < max_retries:
            try:
                supabase.table(table_name).insert(batch).execute()
                break
            except httpx.RemoteProtocolError as e:
                attempt += 1
                if attempt < max_retries:
                    print(f"⚠️ RemoteProtocolError on batch {i//batch_size+1}, retrying ({attempt}/{max_retries})...")
                    time.sleep(delay)
                else:
                    print(f"❌ Failed to insert batch {i//batch_size+1} after {max_retries} retries: {e}")
                    raise

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

            # --- Apply category merge ---
            inv_df["Category_Merged"] = inv_df["Category"].replace(CATEGORY_MERGE_MAP)

            # Category selection (merged)
            sel_cat = st.selectbox(
                "Select Category",
                sorted(inv_df["Category_Merged"].unique()),
                key="inventory_category_select"
            )

            # Filter by merged category
            cat_df = inv_df[inv_df["Category_Merged"] == sel_cat].copy()

            # Editable physical counts
            cat_df['Total_Physical'] = 0
            edited_df = st.data_editor(
                cat_df[['Full Name','SKU','Stock','Total_Physical']],
                num_rows="dynamic",
                width='stretch',
                key="inventory_data_editor"
            )

            # --- Save audit entries (batched) ---
            if st.button("✅ Save Audit", key="inventory_save_audit"):
                audit_entries = []
                for _, row in edited_df.iterrows():
                    audit_entries.append({
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Name": row['Full Name'],
                        "Category": sel_cat,  # merged category
                        "System_Stock": row['Stock'],
                        "Total_Physical": row['Total_Physical'],
                        "Discrepancy": row['Total_Physical'] - row['Stock'],
                        "Counter_Name": username,
                        "location": sel_loc
                    })

                try:
                    safe_batch_insert(supabase, "Inventory", audit_entries)
                    st.success("Audit saved successfully!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error saving audit: {e}")
        else:
            st.info("No data in Master_Inventory.")

        st.divider(); st.subheader("📜 Audit History by Category")

        # --- HISTORY + EXCEL EXPORT ---
        try:
            aud_log_res = supabase.table("Inventory").select("*").order("Date", desc=True).execute()
            if aud_log_res.data:
                df_log = pd.DataFrame(aud_log_res.data)

                # Apply category merge to history
                df_log["Category_Merged"] = df_log["Category"].replace(CATEGORY_MERGE_MAP)

                # Filter by location
                if role == "Staff":
                    df_log = df_log[df_log['location'].isin(loc_list)]
                elif role in ["Admin","Manager"] and sel_loc != "All Locations":
                    df_log = df_log[df_log['location'] == sel_loc]

                output, summary_rows = io.BytesIO(), []
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    for cat in sorted(df_log['Category_Merged'].unique()):
                        cat_df = df_log[df_log['Category_Merged'] == cat]
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
                            key=f"audit_log_{cat}"
                        )

                    summary_df = pd.DataFrame(summary_rows)
                    summary_df.to_excel(writer, sheet_name="Summary", index=False)

                st.download_button(
                    "⬇️ Download Full Audit History (Excel with Sheets + Summary)",
                    data=output.getvalue(),
                    file_name="audit_history_by_category.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="inventory_download_button"
                )

                st.divider(); st.subheader("📊 Summary Preview")
                st.dataframe(summary_df, width='stretch', hide_index=True, key="inventory_summary_preview")
            else:
                st.info("No audit records found yet.")
        except Exception as e:
            st.error(f"Error fetching history: {e}")
