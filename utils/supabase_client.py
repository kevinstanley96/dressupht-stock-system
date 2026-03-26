import streamlit as st
from supabase import create_client, Client
import os

@st.cache_resource
def init_connection() -> Client:
    # Try to read from Streamlit secrets first
    url = st.secrets.get("SUPABASE_URL", None)
    key = st.secrets.get("SUPABASE_KEY", None)

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
