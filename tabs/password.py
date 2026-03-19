import streamlit as st

def render_tab(container, supabase, username, role, loc_list, t):
    with container:
        st.header(t["password_header"])
        new_pw = st.text_input("Enter new password", type="password")
        confirm_pw = st.text_input("Confirm new password", type="password")

        if st.button("Update Password"):
            if new_pw and new_pw == confirm_pw:
                try:
                    supabase.table("user_roles_locations") \
                        .update({"password": new_pw}) \
                        .eq("user_name", username) \
                        .execute()
                    st.success("Password updated successfully!")
                except Exception as e:
                    st.error(f"Error updating password: {e}")
            else:
                st.error("Passwords do not match.")
