import streamlit as st
import pandas as pd
from datetime import datetime
import pandas as pd
from pytz import timezone

haiti_tz = timezone("America/Port-au-Prince")

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

def sync_inventory(supabase, square_client):
    """
    Sync Square orders with Supabase Master_Inventory.
    - Uses Option 3: always resolve Token at sync time.
    - Logs each sale into Supabase Sales table for audit.
    """
    try:
        # Get Square locations
        locations_response = square_client.locations.list()
        location_lookup = {loc.id: loc.name for loc in locations_response.locations}
        location_ids = list(location_lookup.keys())

        # Fetch recent orders
        response = square_client.orders.search(location_ids=location_ids, limit=200)
        if not response.orders:
            return []

        today = datetime.now(haiti_tz).date()
        synced_sales = []

        for order in response.orders:
            created_dt = datetime.fromisoformat(order.created_at.replace("Z","+00:00")).astimezone(haiti_tz)
            if created_dt.date() != today:
                continue

            if order.line_items:
                for item in order.line_items:
                    qty_sold = int(item.quantity)
                    product_name = item.name or ""
                    product_token = item.catalog_object_id

                    # Default values
                    token = "NO_TOKEN"
                    category = "Unknown"
                    location_name = location_lookup.get(order.location_id,"Unknown")

                    # Option 3: resolve Token at sync time
                    inv_result = supabase.table("Master_Inventory").select("Full Name, SKU, Category, Location, Token").eq("Token", product_token).execute()
                    if inv_result.data:
                        inv_info = inv_result.data[0]
                        category = inv_info["Category"]
                        location_name = inv_info["Location"]
                        token = inv_info["Token"]
                    else:
                        # fallback by product name
                        if product_name.strip():
                            inv_result = supabase.table("Master_Inventory").select("Full Name, SKU, Category, Location, Token").eq("Full Name", product_name.strip()).execute()
                            if inv_result.data:
                                inv_info = inv_result.data[0]
                                category = inv_info["Category"]
                                location_name = inv_info["Location"]
                                token = inv_info["Token"] or "NO_TOKEN"

                    sale_entry = {
                        "date": created_dt.strftime("%Y-%m-%d"),
                        "time": created_dt.strftime("%H:%M:%S"),
                        "location": location_name,
                        "category": category,
                        "product": f"{qty_sold} × {product_name if product_name else 'Unknown'}",
                        "token": token,
                        "state": order.state
                    }

                    # Insert into Supabase Sales table
                    supabase.table("Sales").insert(sale_entry).execute()
                    synced_sales.append(sale_entry)

        return synced_sales

    except Exception as e:
        st.error(f"Error syncing inventory: {e}")
        return []
