from getpass import getpass

from modules.supabase_manager import (
    create_supabase_client,
)


def register_user():
    supabase = create_supabase_client()

    email = input(
        "Enter email: "
    ).strip()

    password = getpass(
        "Enter password: "
    )

    username = input(
        "Enter username: "
    ).strip()

    try:
        response = supabase.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "username": username,
                    }
                },
            }
        )

        if response.user:
            print("\nRegistration successful.")
            print(
                f"User ID: {response.user.id}"
            )

            if response.session:
                print(
                    "Session created successfully."
                )
                print(
                    "Email confirmation is not blocking login."
                )
            else:
                print(
                    "User created, but no session was returned."
                )
                print(
                    "Check Confirm Email setting."
                )

        else:
            print(
                "Registration failed."
            )

    except Exception as error:
        print(
            f"Registration Error: {error}"
        )


def login_user():
    supabase = create_supabase_client()

    email = input(
        "Enter registered email: "
    ).strip()

    password = getpass(
        "Enter registered password: "
    )

    try:
        response = (
            supabase.auth.sign_in_with_password(
                {
                    "email": email,
                    "password": password,
                }
            )
        )

        if response.user and response.session:
            print("\nLogin successful.")

            print(
                f"User ID: {response.user.id}"
            )

            print(
                f"Email: {response.user.email}"
            )

            print(
                "Access token created successfully."
            )

        else:
            print(
                "Login failed."
            )

    except Exception as error:
        print(
            f"Login Error: {error}"
        )


def main():
    print("\nTrustGuard AI - Supabase Test")
    print("=" * 40)

    print("1. Register")
    print("2. Login")

    choice = input(
        "Select option: "
    ).strip()

    if choice == "1":
        register_user()

    elif choice == "2":
        login_user()

    else:
        print(
            "Invalid option."
        )


if __name__ == "__main__":
    main()