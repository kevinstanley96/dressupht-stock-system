import streamlit as st
import pandas as pd
from utils.supabase_client import supabase
from utils.square_client import square_client
from utils.helpers import login_user, get_allowed_locations
from utils.translations import get_translations
from utils.sidebar import render_sidebar
import base64

# Import all tab modules
from tabs import library, arrival, inventory, depot, mannequin, compare, transfer, sales, admin, password

# --- App Setup ---
st.set_page_config(page_title="DressUpHT Stock System", layout="wide")

# Load favicon from local file
with open("favicon.png", "rb") as f:
    favicon_data = f.read()
favicon_base64 = base64.b64encode(favicon_data).decode()

favicon_html = f"""
    <link rel="icon" type="image/x-icon" href="data:image/x-icon;base64,{favicon_base64}">
"""
st.markdown(favicon_html, unsafe_allow_html=True)

# --- Sidebar: Language selector only ---
language = st.sidebar.selectbox("🌐 Language / Langue", ["en", "fr"], index=0)
t = get_translations(language)

# --- Authentication ---
user_info = login_user(supabase)
if not user_info:
    # Show login form in main page, not sidebar
    st.title("🔑 Login")
    st.warning("Please log in to access the system.")
    st.stop()

# --- After login succeeds ---
username, role, location = user_info
loc_list = get_allowed_locations(supabase, username)

# ✅ Show login info at the top of the main page
st.info(f"Logged in as {username} ({role}) — Locations: {', '.join(loc_list) if loc_list else 'None'}")

# --- Sidebar: operational tools only ---
with st.sidebar:
    render_sidebar(username, role, loc_list, supabase)

# --- Tab Layout ---
tab_dict = st.tabs([
    "Library", "Arrival", "Inventory", "Depot", "Mannequin",
    "Compare", "Transfer", "Sales", "Admin", "Password"
])

# --- Render Tabs ---
library.render_tab(tab_dict[0], supabase, username, role, loc_list, t)
arrival.render_tab(tab_dict[1], supabase, username, role, loc_list, t)
inventory.render_tab(tab_dict[2], supabase, username, role, loc_list, t)
depot.render_tab(tab_dict[3], supabase, username, role, loc_list, t)
mannequin.render_tab(tab_dict[4], supabase, username, role, loc_list, t)
compare.render_tab(tab_dict[5], supabase, username, role, loc_list, t)
transfer.render_tab(tab_dict[6], supabase, username, role, loc_list, t)
sales.render_tab(tab_dict[7], supabase, square_client, username, role, loc_list, t)
admin.render_tab(tab_dict[8], supabase, username, role, loc_list, t)
password.render_tab(tab_dict[9], supabase, username, role, loc_list, t)
