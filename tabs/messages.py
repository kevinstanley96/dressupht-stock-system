import streamlit as st
import pandas as pd
from datetime import datetime
import pytz

haiti_tz = pytz.timezone("America/Port-au-Prince")

def render_messages_tab(container, supabase, username, role, loc_list, t, user_id=None):
    """
    Message tab UI for wig requests and general questions.
    - supabase: initialized supabase client
    - username: current user's display name
    - role: user role string
    - loc_list: list of locations available to the user
    - t: translations/dictionary (optional)
    - user_id: UUID of the logged-in user (sender_id)
    """
    with container:
        st.header("✉️ Messages / Wig Requests")

        # --- Submit message form ---
        st.subheader("Send a request or question")
        with st.form("message_form", clear_on_submit=True):
            sender = st.text_input("Your name", value=username or "", disabled=bool(username))
            if role in ["Admin", "Manager"]:
                location = st.selectbox("Location", ["-- Select location --"] + sorted(loc_list), index=0)
                if location == "-- Select location --":
                    location = None
            else:
                location = loc_list[0] if loc_list else "Unknown"

            msg_type = st.radio("Type", ["Wig Request", "Question / Other"], index=0, horizontal=True)
            subject = st.text_input("Subject", max_chars=100)
            message = st.text_area("Message", height=160, max_chars=2000)
            submit = st.form_submit_button("📨 Send Message")

            if submit:
                now_ht = datetime.now(haiti_tz)
                record = {
                    "id": None,  # let DB generate UUID/bigint
                    "sender_id": user_id,  # must be auth.uid() in Supabase
                    "sender_name": sender or "Anonymous",
                    "location": location,
                    "type": "WIG_REQUEST" if msg_type == "Wig Request" else "OTHER",
                    "subject": subject or "(no subject)",
                    "message": message or "",
                    "status": "OPEN",
                    "created_at": now_ht.isoformat(),
                    "updated_at": now_ht.isoformat(),
                }
                try:
                    supabase.table("messages").insert(record).execute()
                    st.success("Message sent. Thank you — we will follow up soon.")
                except Exception as e:
                    st.error(f"Failed to send message: {e}")

        st.divider()

        # --- Inbox / Recent messages (Admins & Managers) ---
        if role in ["Admin", "Manager"]:
            st.subheader("Inbox — Recent messages")
            try:
                res = supabase.table("messages").select("*").order("created_at", desc=True).limit(200).execute()
                messages_df = pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=[
                    "id","sender_name","location","type","subject","message","status","created_at"
                ])

                # Filters
                cols = st.columns([2,2,1])
                with cols[0]:
                    filter_loc = st.selectbox("Filter by location", ["All"] + sorted(messages_df['location'].dropna().unique().tolist()), index=0)
                with cols[1]:
                    filter_type = st.selectbox("Filter by type", ["All","WIG_REQUEST","OTHER"], index=0)
                with cols[2]:
                    show_only_open = st.checkbox("Only open", value=True)

                df_view = messages_df.copy()
                if filter_loc != "All":
                    df_view = df_view[df_view['location'] == filter_loc]
                if filter_type != "All":
                    df_view = df_view[df_view['type'] == filter_type]
                if show_only_open:
                    df_view = df_view[df_view['status'] == "OPEN"]

                if df_view.empty:
                    st.info("No messages match the current filters.")
                else:
                    for _, row in df_view.sort_values("created_at", ascending=False).iterrows():
                        created = ""
                        try:
                            created = datetime.fromisoformat(str(row.get("created_at"))).astimezone(haiti_tz).strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            created = str(row.get("created_at",""))
                        header = f"{row.get('subject','(no subject)')} — {row.get('sender_name','')} ({row.get('location','')}) [{row.get('status','')}]"
                        with st.expander(header):
                            st.markdown(f"**Type:** {row.get('type')}")
                            st.markdown(f"**Sent:** {created}")
                            st.markdown("**Message:**")
                            st.write(row.get("message",""))
                            action_cols = st.columns([1,1,3])
                            if action_cols[0].button("Mark Resolved", key=f"resolve_{row.get('id')}"):
                                try:
                                    supabase.table("messages").update({"status":"RESOLVED"}).eq("id", row.get("id")).execute()
                                    st.success("Marked as resolved.")
                                    st.experimental_rerun()
                                except Exception as e:
                                    st.error(f"Could not update status: {e}")
                            if action_cols[1].button("Re-open", key=f"reopen_{row.get('id')}"):
                                try:
                                    supabase.table("messages").update({"status":"OPEN"}).eq("id", row.get("id")).execute()
                                    st.success("Re-opened message.")
                                    st.experimental_rerun()
                                except Exception as e:
                                    st.error(f"Could not update status: {e}")
                            reply = action_cols[2].text_input("Quick reply (not sent)", key=f"reply_{row.get('id')}")

            except Exception as e:
                st.error(f"Error loading messages: {e}")

        else:
            # --- Recent messages for regular users (their own messages) ---
            st.subheader("Your recent messages")
            try:
                res = supabase.table("messages").select("*").eq("sender_name", username).order("created_at", desc=True).limit(50).execute()
                user_msgs = pd.DataFrame(res.data) if res.data else pd.DataFrame()
                if user_msgs.empty:
                    st.info("You have not sent any messages yet.")
                else:
                    for _, row in user_msgs.iterrows():
                        created = ""
                        try:
                            created = datetime.fromisoformat(str(row.get("created_at"))).astimezone(haiti_tz).strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            created = str(row.get("created_at",""))
                        st.markdown(f"**{row.get('subject','(no subject)')}** — {created} — **{row.get('status','')}**")
                        st.write(row.get("message",""))
                        st.divider()
            except Exception as e:
                st.error(f"Error fetching your messages: {e}")
