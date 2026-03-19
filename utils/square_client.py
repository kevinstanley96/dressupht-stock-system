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
        environment = st.secrets.get("SQUARE_ENVIRONMENT", "PRODUCTION")
    except Exception:
        access_token = os.getenv("SQUARE_TOKEN") or os.getenv("SQUARE_ACCESS_TOKEN")
        environment = os.getenv("SQUARE_ENVIRONMENT", "PRODUCTION")

    if not access_token:
        st.error("❌ Square credentials not found.")
        return None

    # Use uppercase constants for environment
    env = SquareEnvironment.PRODUCTION if environment.upper() == "PRODUCTION" else SquareEnvironment.SANDBOX

    return Square(
        token=access_token,
        environment=env
    )

# Global client instance
square_client = init_square_client()
