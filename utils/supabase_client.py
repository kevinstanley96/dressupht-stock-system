import streamlit as st
from supabase import create_client, Client
import os

@st.cache_resource
def init_connection() -> Client:
    # Try to read from Streamlit secrets first
    url = st.secrets.get("SUPABASE_URL", None)
    key = st.secrets.get("SUPABASE_KEY", None)

    st.write("🔍 Debug: Checking Streamlit secrets...")
    st.write("   URL =", url if url else "❌ Not found")
    st.write("   Key present =", bool(key))
    if key:
        st.write("   Key starts with =", key[:6] + "..." + key[-4:])

    # Fallback to environment variables if secrets not found
    if not url or not key:
        st.write("⚠️ Falling back to environment variables...")
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        st.write("   URL =", url if url else "❌ Not found")
        st.write("   Key present =", bool(key))
        if key:
            st.write("   Key starts with =", key[:6] + "..." + key[-4:])

    # Final check
    if not url or not key:
        st.error("❌ Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY.")
        raise ValueError("Supabase credentials missing")

    try:
        client = create_client(url, key)
        st.success("✅ Supabase client initialized successfully")
        return client
    except Exception as e:
        st.error(f"❌ Failed to create Supabase client: {e}")
        raise

# Create a global client instance
supabase = init_connection()
