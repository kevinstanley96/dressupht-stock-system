import streamlit as st
import os
from square import Square
from square.environment import SquareEnvironment

def init_square_client():
    """
    Initialize and return a Square client using the Square SDK v44+.
    """
    try:
        access_token = st.secrets["SQUARE_ACCESS_TOKEN"]
        environment = st.secrets.get("SQUARE_ENVIRONMENT", "production")
    except Exception:
        access_token = os.getenv("SQUARE_ACCESS_TOKEN")
        environment = os.getenv("SQUARE_ENVIRONMENT", "production")

    if not access_token:
        st.error("❌ Square credentials not found.")
        return None

    # Use lowercase attributes for SquareEnvironment
    env = SquareEnvironment.production if environment == "production" else SquareEnvironment.sandbox

    return Square(
        access_token=access_token,
        environment=env
    )

# Global client instance
square_client = init_square_client()
