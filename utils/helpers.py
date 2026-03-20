import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, date
import time
import io
import re
import os
from square import Square
from square.environment import SquareEnvironment
import pytz

# Import the global supabase client
from utils.supabase_client import supabase

# Import the Square client
from utils.square_client import square_client

# --- Timezone ---
haiti_tz = pytz.timezone("America/Port-au-Prince")

# --- Square connection ---
# Load your token from environment or Streamlit secrets
SQUARE_TOKEN = os.getenv("SQUARE_TOKEN") or st.secrets["SQUARE_ACCESS_TOKEN"]

# Initialize Square client (sandbox for testing, production when live)
square_client = Square(
    token=SQUARE_TOKEN,
    environment=SquareEnvironment.PRODUCTION   # or SquareEnvironment.SANDBOX
)

# --- LOGIN ---
def login_user(supabase):
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.role = None
        st.session_state.location = None

        if st.button("Login"):
            result = supabase.table("user_roles_locations").select("*").eq("user_name", username_input).execute()
            if not result.data:
                st.error("Invalid username")
                return None

            user = result.data[0]
            stored_pw = user.get("password")

            if stored_pw and password_input == stored_pw:
                st.success(f"Welcome {user['user_name']}!")
                st.session_state.authenticated = True
                st.session_state.username = user["user_name"]
                st.session_state.role = user["role"]
                st.session_state.location = user["location"]
                st.rerun()
            else:
                st.error("Invalid password")

        return None
    else:
        return (
            st.session_state.username,
            st.session_state.role,
            st.session_state.location,
        )

# --- LOCATION ACCESS ---
def get_allowed_locations(supabase, username):
    """Return all locations assigned to a user."""
    try:
        result = supabase.table("user_roles_locations") \
                         .select("location") \
                         .eq("user_name", username) \
                         .execute()
        return [row["location"] for row in result.data] if result.data else []
    except Exception:
        return []

def clean_and_combine(file_cv, file_pv):
    def process_file(file, loc_name):
        df = pd.read_excel(file, skiprows=1)
        df.columns = [str(c).strip() for c in df.columns]

        # Column mapping
        mapping = {
            'Item Name': 'Full Name',
            'SKU': 'SKU',
            'Categories': 'Category',
            'Price': 'Price',
            'Token': 'Token',              # Matches Square Excel
            'Square Item ID': 'square_item_id'  # ✅ new mapping if present
        }
        df = df.rename(columns=mapping)

        # Stock column depends on location
        stock_col = "Current Quantity Dressup Haiti" if loc_name == "Canape-Vert" else "Current Quantity Dressupht Pv"

        # Ensure required columns exist
        if 'Token' not in df.columns:
            df['Token'] = "NO_TOKEN"
        if 'square_item_id' not in df.columns:
            df['square_item_id'] = "NO_ID"

        # Clean and normalize fields
        df['Stock'] = pd.to_numeric(df[stock_col], errors='coerce').fillna(0).astype(int) if stock_col in df.columns else 0
        df['SKU'] = df['SKU'].astype(str).str.strip().replace(['nan', ''], 'NO_SKU')
        df['Category'] = df['Category'].fillna("Uncategorized").astype(str)
        df['Location'] = loc_name
        df['Price'] = pd.to_numeric(df.get('Price', 0), errors='coerce').fillna(0.0)

        return df[['SKU', 'Full Name', 'Stock', 'Price', 'Category', 'Location', 'Token', 'square_item_id']].copy()

    df1 = process_file(file_cv, "Canape-Vert")
    df2 = process_file(file_pv, "Pv")
    return pd.concat([df1, df2], ignore_index=True)

# Map internal names → Square names
LOCATION_MAP = {
    "Canape-Vert": "Dressup Haiti",
    "Pv": "Dressupht Pv",
    "Dressupht Pv": "Dressupht Pv"   # ✅ add this line
}

# --- SAFE DATAFRAME DISPLAY ---
def safe_dataframe(df, cols, empty_msg="No data available."):
    """Safely display a dataframe with selected columns."""
    if df is not None and not df.empty:
        st.dataframe(df[cols], width="stretch", hide_index=True)
    else:
        st.info(empty_msg)

# --- SEARCH INVENTORY ---
def search_inventory(df, query):
    """Search inventory dataframe by SKU, Full Name, Token, or Category."""
    if df is None or df.empty or not query.strip():
        return pd.DataFrame()
    q = query.strip().lower()
    return df[
        df['Full Name'].str.lower().str.contains(q, na=False) |
        df['SKU'].str.lower().str.contains(q, na=False) |
        df.get('Token', pd.Series("", index=df.index)).str.lower().str.contains(q, na=False) |
        df.get('Category', pd.Series("", index=df.index)).str.lower().str.contains(q, na=False)
    ]

# --- SANITIZE SHEET NAME ---
def sanitize_sheet_name(name):
    """Ensure Excel sheet names are valid (<=31 chars, no special chars)."""
    invalid_chars = ['\\','/','*','?','[',']',':']
    safe = ''.join(c for c in name if c not in invalid_chars)
    return safe[:31]

# --- NORMALIZE LOCATION ---
def normalize_location(loc):
    """Normalize location names for consistency."""
    if not loc:
        return "Unknown"
    loc = loc.strip().lower()
    if "pv" in loc:
        return "Pv"
    if "canape" in loc or "cv" in loc:
        return "Canape-Vert"
    return loc.title()

# --- HIGH STOCK ALERT ---
def show_high_stock_alert(df, location, threshold=50):
    """Display items with stock above threshold."""
    if df is not None and not df.empty:
        high_stock = df[df['Stock'] > threshold]
        if not high_stock.empty:
            st.warning(f"⚠️ {len(high_stock)} items in {location} exceed {threshold} units")
            st.dataframe(high_stock[['SKU','Full Name','Stock']], width="stretch", hide_index=True)
        else:
            st.success(f"No items in {location} exceed {threshold} units")

def sync_inventory(location_name):
    try:
        # --- Get Square locations ---
        locations_response = square_client.locations.list()
        location_lookup = {loc.id: (loc.name or "") for loc in locations_response.locations}

        # --- Map normalized name back to Square’s actual name ---
        square_name = LOCATION_MAP.get(location_name, location_name or "Unknown")
        square_name = (square_name or "").strip()

        # --- Find matching Square location ID ---
        location_id = next(
            (lid for lid, lname in location_lookup.items() if (lname or "").strip() == square_name),
            None
        )
        if not location_id:
            st.sidebar.error(f"❌ Location '{square_name}' not found in Square.")
            return

        # --- Get last MISE time ---
        last_mise = supabase.table("sync_log") \
            .select("synced_at") \
            .eq("location", location_name) \
            .eq("type", "MISE") \
            .order("synced_at", desc=True) \
            .limit(1) \
            .execute()

        last_mise_time = None
        if last_mise.data:
            synced_at = last_mise.data[0].get("synced_at")
            if synced_at:
                last_mise_time = datetime.fromisoformat(synced_at).astimezone(haiti_tz)

        # --- Get last SSD time ---
        last_ssd = supabase.table("sync_log") \
            .select("synced_at") \
            .eq("location", location_name) \
            .eq("type", "SSD") \
            .order("synced_at", desc=True) \
            .limit(1) \
            .execute()

        last_ssd_time = None
        if last_ssd.data:
            synced_at = last_ssd.data[0].get("synced_at")
            if synced_at:
                last_ssd_time = datetime.fromisoformat(synced_at).astimezone(haiti_tz)

        # --- Determine cutoff time ---
        cutoff_time = last_ssd_time if last_ssd_time else last_mise_time

        # --- Progress bar for SSD ---
        progress = st.progress(0)
        progress.progress(20)

        # --- Fetch orders for this location ---
        response = square_client.orders.search(location_ids=[location_id], limit=200)
        progress.progress(40)

        if response.orders:
            updates = []
            for order in response.orders:
                created_dt = datetime.fromisoformat(order.created_at.replace("Z", "+00:00")).astimezone(haiti_tz)

                # ✅ Only process orders created AFTER cutoff
                if cutoff_time and created_dt <= cutoff_time:
                    continue

                if order.line_items:
                    for item in order.line_items:
                        qty_sold = int(item.quantity)
                        product_name = (item.name or "").strip()
                        product_token = (item.catalog_object_id or "").strip()

                        # --- Lookup category/location from Master_Inventory ---
                        category = "Uncategorized"
                        inv_result = supabase.table("Master_Inventory").select("Category, Location").eq("Token", product_token).execute()
                        if inv_result.data:
                            category = inv_result.data[0].get("Category", "Uncategorized")
                        elif product_name:
                            inv_result = supabase.table("Master_Inventory").select("Category, Location").eq("Full Name", product_name).execute()
                            if inv_result.data:
                                category = inv_result.data[0].get("Category", "Uncategorized")

                        # ✅ Update inventory stock
                        current = supabase.table("Master_Inventory").select("Stock").eq("Token", product_token).execute()
                        if current.data:
                            new_qty = current.data[0]["Stock"] - qty_sold
                            supabase.table("Master_Inventory").update({"Stock": new_qty}).eq("Token", product_token).execute()
                        else:
                            if product_name:
                                current = supabase.table("Master_Inventory").select("Stock").eq("Full Name", product_name).execute()
                                if current.data:
                                    new_qty = current.data[0]["Stock"] - qty_sold
                                    supabase.table("Master_Inventory").update({"Stock": new_qty}).eq("Full Name", product_name).execute()

                        # ✅ Log into sales table with upsert
                        supabase.table("Sales").upsert(
                            {
                                "order_id": order.id,
                                "location": location_name,
                                "product_token": product_token if product_token else None,
                                "product_name": product_name,
                                "quantity": qty_sold,
                                "unit_price": float(item.base_price_money.amount) / 100 if item.base_price_money else None,
                                "total_amount": float(item.total_money.amount) / 100 if item.total_money else None,
                                "category": category,
                                "state": order.state,
                                "created_at": created_dt.isoformat(),
                                "updated_at": datetime.now(haiti_tz).isoformat()
                            },
                            on_conflict="order_id,product_token"  # ✅ key fix
                        ).execute()

                updates.append(order.id)

            progress.progress(80)

            if updates:
                st.sidebar.success(f"✅ {location_name}: Inventory updated from {len(updates)} new orders")
                supabase.table("sync_log").insert({
                    "location": location_name,
                    "synced_at": datetime.now(haiti_tz).isoformat(),
                    "type": "SSD"
                }).execute()
            progress.progress(100)
        else:
            st.sidebar.info(f"No new orders found for {location_name}.")
            progress.progress(100)

    except Exception as e:
        st.sidebar.error(f"Error syncing {location_name}: {e}")
