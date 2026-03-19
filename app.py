import streamlit as st
import pandas as pd
from utils.supabase_client import supabase
from utils.square_client import square_client
from utils.translations import translations
from utils.helpers import login_user, get_allowed_locations

# --- PAGE CONFIG ---
st.set_page_config(page_title="Dressup Haiti Stock", layout="wide")

# --- LANGUAGE SELECTOR ---
lang = st.sidebar.selectbox("🌐 Language / Langue", ["en", "fr"])
t = translations[lang]

# --- LOGIN ---
login_result = login_user(supabase)
if not login_result or login_result[0] is None:
    st.stop()

username, role, location = login_result
loc_list = get_allowed_locations(supabase, username)

# --- ROLE-BASED TABS ---
role_tabs = {
    "Staff":   ["Library", "Mannequin", "Password"],
    "Manager": ["Library", "Arrival", "Inventory", "Mannequin", "Depot", "Transfer", "Compare", "Password"],
    "Admin":   ["Library", "Arrival", "Inventory", "Mannequin", "Depot", "Transfer", "Compare", "Sales", "Admin", "Password"]
}
tab_list = role_tabs.get(role, ["Library", "Password"])
tabs = st.tabs(tab_list)
tab_dict = {name: tabs[i] for i, name in enumerate(tab_list)}

# --- IMPORT TAB MODULES ---
from tabs import library, arrival, inventory, depot, mannequin, compare, transfer, sales, admin, password

# --- RENDER EACH TAB ---
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
    sales.render_tab(tab_dict["Sales"], supabase, username, role, loc_list, t)

if "Admin" in tab_dict:
    admin.render_tab(tab_dict["Admin"], supabase, username, role, loc_list, t)

if "Password" in tab_dict:
    password.render_tab(tab_dict["Password"], supabase, username, role, loc_list, t)
