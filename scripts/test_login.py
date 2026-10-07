from pathlib import Path
import sys
from getpass import getpass


# Project root add to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from modules.supabase_manager import create_supabase_client


email = input("Enter email: ").strip()
password = getpass("Enter password: ")


try:
    client = create_supabase_client()

    response = client.auth.sign_in_with_password(
        {
            "email": email,
            "password": password,
        }
    )

    print("\nLOGIN SUCCESS")

    if response.user:
        print("User ID:", response.user.id)
        print("Email:", response.user.email)

    if response.session:
        print("Session created: YES")
    else:
        print("Session created: NO")

except Exception as error:
    print("\nLOGIN FAILED")
    print("ERROR:", error)