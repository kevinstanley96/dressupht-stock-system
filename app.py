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
st.set_page_config(
    page_title="DressUp Haiti Stock",
    page_icon="favicon.png",   # file in same folder as app.py
    layout="wide"
)

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

# --- TABS SETUP BASED ON ROLE ---
role_tabs = {
    "Staff":   ["Library", "Mannequin", "Password"],
    "Manager": ["Library", "Arrival", "Inventory", "Mannequin", "Depot", "Transfer", "Compare", "Password"],
    "Admin":   ["Library", "Arrival", "Inventory", "Mannequin", "Depot", "Transfer", "Compare", "Sales", "Admin", "Password"]
}

tab_list = role_tabs.get(role, ["Library", "Password"])
tabs = st.tabs(tab_list)
tab_dict = {name: tabs[i] for i, name in enumerate(tab_list)}

# --- After login succeeds ---
username, role, location = user_info
loc_list = get_allowed_locations(supabase, username)

# ✅ Show login info at the top of the main page
st.info(f"Logged in as {username} ({role}) — Locations: {', '.join(loc_list) if loc_list else 'None'}")

# --- Sidebar: operational tools + role indicator ---
with st.sidebar:
    st.markdown("### 👤 User Info")
    st.write(f"**Role:** {role}")

# --- Render Tabs (only those allowed) ---
if "Library" in tab_dict:
    library.render_tab(tab_dict["Library"], supabase, username, role, loc_list, t)
if "Arrival" in tab_dict:
    arrival.render_tab(tab_dict["Arrival"], supabase, username, role, loc_list, t)
if "Inventory" in tab_dict:
    inventory.render_tab(tab_dict["Inventory"], supabase, username, role, loc_list, t)
if "Depot" in tab_dict:
    depot.render_tab(tab_dict["Depot"], supabase, username, role, loc_list, t)
if "Mannequin" in tab_dict:
    mannequin.render_tab(tab_dict["Mannequin"], supabase, username, role, loc_list, t)
if "Compare" in tab_dict:
    compare.render_tab(tab_dict["Compare"], supabase, username, role, loc_list, t)
if "Transfer" in tab_dict:
    transfer.render_tab(tab_dict["Transfer"], supabase, username, role, loc_list, t)
if "Sales" in tab_dict:
    sales.render_tab(tab_dict["Sales"], supabase, square_client, username, role, loc_list, t)
if "Admin" in tab_dict:
    admin.render_tab(tab_dict["Admin"], supabase, username, role, loc_list, t)
if "Password" in tab_dict:
    password.render_tab(tab_dict["Password"], supabase, username, role, loc_list, t)
    st.write(f"**Allowed Tabs:** {', '.join(tab_list)}")
    st.write(f"**Locations:** {', '.join(loc_list) if loc_list else 'None'}")
    st.divider()
    render_sidebar(username, role, loc_list, supabase)
