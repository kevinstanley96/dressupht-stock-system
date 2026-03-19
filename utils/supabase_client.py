import streamlit as st
from supabase import create_client, Client
import os

def init_connection() -> Client:
    """
    Initialize and return a Supabase client.
    Reads credentials from Streamlit secrets or environment variables.
    """
    try:
        # Prefer Streamlit secrets
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        # Fallback to environment variables
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        st.error("❌ Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY.")
        return None

    return create_client(url, key)

# Create a global client instance
supabase = init_connection()
