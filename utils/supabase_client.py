import streamlit as st
from supabase import create_client, Client
import os

@st.cache_resource
def init_connection() -> Client:
    try:
        url = st.secrets.get("SUPABASE_URL", None)
        key = st.secrets.get("SUPABASE_KEY", None)
        st.write("🔍 Debug: URL from secrets =", url)
        st.write("🔍 Debug: Key present =", bool(key))
    except Exception as e:
        st.write("⚠️ Debug: Could not read st.secrets:", e)
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        st.write("🔍 Debug: URL from env =", url)
        st.write("🔍 Debug: Key present =", bool(key))

    if not url or not key:
        st.error("❌ Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY.")
        return None

    return create_client(url, key)

# Create a global client instance
supabase = init_connection()
