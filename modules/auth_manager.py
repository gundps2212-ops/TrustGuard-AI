from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_DIRECTORY = (
    PROJECT_ROOT / "database"
)

DATABASE_PATH = (
    DATABASE_DIRECTORY / "trustguard.db"
)

PASSWORD_ITERATIONS = 200_000

VALID_ROLES = {
    "user",
    "admin",
}


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection() -> sqlite3.Connection:
    """
    Create and return a SQLite database connection.
    """

    DATABASE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=10,
    )

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_auth_database() -> None:
    """
    Create the users table.

    For older databases, automatically add the role column.
    """

    create_table_query = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        password_salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TEXT NOT NULL
    )
    """

    with get_connection() as connection:
        connection.execute(
            create_table_query
        )

        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

        # Migration for old database
        if "role" not in existing_columns:
            connection.execute(
                """
                ALTER TABLE users
                ADD COLUMN role TEXT NOT NULL DEFAULT 'user'
                """
            )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_users_email
            ON users(email)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_users_username
            ON users(username)
            """
        )

        connection.commit()


# =========================================================
# PASSWORD HASHING
# =========================================================

def hash_password(
    password: str,
    salt: bytes | None = None,
) -> tuple[str, str]:
    """
    Hash a password using PBKDF2-HMAC-SHA256.

    Returns:
        password_hash_hex
        password_salt_hex
    """

    if not isinstance(password, str):
        raise TypeError(
            "Password must be a string."
        )

    if salt is None:
        salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )

    return (
        password_hash.hex(),
        salt.hex(),
    )


def verify_password(
    entered_password: str,
    stored_hash: str,
    stored_salt: str,
) -> bool:
    """
    Verify an entered password against the saved hash.
    """

    try:
        salt_bytes = bytes.fromhex(
            stored_salt
        )

        entered_hash, _ = hash_password(
            password=entered_password,
            salt=salt_bytes,
        )

        return hmac.compare_digest(
            entered_hash,
            stored_hash,
        )

    except (
        TypeError,
        ValueError,
    ):
        return False


# =========================================================
# VALIDATION FUNCTIONS
# =========================================================

def normalize_username(
    username: str,
) -> str:
    """
    Remove extra spaces from username.
    """

    return username.strip()


def normalize_email(
    email: str,
) -> str:
    """
    Normalize email address.
    """

    return email.strip().lower()


def validate_username(
    username: str,
) -> tuple[bool, str]:
    """
    Validate username.
    """

    clean_username = normalize_username(
        username
    )

    if not clean_username:
        return (
            False,
            "Username is required.",
        )

    if len(clean_username) < 3:
        return (
            False,
            "Username must contain at least 3 characters.",
        )

    if len(clean_username) > 30:
        return (
            False,
            "Username must contain at most 30 characters.",
        )

    allowed_characters = (
        clean_username
        .replace("_", "")
        .replace("-", "")
    )

    if not allowed_characters.isalnum():
        return (
            False,
            "Username can contain only letters, numbers, "
            "underscore and hyphen.",
        )

    return (
        True,
        "Username is valid.",
    )


def validate_email(
    email: str,
) -> tuple[bool, str]:
    """
    Perform basic email validation.
    """

    clean_email = normalize_email(
        email
    )

    if not clean_email:
        return (
            False,
            "Email address is required.",
        )

    if len(clean_email) > 254:
        return (
            False,
            "Email address is too long.",
        )

    if clean_email.count("@") != 1:
        return (
            False,
            "Please enter a valid email address.",
        )

    local_part, domain_part = clean_email.split(
        "@",
        maxsplit=1,
    )

    if not local_part:
        return (
            False,
            "Email username is missing.",
        )

    if (
        not domain_part
        or "." not in domain_part
    ):
        return (
            False,
            "Please enter a valid email domain.",
        )

    if domain_part.startswith("."):
        return (
            False,
            "Please enter a valid email address.",
        )

    if domain_part.endswith("."):
        return (
            False,
            "Please enter a valid email address.",
        )

    return (
        True,
        "Email address is valid.",
    )


def validate_password(
    password: str,
) -> tuple[bool, str]:
    """
    Validate password strength.
    """

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

    if len(password) > 128:
        return (
            False,
            "Password must contain at most 128 characters.",
        )

    has_uppercase = any(
        character.isupper()
        for character in password
    )

    has_lowercase = any(
        character.islower()
        for character in password
    )

    has_number = any(
        character.isdigit()
        for character in password
    )

    if not has_uppercase:
        return (
            False,
            "Password must contain at least one uppercase letter.",
        )

    if not has_lowercase:
        return (
            False,
            "Password must contain at least one lowercase letter.",
        )

    if not has_number:
        return (
            False,
            "Password must contain at least one number.",
        )

    return (
        True,
        "Password is valid.",
    )


def validate_registration(
    username: str,
    email: str,
    password: str,
    confirm_password: str,
) -> tuple[bool, str]:
    """
    Validate registration form fields.
    """

    username_valid, username_message = (
        validate_username(
            username
        )
    )

    if not username_valid:
        return (
            False,
            username_message,
        )

    email_valid, email_message = (
        validate_email(
            email
        )
    )

    if not email_valid:
        return (
            False,
            email_message,
        )

    password_valid, password_message = (
        validate_password(
            password
        )
    )

    if not password_valid:
        return (
            False,
            password_message,
        )

    if password != confirm_password:
        return (
            False,
            "Password and confirm password do not match.",
        )

    return (
        True,
        "Registration information is valid.",
    )


# =========================================================
# USER LOOKUP FUNCTIONS
# =========================================================

def username_exists(
    username: str,
) -> bool:
    """
    Check whether username already exists.
    """

    clean_username = normalize_username(
        username
    ).lower()

    query = """
    SELECT id
    FROM users
    WHERE LOWER(username) = ?
    LIMIT 1
    """

    with get_connection() as connection:
        row = connection.execute(
            query,
            (clean_username,),
        ).fetchone()

    return row is not None


def email_exists(
    email: str,
) -> bool:
    """
    Check whether email address already exists.
    """

    clean_email = normalize_email(
        email
    )

    query = """
    SELECT id
    FROM users
    WHERE LOWER(email) = ?
    LIMIT 1
    """

    with get_connection() as connection:
        row = connection.execute(
            query,
            (clean_email,),
        ).fetchone()

    return row is not None


def get_user_by_id(
    user_id: int,
) -> dict[str, Any] | None:
    """
    Get public user information using user ID.
    """

    if not isinstance(user_id, int):
        return None

    if user_id <= 0:
        return None

    query = """
    SELECT
        id,
        username,
        email,
        role,
        created_at
    FROM users
    WHERE id = ?
    LIMIT 1
    """

    with get_connection() as connection:
        row = connection.execute(
            query,
            (user_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


# =========================================================
# USER REGISTRATION
# =========================================================

def register_user(
    username: str,
    email: str,
    password: str,
    confirm_password: str,
) -> tuple[bool, str]:
    """
    Register a new TrustGuard AI user.
    """

    init_auth_database()

    is_valid, validation_message = (
        validate_registration(
            username=username,
            email=email,
            password=password,
            confirm_password=confirm_password,
        )
    )

    if not is_valid:
        return (
            False,
            validation_message,
        )

    clean_username = normalize_username(
        username
    )

    clean_email = normalize_email(
        email
    )

    if username_exists(clean_username):
        return (
            False,
            "This username is already registered.",
        )

    if email_exists(clean_email):
        return (
            False,
            "This email address is already registered.",
        )

    password_hash, password_salt = (
        hash_password(
            password
        )
    )

    created_at = datetime.now().isoformat(
        timespec="seconds"
    )

    insert_query = """
    INSERT INTO users (
        username,
        email,
        password_hash,
        password_salt,
        role,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """

    values = (
        clean_username,
        clean_email,
        password_hash,
        password_salt,
        "user",
        created_at,
    )

    try:
        with get_connection() as connection:
            connection.execute(
                insert_query,
                values,
            )

            connection.commit()

        return (
            True,
            "Account created successfully. You can now log in.",
        )

    except sqlite3.IntegrityError as error:
        error_message = str(
            error
        ).lower()

        if "username" in error_message:
            return (
                False,
                "This username is already registered.",
            )

        if "email" in error_message:
            return (
                False,
                "This email address is already registered.",
            )

        return (
            False,
            "Unable to create the account.",
        )

    except sqlite3.Error as error:
        return (
            False,
            f"Database error: {error}",
        )


# =========================================================
# USER LOGIN
# =========================================================

def authenticate_user(
    username_or_email: str,
    password: str,
) -> dict[str, Any] | None:
    """
    Authenticate user using username or email.

    Returns:
        User dictionary when authentication succeeds.
        None when authentication fails.
    """

    init_auth_database()

    login_value = (
        username_or_email
        .strip()
        .lower()
    )

    if not login_value:
        return None

    if not password:
        return None

    query = """
    SELECT
        id,
        username,
        email,
        role,
        password_hash,
        password_salt,
        created_at
    FROM users
    WHERE LOWER(username) = ?
       OR LOWER(email) = ?
    LIMIT 1
    """

    with get_connection() as connection:
        row = connection.execute(
            query,
            (
                login_value,
                login_value,
            ),
        ).fetchone()

    if row is None:
        return None

    password_is_correct = verify_password(
        entered_password=password,
        stored_hash=row["password_hash"],
        stored_salt=row["password_salt"],
    )

    if not password_is_correct:
        return None

    role = row["role"] or "user"

    if role not in VALID_ROLES:
        role = "user"

    return {
        "id": int(row["id"]),
        "username": row["username"],
        "email": row["email"],
        "role": role,
        "created_at": row["created_at"],
    }


# =========================================================
# ADMIN FUNCTIONS
# =========================================================

def promote_user_to_admin(
    email: str,
) -> tuple[bool, str]:
    """
    Promote an existing account to admin using email.
    """

    init_auth_database()

    clean_email = normalize_email(
        email
    )

    if not clean_email:
        return (
            False,
            "Email address is required.",
        )

    query = """
    UPDATE users
    SET role = 'admin'
    WHERE LOWER(email) = ?
    """

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                query,
                (clean_email,),
            )

            connection.commit()

        if cursor.rowcount == 0:
            return (
                False,
                "No registered account was found "
                "with this email address.",
            )

        return (
            True,
            "User account promoted to admin successfully.",
        )

    except sqlite3.Error as error:
        return (
            False,
            f"Database error: {error}",
        )


def demote_admin_to_user(
    email: str,
) -> tuple[bool, str]:
    """
    Change an admin account back to a normal user.
    """

    init_auth_database()

    clean_email = normalize_email(
        email
    )

    if not clean_email:
        return (
            False,
            "Email address is required.",
        )

    query = """
    UPDATE users
    SET role = 'user'
    WHERE LOWER(email) = ?
    """

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                query,
                (clean_email,),
            )

            connection.commit()

        if cursor.rowcount == 0:
            return (
                False,
                "No registered account was found "
                "with this email address.",
            )

        return (
            True,
            "Admin account changed to a normal user.",
        )

    except sqlite3.Error as error:
        return (
            False,
            f"Database error: {error}",
        )


def get_all_users(
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Return users for the Admin Dashboard.

    Password hashes and salts are not returned.
    """

    try:
        safe_limit = int(limit)
    except (TypeError, ValueError):
        safe_limit = 100

    safe_limit = max(
        1,
        min(safe_limit, 500),
    )

    query = """
    SELECT
        id,
        username,
        email,
        role,
        created_at
    FROM users
    ORDER BY id DESC
    LIMIT ?
    """

    with get_connection() as connection:
        rows = connection.execute(
            query,
            (safe_limit,),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def count_users() -> int:
    """
    Return total number of registered users.
    """

    query = """
    SELECT COUNT(*) AS total_users
    FROM users
    """

    with get_connection() as connection:
        row = connection.execute(
            query
        ).fetchone()

    if row is None:
        return 0

    return int(
        row["total_users"] or 0
    )