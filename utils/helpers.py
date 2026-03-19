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

    if not st.session_state.authenticated:
        st.title("🔑 Login")
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type="password")

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

def sync_inventory(location_name, supabase):
    try:
        st.sidebar.info(f"🔄 Starting sync for {location_name}...")
        progress = st.progress(0)

        # --- Get Square locations ---
        locs = square_client.locations.list()
        if locs.errors:
            st.sidebar.error(f"❌ Square error: {locs.errors}")
            return False

        # Find matching Square location ID
        location_id = None
        for loc in locs.body["locations"]:
            if (loc.get("name") or "").strip() == location_name.strip():
                location_id = loc["id"]
                break
        if not location_id:
            st.sidebar.error(f"❌ Location '{location_name}' not found in Square.")
            return False

        progress.progress(20)

        # --- Pull inventory counts (new logic) ---
        inv_res = square_client.inventory.batch_retrieve_inventory_counts(
            body={"location_ids": [location_id]}
        )
        if inv_res.errors:
            st.sidebar.error(f"❌ Square inventory error: {inv_res.errors}")
            return False

        counts = inv_res.body.get("counts", [])
        df = pd.DataFrame(counts)
        if not df.empty:
            df["Location"] = location_name
            df = df.rename(columns={
                "catalog_object_id": "square_item_id",
                "quantity": "Stock"
            })
            df["Stock"] = pd.to_numeric(df["Stock"], errors="coerce").fillna(0).astype(int)
            df["Price"] = 0.0
            df["Category"] = "Uncategorized"
            df["Token"] = "NO_TOKEN"
            df["Full Name"] = df["square_item_id"]

            records = df[["Full Name","Category","Stock","Price","Location","Token","square_item_id"]].to_dict(orient="records")
            supabase.table("Master_Inventory").upsert(records).execute()

        progress.progress(40)

        # --- Order‑based sync (old logic) ---
        # Get last sync times
        last_ssd = supabase.table("sync_log").select("synced_at").eq("location", location_name).eq("type","SSD").order("synced_at", desc=True).limit(1).execute()
        last_mise = supabase.table("sync_log").select("synced_at").eq("location", location_name).eq("type","MISE").order("synced_at", desc=True).limit(1).execute()

        cutoff_time = None
        for res in (last_ssd, last_mise):
            if res.data:
                synced_at = res.data[0].get("synced_at")
                if synced_at:
                    cutoff_time = datetime.fromisoformat(synced_at).astimezone(haiti_tz)
                    break

        progress.progress(50)

        # Fetch orders
        orders_res = square_client.orders.search(location_ids=[location_id], limit=200)
        if orders_res.errors:
            st.sidebar.error(f"❌ Square orders error: {orders_res.errors}")
            return False

        updates = []
        if orders_res.body.get("orders"):
            for order in orders_res.body["orders"]:
                created_dt = datetime.fromisoformat(order["created_at"].replace("Z","+00:00")).astimezone(haiti_tz)
                if cutoff_time and created_dt <= cutoff_time:
                    continue

                if order.get("line_items"):
                    for item in order["line_items"]:
                        qty_sold = int(item["quantity"])
                        product_name = (item.get("name") or "").strip()
                        product_token = (item.get("catalog_object_id") or "").strip()

                        # Update inventory stock
                        current = supabase.table("Master_Inventory").select("Stock").eq("Token", product_token).execute()
                        if current.data:
                            new_qty = current.data[0]["Stock"] - qty_sold
                            supabase.table("Master_Inventory").update({"Stock": new_qty}).eq("Token", product_token).execute()

                        # Log sale
                        supabase.table("Sales").upsert({
                            "order_id": order["id"],
                            "location": location_name,
                            "product_token": product_token if product_token else None,
                            "product_name": product_name,
                            "quantity": qty_sold,
                            "unit_price": float(item["base_price_money"]["amount"]) / 100 if item.get("base_price_money") else None,
                            "total_amount": float(item["total_money"]["amount"]) / 100 if item.get("total_money") else None,
                            "category": "Uncategorized",
                            "state": order.get("state"),
                            "created_at": created_dt.isoformat(),
                            "updated_at": datetime.now(haiti_tz).isoformat()
                        }, on_conflict=["order_id","product_token"]).execute()

                updates.append(order["id"])

        progress.progress(80)

        # --- Log sync ---
        supabase.table("sync_log").insert({
            "location": location_name,
            "synced_at": datetime.now(haiti_tz).isoformat(),
            "type": "SSD"
        }).execute()

        progress.progress(100)
        st.sidebar.success(f"✅ {location_name}: Inventory synced ({len(updates)} new orders, {len(counts)} items updated).")
        return True

    except Exception as e:
        st.sidebar.error(f"❌ Error syncing {location_name}: {e}")
        return False
