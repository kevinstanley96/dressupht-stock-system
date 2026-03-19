import streamlit as st
from utils.supabase_client import supabase
from utils.square_client import square_client
from utils.helpers import login_user, get_allowed_locations
from utils.translations import get_translations
from utils.sidebar import render_sidebar

# Import all tab modules
from tabs import library, arrival, inventory, depot, mannequin, compare, transfer, sales, admin, password

# --- App Setup ---
st.set_page_config(page_title="DressUpHT Stock System", layout="wide")

# --- Language Selector ---
language = st.sidebar.selectbox("🌐 Language", ["en", "fr"], index=0)
t = get_translations(language)

# --- Authentication ---
user_info = login_user(supabase)
if not user_info:
    st.stop()

username, role, location = user_info
loc_list = get_allowed_locations(supabase, username)

# --- Sidebar (operational only, no login info) ---
with st.sidebar:
    render_sidebar(role, supabase)

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
