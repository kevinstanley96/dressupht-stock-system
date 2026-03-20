import streamlit as st
import pandas as pd
import time
from datetime import date

def render_tab(container, supabase, username, role, loc_list, t, master_inventory=None):
    with container:
        st.header(t["admin_header"])

        if role != "Admin":
            st.error("🚫 Access Denied. This section is restricted to System Administrators.")
            return

        admin_subtab = st.tabs(["👤 User Management","📜 Global Activity Log","🧹 Database Maintenance"])

        # --- SUB-TAB 1: USER MANAGEMENT ---
        with admin_subtab[0]:
            st.subheader("Manage Team Roles & Locations")
            try:
                users_df = pd.DataFrame(supabase.table("user_roles_locations").select("*").execute().data)
                if not users_df.empty:
                    st.dataframe(users_df[['user_name','role','location']], width='stretch', hide_index=True, key="admin_users_df")
                    st.divider()

                    # Update Role
                    with st.form("role_update_form"):
                        target_user = st.selectbox("Select User", users_df['user_name'].unique(), key="admin_role_user_select")
                        new_role = st.selectbox("Assign New Role", ["Admin","Manager","Staff"], key="admin_role_select")
                        if st.form_submit_button("Update Role", key="admin_update_role_btn"):
                            supabase.table("user_roles_locations").update({"role":new_role}).eq("user_name",target_user).execute()
                            st.success(f"Updated {target_user} to {new_role}")
                            time.sleep(1); st.rerun()

                    # Add Location
                    with st.form("loc_add_form"):
                        target_user_loc = st.selectbox("Select User", users_df['user_name'].unique(), key="admin_loc_add_user")
                        new_loc = st.selectbox("Assign Location", ["Pv","Canape-Vert"], key="admin_loc_add_loc")
                        if st.form_submit_button("Add Location", key="admin_add_loc_btn"):
                            role_val = users_df.loc[users_df['user_name']==target_user_loc,'role'].iloc[0]
                            supabase.table("user_roles_locations").insert({
                                "user_name":target_user_loc,
                                "role":role_val,
                                "location":new_loc
                            }).execute()
                            st.success(f"Added {new_loc} for {target_user_loc}")
                            time.sleep(1); st.rerun()

                    # Remove Location
                    with st.form("loc_remove_form"):
                        target_user_loc = st.selectbox("Select User", users_df['user_name'].unique(), key="admin_loc_remove_user")
                        existing_locs = users_df[users_df['user_name']==target_user_loc]['location'].unique().tolist()
                        remove_loc = st.selectbox("Select Location to Remove", existing_locs, key="admin_loc_remove_loc")
                        if st.form_submit_button("Remove Location", key="admin_remove_loc_btn"):
                            supabase.table("user_roles_locations").delete().eq("user_name",target_user_loc).eq("location",remove_loc).execute()
                            st.success(f"Removed {remove_loc} for {target_user_loc}")
                            time.sleep(1); st.rerun()

                    st.divider()
                    # Add New User
                    st.subheader("➕ Add New User")
                    with st.form("add_user_form", clear_on_submit=True):
                        new_username = st.text_input("Username", key="admin_new_user_name")
                        new_role = st.selectbox("Role", ["Admin","Manager","Staff"], key="admin_new_user_role")
                        new_locations = st.multiselect("Assign Locations", ["Pv","Canape-Vert"], key="admin_new_user_locs")
                        default_password = st.text_input("Default Password", value="DressupHT@2026!", type="password", key="admin_new_user_pwd")

                        if st.form_submit_button("Create User", key="admin_create_user_btn"):
                            if not new_username.strip():
                                st.error("Username cannot be empty.")
                            elif not default_password.strip():
                                st.error("Password cannot be empty.")
                            else:
                                try:
                                    for loc in (new_locations if new_locations else ["Pv"]):
                                        supabase.table("user_roles_locations").insert({
                                            "user_name": new_username.strip(),
                                            "role": new_role,
                                            "location": loc,
                                            "password": default_password.strip()
                                        }).execute()
                                    st.success(f"User '{new_username}' created with role '{new_role}', locations {new_locations or ['Pv']}, and a default password.")
                                    time.sleep(1); st.rerun()
                                except Exception as e:
                                    st.error(f"Error creating user: {e}")
                else:
                    st.warning("The user_roles_locations table is currently empty.")
            except Exception as e:
                st.error(f"Could not load user table: {e}")

        # --- SUB-TAB 2: GLOBAL ACTIVITY LOG ---
        with admin_subtab[1]:
            st.subheader("Recent System-Wide Actions")
            log_choice = st.radio("View Logs From:", ["Arrivals","Inventory Audits","Depot Movements","Mannequin Display"], horizontal=True, key="admin_log_choice")
            table_map = {"Arrivals":"Arrival","Inventory Audits":"Inventory","Depot Movements":"Depot","Mannequin Display":"Mannequin"}
            try:
                logs_df = pd.DataFrame(supabase.table(table_map[log_choice]).select("*").execute().data)
                if not logs_df.empty:
                    date_cols = ['Date','Last_Updated','created_at']
                    found_date = next((c for c in date_cols if c in logs_df.columns), None)
                    if found_date:
                        logs_df = logs_df.sort_values(by=found_date, ascending=False)
                    st.dataframe(logs_df, width='stretch', hide_index=True, key="admin_logs_df")
                else:
                    st.info(f"No records found in the {log_choice} table.")
            except Exception as e:
                st.error(f"Error fetching logs: {e}")

        # --- SUB-TAB 3: DATABASE MAINTENANCE ---
        with admin_subtab[2]:
            st.subheader("Data Management")
            st.warning("⚠️ These tools allow you to export or manage bulk data.")

            col1, col2 = st.columns(2)
            with col1:
                st.write("### Export Data")
                if master_inventory is not None:
                    csv = master_inventory.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Master Inventory (CSV)", data=csv,
                                       file_name=f"Master_Inventory_{date.today()}.csv", mime='text/csv',
                                       key="admin_download_inventory_btn")
            with col2:
                st.write("### System Status")
                if master_inventory is not None:
                    st.metric("Total Items in System", len(master_inventory), key="admin_total_items_metric")
                st.info("To clear or reset database tables, please use the Supabase SQL Editor for safety.")
