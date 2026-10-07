from __future__ import annotations

from typing import Any

from modules.supabase_manager import (
    create_authenticated_client,
    create_supabase_client,
)


# =========================================================
# CONSTANTS
# =========================================================

VALID_ROLES = {
    "user",
    "admin",
}


# =========================================================
# SQLITE COMPATIBILITY
# =========================================================

def init_auth_database() -> None:
    """
    Authentication is now handled by Supabase.
    Kept only so old imports do not fail.
    """

    return None


# =========================================================
# HELPERS
# =========================================================

def normalize_email(
    email: str,
) -> str:
    return str(
        email or ""
    ).strip().lower()


def normalize_username(
    username: str,
) -> str:
    return str(
        username or ""
    ).strip()


def normalize_role(
    role: Any,
) -> str:

    clean_role = str(
        role or "user"
    ).strip().lower()

    if clean_role not in VALID_ROLES:
        return "user"

    return clean_role


# =========================================================
# VALIDATION
# =========================================================

def validate_username(
    username: str,
) -> tuple[bool, str]:

    username = normalize_username(
        username
    )

    if not username:
        return (
            False,
            "Username is required.",
        )

    if len(username) < 3:
        return (
            False,
            "Username must contain at least 3 characters.",
        )

    if len(username) > 30:
        return (
            False,
            "Username is too long.",
        )

    cleaned = (
        username
        .replace("_", "")
        .replace("-", "")
    )

    if not cleaned.isalnum():
        return (
            False,
            "Username can contain only letters, "
            "numbers, underscore and hyphen.",
        )

    return (
        True,
        "Valid username.",
    )


def validate_email(
    email: str,
) -> tuple[bool, str]:

    email = normalize_email(
        email
    )

    if not email:
        return (
            False,
            "Email is required.",
        )

    if email.count("@") != 1:
        return (
            False,
            "Please enter a valid email.",
        )

    local_part, domain = email.split(
        "@",
        1,
    )

    if (
        not local_part
        or not domain
        or "." not in domain
    ):
        return (
            False,
            "Please enter a valid email.",
        )

    return (
        True,
        "Valid email.",
    )


def validate_password(
    password: str,
) -> tuple[bool, str]:

    if not password:
        return (
            False,
            "Password is required.",
        )

    if len(password) < 8:
        return (
            False,
            "Password must contain at least 8 characters.",
        )

    return (
        True,
        "Valid password.",
    )


# =========================================================
# GET PROFILE
# =========================================================

def get_user_profile(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> dict[str, Any]:
    """
    Read application profile from public.profiles.
    """

    clean_user_id = str(
        user_id or ""
    ).strip()

    if not clean_user_id:
        raise ValueError(
            "User ID is required."
        )

    client = create_authenticated_client(
        access_token=access_token,
        refresh_token=refresh_token,
    )

    response = (
        client
        .table("profiles")
        .select(
            "id, username, role, created_at"
        )
        .eq(
            "id",
            clean_user_id,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return {
            "id": clean_user_id,
            "username": "User",
            "role": "user",
            "created_at": "",
        }

    profile = response.data[0]

    return {
        "id": str(
            profile.get(
                "id",
                clean_user_id,
            )
        ),

        "username": str(
            profile.get(
                "username",
                "User",
            )
        ),

        "role": normalize_role(
            profile.get(
                "role",
                "user",
            )
        ),

        "created_at": str(
            profile.get(
                "created_at",
                "",
            )
        ),
    }


# =========================================================
# REGISTER USER
# =========================================================

def register_user(
    username: str,
    email: str,
    password: str,
    confirm_password: str,
) -> tuple[bool, str]:
    """
    Register new account using Supabase Auth.
    """

    username_ok, message = (
        validate_username(
            username
        )
    )

    if not username_ok:
        return (
            False,
            message,
        )

    email_ok, message = (
        validate_email(
            email
        )
    )

    if not email_ok:
        return (
            False,
            message,
        )

    password_ok, message = (
        validate_password(
            password
        )
    )

    if not password_ok:
        return (
            False,
            message,
        )

    if password != confirm_password:
        return (
            False,
            "Password and confirm password do not match.",
        )

    clean_username = normalize_username(
        username
    )

    clean_email = normalize_email(
        email
    )

    try:

        client = create_supabase_client()

        response = client.auth.sign_up(
            {
                "email": clean_email,

                "password": password,

                "options": {
                    "data": {
                        "username": clean_username,
                    }
                },
            }
        )

        if response.user is None:
            return (
                False,
                "Unable to create account.",
            )

        if response.session is None:
            return (
                True,
                "Account created. "
                "Please confirm your email before login.",
            )

        return (
            True,
            "Account created successfully. "
            "You can login now.",
        )

    except Exception as error:

        print(
            f"REGISTER ERROR: {error}"
        )

        return (
            False,
            f"Registration failed: {error}",
        )


# =========================================================
# AUTHENTICATE USER
# =========================================================

def authenticate_user(
    email: str,
    password: str,
) -> dict[str, Any] | None:
    """
    Login existing user using Supabase Auth.
    """

    clean_email = normalize_email(
        email
    )

    if not clean_email:
        print(
            "LOGIN ERROR: Email is empty."
        )
        return None

    if not password:
        print(
            "LOGIN ERROR: Password is empty."
        )
        return None

    try:

        client = create_supabase_client()

        response = (
            client.auth.sign_in_with_password(
                {
                    "email": clean_email,
                    "password": password,
                }
            )
        )

        if response.user is None:
            print(
                "LOGIN ERROR: Supabase returned no user."
            )
            return None

        if response.session is None:
            print(
                "LOGIN ERROR: Supabase returned no session."
            )
            return None

        user_id = str(
            response.user.id
        )

        access_token = str(
            response.session.access_token
        )

        refresh_token = str(
            response.session.refresh_token
        )

        profile = get_user_profile(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )

        email_value = (
            response.user.email
            or clean_email
        )

        return {
            "id": user_id,

            "username": profile.get(
                "username",
                "User",
            ),

            "email": str(
                email_value
            ),

            "role": normalize_role(
                profile.get(
                    "role",
                    "user",
                )
            ),

            "created_at": profile.get(
                "created_at",
                "",
            ),

            "access_token": (
                access_token
            ),

            "refresh_token": (
                refresh_token
            ),
        }

    except Exception as error:

        print(
            f"LOGIN ERROR: {error}"
        )

        return None


# =========================================================
# RESTORE SESSION
# =========================================================

def restore_user_session(
    access_token: str,
    refresh_token: str,
) -> dict[str, Any] | None:
    """
    Restore Supabase login session.
    """

    if not access_token:
        return None

    if not refresh_token:
        return None

    try:

        client = create_authenticated_client(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        user_response = (
            client.auth.get_user()
        )

        if user_response.user is None:
            return None

        session = (
            client.auth.get_session()
        )

        if session is None:
            return None

        user_id = str(
            user_response.user.id
        )

        current_access_token = str(
            session.access_token
        )

        current_refresh_token = str(
            session.refresh_token
        )

        profile = get_user_profile(
            user_id=user_id,
            access_token=current_access_token,
            refresh_token=current_refresh_token,
        )

        return {
            "id": user_id,

            "username": profile.get(
                "username",
                "User",
            ),

            "email": str(
                user_response.user.email
                or ""
            ),

            "role": normalize_role(
                profile.get(
                    "role",
                    "user",
                )
            ),

            "created_at": profile.get(
                "created_at",
                "",
            ),

            "access_token": (
                current_access_token
            ),

            "refresh_token": (
                current_refresh_token
            ),
        }

    except Exception as error:

        print(
            f"SESSION RESTORE ERROR: {error}"
        )

        return None


# =========================================================
# LOGOUT
# =========================================================

def logout_user(
    access_token: str,
    refresh_token: str,
) -> bool:
    """
    Logout Supabase user.
    """

    if not access_token:
        return False

    if not refresh_token:
        return False

    try:

        client = create_authenticated_client(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        client.auth.sign_out()

        return True

    except Exception as error:

        print(
            f"LOGOUT ERROR: {error}"
        )

        return False


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(
    user_id: str,
    access_token: str,
    refresh_token: str,
) -> bool:

    try:

        profile = get_user_profile(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )

        return (
            profile.get(
                "role",
                "user",
            )
            == "admin"
        )

    except Exception:

        return False