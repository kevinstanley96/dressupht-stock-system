import streamlit as st
import pandas as pd
from datetime import datetime
import pandas as pd
from pytz import timezone

haiti_tz = timezone("America/Port-au-Prince")

# Initialize Square client once
square_client = Client(
    access_token="YOUR_SQUARE_ACCESS_TOKEN",
    environment="production"   # or "sandbox" if testing
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
        # --- Fetch inventory from Square ---
        # Get all locations from Square
        locs = square_client.locations.list_locations()
        if locs.is_error():
            raise Exception(f"Square error: {locs.errors}")

        # Find the matching Square location
        location_id = None
        for loc in locs.body["locations"]:
            if loc["name"] == location_name:
                location_id = loc["id"]
                break
        if not location_id:
            raise Exception(f"Location {location_name} not found in Square")

        # Pull inventory counts for that location
        inv_res = square_client.inventory.batch_retrieve_inventory_counts(
            body={"location_ids": [location_id]}
        )
        if inv_res.is_error():
            raise Exception(f"Square inventory error: {inv_res.errors}")

        counts = inv_res.body["counts"]

        # --- Transform into DataFrame ---
        df = pd.DataFrame(counts)
        df["Location"] = location_name
        # Map Square fields to your schema
        df = df.rename(columns={
            "catalog_object_id": "square_item_id",
            "quantity": "Stock"
        })
        df["Stock"] = pd.to_numeric(df["Stock"], errors="coerce").fillna(0).astype(int)
        df["Price"] = 0.0  # Square inventory counts don’t include price; fill later if needed
        df["Category"] = "Uncategorized"
        df["Token"] = "NO_TOKEN"
        df["Full Name"] = df["square_item_id"]  # placeholder if no name field

        records = df[["SKU","Full Name","Category","Stock","Price","Location","Token","square_item_id"]].to_dict(orient="records")

        # --- Save to Supabase ---
        supabase.table("Master_Inventory").upsert(records).execute()

        # --- Log sync ---
        now_ht = datetime.now(haiti_tz).isoformat()
        supabase.table("sync_log").insert({
            "location": location_name,
            "synced_at": now_ht,
            "type": "AUTO"
        }).execute()

        return True

    except Exception as e:
        print(f"Error syncing inventory: {e}")
        return False
