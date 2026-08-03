from pathlib import Path
import sys


# TrustGuard-AI project root Python path मध्ये add करा
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from modules.auth_manager import (
    init_auth_database,
    promote_user_to_admin,
)


def main() -> None:
    """
    Promote an existing TrustGuard AI user to admin.
    """

    init_auth_database()

    print("=" * 50)
    print("TrustGuard AI - Admin Account Setup")
    print("=" * 50)

    email = input(
        "Enter registered user email: "
    ).strip()

    if not email:
        print("\nERROR: Email address is required.")
        return

    success, message = promote_user_to_admin(
        email
    )

    if success:
        print(f"\nSUCCESS: {message}")
        print(
            "Logout and login again to activate admin access."
        )
    else:
        print(f"\nERROR: {message}")


if __name__ == "__main__":
    main()