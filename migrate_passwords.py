import os
import bcrypt
from supabase import create_client

# Initialize Supabase client (adjust with your project URL and key)
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def migrate_passwords():
    # Fetch all users
    users = supabase.table("user_roles_locations").select("*").execute().data

    for user in users:
        plaintext_pw = user.get("password")
        hashed_pw = user.get("password_hash")

        # Only migrate if plaintext exists and hash is missing
        if plaintext_pw and not hashed_pw:
            new_hash = hash_password(plaintext_pw)
            supabase.table("user_roles_locations") \
                .update({"password_hash": new_hash}) \
                .eq("id", user["id"]) \
                .execute()
            print(f"Migrated user {user['user_name']}")

    print("✅ Migration complete. All plaintext passwords hashed.")

if __name__ == "__main__":
    migrate_passwords()
