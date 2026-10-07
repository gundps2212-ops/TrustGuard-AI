from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


# =========================================================
# PROJECT ROOT
# =========================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT_DIR),
    )

load_dotenv(
    ROOT_DIR / ".env"
)


# =========================================================
# OUTPUT HELPERS
# =========================================================

def success(message: str) -> None:
    print(
        f"[OK] {message}"
    )


def failure(message: str) -> None:
    print(
        f"[ERROR] {message}"
    )


def warning(message: str) -> None:
    print(
        f"[WARNING] {message}"
    )


# =========================================================
# ENVIRONMENT CHECK
# =========================================================

def check_environment() -> bool:
    print(
        "\n=== ENVIRONMENT CHECK ==="
    )

    required_variables = [
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
        "GEMINI_API_KEY",
    ]

    optional_variables = [
        "GROQ_API_KEY",
        "TAVILY_API_KEY",
    ]

    passed = True

    for variable in required_variables:

        value = os.getenv(
            variable
        )

        if value:
            success(
                f"{variable} configured"
            )

        else:
            failure(
                f"{variable} missing"
            )
            passed = False

    for variable in optional_variables:

        value = os.getenv(
            variable
        )

        if value:
            success(
                f"{variable} configured"
            )

        else:
            warning(
                f"{variable} not configured"
            )

    return passed


# =========================================================
# MODULE IMPORT CHECK
# =========================================================

def check_modules() -> bool:
    print(
        "\n=== MODULE IMPORT CHECK ==="
    )

    modules = [
        "modules.config",
        "modules.supabase_manager",
        "modules.auth_manager",
        "modules.database_manager",
        "modules.admin_manager",
        "modules.evaluation_manager",
        "modules.claim_extractor",
        "modules.evidence_retriever",
        "modules.llm",
        "modules.llm_comparison",
        "modules.pdf_reader",
        "modules.report_generator",
        "modules.pdf_report_generator",
        "modules.score",
        "modules.verifier",
        "modules.web_retriever",
    ]

    passed = True

    for module_name in modules:

        try:
            importlib.import_module(
                module_name
            )

            success(
                f"{module_name} imported"
            )

        except Exception as error:
            failure(
                f"{module_name}: {error}"
            )
            passed = False

    return passed


# =========================================================
# REQUIRED FUNCTIONS CHECK
# =========================================================

def check_functions() -> bool:
    print(
        "\n=== FUNCTION CHECK ==="
    )

    requirements = {

        "modules.auth_manager": [
            "authenticate_user",
            "register_user",
            "logout_user",
            "restore_user_session",
            "get_user_profile",
        ],

        "modules.supabase_manager": [
            "create_supabase_client",
            "create_authenticated_client",
        ],

        "modules.database_manager": [
            "save_verification",
            "get_verification_history",
            "get_verification_details",
            "delete_verification",
        ],

        "modules.evaluation_manager": [
            "save_ground_truth_labels",
            "get_report_evaluation_labels",
            "get_evaluation_rows",
            "calculate_evaluation_metrics",
        ],

        "modules.admin_manager": [
            "get_admin_statistics",
            "get_recent_users",
            "get_recent_verifications",
            "get_user_activity",
            "get_score_distribution",
            "get_claim_status_distribution",
            "get_user_details",
            "change_user_role",
        ],
    }

    passed = True

    for module_name, functions in requirements.items():

        try:
            module = importlib.import_module(
                module_name
            )

        except Exception as error:
            failure(
                f"Cannot import {module_name}: {error}"
            )
            passed = False
            continue

        for function_name in functions:

            if hasattr(
                module,
                function_name,
            ):
                success(
                    f"{module_name}.{function_name}"
                )

            else:
                failure(
                    f"{module_name}.{function_name} missing"
                )
                passed = False

    return passed


# =========================================================
# LEGACY SQLITE CHECK
# =========================================================

def check_legacy_sqlite() -> bool:
    print(
        "\n=== LEGACY SQLITE CHECK ==="
    )

    active_files = [
        ROOT_DIR / "app.py",
        ROOT_DIR / "modules" / "auth_manager.py",
        ROOT_DIR / "modules" / "admin_manager.py",
        ROOT_DIR / "modules" / "database_manager.py",
        ROOT_DIR / "modules" / "evaluation_manager.py",
        ROOT_DIR / "pages" / "1_Verification_History.py",
        ROOT_DIR / "pages" / "2_Admin_Dashboard.py",
        ROOT_DIR / "pages" / "3_Evaluation_Dashboard.py",
    ]

    forbidden_patterns = [
        "get_connection",
        "sqlite3",
    ]

    passed = True

    for file_path in active_files:

        if not file_path.exists():
            warning(
                f"{file_path.name} not found"
            )
            continue

        try:
            text = file_path.read_text(
                encoding="utf-8"
            )

        except Exception as error:
            failure(
                f"Cannot read {file_path}: {error}"
            )
            passed = False
            continue

        for pattern in forbidden_patterns:

            if pattern in text:
                failure(
                    f"{pattern} found in {file_path}"
                )
                passed = False

    if passed:
        success(
            "No active SQLite/get_connection code found"
        )

    return passed


# =========================================================
# PAGE CHECK
# =========================================================

def check_pages() -> bool:
    print(
        "\n=== STREAMLIT PAGE CHECK ==="
    )

    required_pages = [
        ROOT_DIR / "app.py",
        ROOT_DIR
        / "pages"
        / "1_Verification_History.py",
        ROOT_DIR
        / "pages"
        / "2_Admin_Dashboard.py",
        ROOT_DIR
        / "pages"
        / "3_Evaluation_Dashboard.py",
    ]

    passed = True

    for page in required_pages:

        if page.exists():
            success(
                f"{page.name} exists"
            )

        else:
            failure(
                f"{page.name} missing"
            )
            passed = False

    return passed


# =========================================================
# MAIN
# =========================================================

def main() -> None:
    print(
        "\n================================="
    )
    print(
        " TRUSTGUARD AI SYSTEM CHECK"
    )
    print(
        "================================="
    )

    results = [
        check_environment(),
        check_modules(),
        check_functions(),
        check_legacy_sqlite(),
        check_pages(),
    ]

    print(
        "\n================================="
    )

    if all(results):

        print(
            "ALL CORE CHECKS PASSED"
        )

    else:

        print(
            "SOME CHECKS FAILED"
        )
        print(
            "Fix [ERROR] items before deployment."
        )

    print(
        "=================================\n"
    )


if __name__ == "__main__":
    main()