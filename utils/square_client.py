import streamlit as st
import os
from square.client import Client

def init_square_client() -> Client:
    """
    Initialize and return a Square client.
    Reads credentials from Streamlit secrets or environment variables.
    """
    try:
        # Prefer Streamlit secrets
        access_token = st.secrets["SQUARE_ACCESS_TOKEN"]
        environment = st.secrets.get("SQUARE_ENVIRONMENT", "production")
    except Exception:
        # Fallback to environment variables
        access_token = os.getenv("SQUARE_ACCESS_TOKEN")
        environment = os.getenv("SQUARE_ENVIRONMENT", "production")

    if not access_token:
        st.error("❌ Square credentials not found. Please set SQUARE_ACCESS_TOKEN.")
        return None

    return Client(
        access_token=access_token,
        environment=environment
    )

# Create a global client instance
square_client = init_square_client()
