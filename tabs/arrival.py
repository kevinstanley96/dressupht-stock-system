import streamlit as st
import pandas as pd
import time
from datetime import datetime, date
from utils.helpers import safe_dataframe

def render_tab(container, supabase, username, role, loc_list, t):
    with container:
        st.header(t["arrival_header"])

        if role not in ["Admin", "Manager"]:
            st.warning(t["restricted"])
        else:
            st.session_state.setdefault("arrival_verify", {"name": None, "cat": None, "sku": ""})
            st.session_state.setdefault("arrival_date", date.today())

            col1, col2 = st.columns([1, 2])

            # --- Arrival Entry ---
            with col1:
                st.subheader(t["log_stock"])
                search_query = st.text_input("🔍 Search Inventory", placeholder="Search by SKU, Name, Token, or Category...", key="arrival_search").strip().lower()

                if search_query:
                    inv_query = supabase.table("Master_Inventory").select("*").execute()
                    inv_df = pd.DataFrame(inv_query.data) if inv_query.data else pd.DataFrame()
                
                    match = search_inventory(inv_df, search_query)
                    if not match.empty:
                        options = match[['SKU','Full Name']].apply(lambda x: f"{x['SKU']} - {x['Full Name']}", axis=1).tolist()
                        selected_sku = st.selectbox("Select Item", options).split(" - ")[0]
                        t_item = match[match['SKU'] == selected_sku].iloc[0]
                
                        st.session_state.arrival_verify = {
                            "name": t_item['Full Name'],
                            "cat": t_item['Category'],
                            "sku": t_item['SKU']
                        }
                    else:
                        st.session_state.arrival_verify = {"name": None, "cat": None, "sku": ""}
                        st.error(t["not_found"])

                if st.session_state.arrival_verify["name"]:
                    st.info(f"**{t['item']}:** {st.session_state.arrival_verify['name']}\n\n"
                            f"**{t['category']}:** {st.session_state.arrival_verify['cat']}")

                    with st.form("arrival_form", clear_on_submit=True):
                        arr_date = st.date_input(t["arrival_date"], value=st.session_state.arrival_date)
                        arr_qty = st.number_input(t["quantity"], min_value=1, step=1)
                        arr_loc = st.selectbox(t["location"], ["Pv","Canape-Vert"]) if role in ["Admin","Manager"] else loc_list[0]

                        if st.form_submit_button(t["confirm"]):
                            try:
                                arrival_data = {
                                    "date": datetime.combine(arr_date, datetime.now().time()).isoformat(),
                                    "sku": st.session_state.arrival_verify["sku"],
                                    "wig_name": st.session_state.arrival_verify["name"],
                                    "category": st.session_state.arrival_verify["cat"],
                                    "quantity": int(arr_qty),
                                    "user": username,
                                    "location": arr_loc
                                }
                                supabase.table("Arrival").insert(arrival_data).execute()
                                st.success(t["success"].format(qty=arr_qty, name=st.session_state.arrival_verify['name']))
                                st.session_state.arrival_date = arr_date
                                st.session_state.arrival_verify = {"name": None, "cat": None, "sku": ""}
                                time.sleep(1); st.rerun()
                            except Exception as e:
                                st.error(f"{t['error_log']}: {e}")

            # --- Arrival History ---
            with col2:
                st.subheader(t["history"])
                try:
                    arr_log = supabase.table("Arrival").select("*").order("date", desc=True).execute()
                    if arr_log.data:
                        log_df = pd.DataFrame(arr_log.data)
                        log_df['date'] = pd.to_datetime(log_df['date']).dt.date

                        st.dataframe(log_df[['date','wig_name','sku','category','quantity','location','user']],
                                     width='stretch', hide_index=True)
                        st.caption(t["showing"].format(count=len(log_df)))

                        # Daily summary
                        st.divider(); st.subheader("📊 Daily Summary")
                        st.dataframe(log_df.groupby('date')['quantity'].sum().reset_index(),
                                     width='stretch', hide_index=True)
                        st.dataframe(log_df.groupby(['date','category'])['quantity'].sum().reset_index(),
                                     width='stretch', hide_index=True)

                        # Monthly summary
                        st.divider(); st.subheader("📅 Monthly Summary")
                        log_df['month'] = pd.to_datetime(log_df['date']).dt.to_period('M').astype(str)
                        st.dataframe(log_df.groupby('month')['quantity'].sum().reset_index(),
                                     width='stretch', hide_index=True)
                        st.dataframe(log_df.groupby(['month','category'])['quantity'].sum().reset_index(),
                                     width='stretch', hide_index=True)
                    else:
                        st.write(t["no_logs"])
                except Exception as e:
                    st.error(f"{t['error_log']}: {e}")
