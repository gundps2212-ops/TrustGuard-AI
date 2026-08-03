import pandas as pd
import streamlit as st

from modules.admin_manager import (
    change_user_role,
    delete_user_account,
    get_admin_statistics,
    get_claim_status_distribution,
    get_recent_users,
    get_recent_verifications,
    get_score_distribution,
    get_user_activity,
    get_user_details,
)
from modules.auth_manager import init_auth_database
from modules.database_manager import init_database


st.set_page_config(
    page_title="Admin Dashboard",
    page_icon="📊",
    layout="wide",
)


init_database()
init_auth_database()


# =========================================================
# ACCESS PROTECTION
# =========================================================

if not st.session_state.get(
    "logged_in",
    False,
):
    st.warning(
        "Please login from the main TrustGuard AI page."
    )
    st.stop()


if (
    st.session_state.get(
        "user_role",
        "user",
    )
    != "admin"
):
    st.error(
        "Access denied. This page is available only "
        "to administrator accounts."
    )

    st.info(
        "Login using an admin account to access "
        "system analytics."
    )

    st.stop()
# =========================================================
# USER MANAGEMENT
# =========================================================

st.divider()

st.write("## ⚙️ User Management")

st.warning(
    "Role changes and account deletion are sensitive "
    "administrative actions. Check the selected user carefully."
)

management_users = get_user_activity()

current_admin_id = int(
    st.session_state.get(
        "user_id",
        0,
    )
)

manageable_users = [
    user
    for user in management_users
    if int(user["user_id"]) != current_admin_id
]


if not manageable_users:
    st.info(
        "No other user accounts are available to manage."
    )

else:
    user_options = {
        (
            f"{user['username']} | "
            f"{user['email']} | "
            f"Role: {user['role']} | "
            f"ID: {user['user_id']}"
        ): int(user["user_id"])
        for user in manageable_users
    }

    selected_user_label = st.selectbox(
        label="Select user account",
        options=list(
            user_options.keys()
        ),
        key="admin_selected_user",
    )

    selected_user_id = user_options[
        selected_user_label
    ]

    selected_user = get_user_details(
        selected_user_id
    )

    if selected_user is None:
        st.error(
            "Selected user account could not be loaded."
        )

    else:
        st.write("### Selected User Details")

        (
            username_column,
            role_column,
            verification_column,
            score_column,
        ) = st.columns(4)

        with username_column:
            st.metric(
                label="Username",
                value=selected_user[
                    "username"
                ],
            )

        with role_column:
            st.metric(
                label="Current Role",
                value=str(
                    selected_user["role"]
                ).title(),
            )

        with verification_column:
            st.metric(
                label="Verifications",
                value=selected_user[
                    "verification_count"
                ],
            )

        with score_column:
            st.metric(
                label="Average Trust Score",
                value=(
                    f"{float(selected_user['average_trust_score']):.2f}%"
                ),
            )

        detail_column_1, detail_column_2 = (
            st.columns(2)
        )

        with detail_column_1:
            st.write(
                f"**Email:** "
                f"{selected_user['email']}"
            )

            st.write(
                f"**Registered At:** "
                f"{selected_user['created_at']}"
            )

        with detail_column_2:
            st.write(
                f"**Last Verification:** "
                f"{selected_user['last_verification'] or 'None'}"
            )

            st.write(
                f"**User ID:** "
                f"{selected_user['id']}"
            )

        # =============================================
        # ROLE MANAGEMENT
        # =============================================

        st.write("### Change User Role")

        current_role = (
            selected_user["role"]
            or "user"
        )

        default_role_index = (
            1
            if current_role == "admin"
            else 0
        )

        with st.form(
            key=(
                f"role_form_"
                f"{selected_user_id}"
            )
        ):
            selected_new_role = st.selectbox(
                label="New account role",
                options=[
                    "user",
                    "admin",
                ],
                index=default_role_index,
            )

            confirm_role_change = st.checkbox(
                "I confirm this role change"
            )

            change_role_button = (
                st.form_submit_button(
                    label="Update User Role",
                    use_container_width=True,
                    type="primary",
                    disabled=(
                        not confirm_role_change
                    ),
                )
            )

        if change_role_button:
            success, message = change_user_role(
                target_user_id=selected_user_id,
                new_role=selected_new_role,
                acting_admin_id=current_admin_id,
            )

            if success:
                st.success(message)
                st.rerun()

            else:
                st.error(message)

        # =============================================
        # DELETE ACCOUNT
        # =============================================

        st.write("### Delete User Account")

        st.error(
            "Deleting an account cannot be undone."
        )

        with st.form(
            key=(
                f"delete_user_form_"
                f"{selected_user_id}"
            )
        ):
            history_option = st.radio(
                label=(
                    "What should happen to this "
                    "user's verification history?"
                ),
                options=[
                    (
                        "Preserve reports anonymously"
                    ),
                    (
                        "Permanently delete all reports"
                    ),
                ],
            )

            confirmation_text = st.text_input(
                label=(
                    "Type the selected username "
                    "to confirm deletion"
                ),
                placeholder=selected_user[
                    "username"
                ],
            )

            delete_confirmation = st.checkbox(
                "I understand that this action cannot be undone"
            )

            delete_user_button = (
                st.form_submit_button(
                    label="Delete User Account",
                    use_container_width=True,
                )
            )

        if delete_user_button:
            username_matches = (
                confirmation_text.strip()
                == selected_user[
                    "username"
                ]
            )

            if not delete_confirmation:
                st.error(
                    "Please select the deletion "
                    "confirmation checkbox."
                )

            elif not username_matches:
                st.error(
                    "Entered username does not match "
                    "the selected account."
                )

            else:
                should_delete_history = (
                    history_option
                    == "Permanently delete all reports"
                )

                success, message = (
                    delete_user_account(
                        target_user_id=(
                            selected_user_id
                        ),
                        acting_admin_id=(
                            current_admin_id
                        ),
                        delete_verification_history=(
                            should_delete_history
                        ),
                    )
                )

                if success:
                    st.success(message)
                    st.rerun()

                else:
                    st.error(message)

# =========================================================
# PAGE HEADER
# =========================================================

st.title("📊 TrustGuard AI Admin Dashboard")

st.write(
    f"Administrator: "
    f"**{st.session_state.get('username', 'Admin')}**"
)

st.write(
    "View user registrations, verification activity, "
    "trust scores and claim statistics."
)

st.divider()


# =========================================================
# MAIN STATISTICS
# =========================================================

statistics = get_admin_statistics()

(
    users_column,
    reports_column,
    active_column,
    score_column,
) = st.columns(4)


with users_column:
    st.metric(
        label="Total Users",
        value=statistics["total_users"],
    )


with reports_column:
    st.metric(
        label="Total Verifications",
        value=statistics[
            "total_verifications"
        ],
    )


with active_column:
    st.metric(
        label="Active Users",
        value=statistics["active_users"],
    )


with score_column:
    st.metric(
        label="Average Trust Score",
        value=(
            f"{statistics['average_score']:.2f}%"
        ),
    )


highest_column, lowest_column = st.columns(2)


with highest_column:
    st.metric(
        label="Highest Trust Score",
        value=f"{statistics['highest_score']}%",
    )


with lowest_column:
    st.metric(
        label="Lowest Trust Score",
        value=f"{statistics['lowest_score']}%",
    )


st.divider()


# =========================================================
# CLAIM STATUS DISTRIBUTION
# =========================================================

st.write("## 🔎 Claim Status Distribution")

claim_status_data = get_claim_status_distribution()

claim_status_dataframe = pd.DataFrame(
    claim_status_data
)

if claim_status_dataframe.empty:
    st.info(
        "No claim verification data is available."
    )
else:
    status_columns = st.columns(
        len(claim_status_data)
    )

    for column, item in zip(
        status_columns,
        claim_status_data,
    ):
        with column:
            st.metric(
                label=item["status"],
                value=item["claim_count"],
            )

    chart_dataframe = (
        claim_status_dataframe
        .set_index("status")
    )

    st.bar_chart(
        chart_dataframe,
        y="claim_count",
    )


st.divider()


# =========================================================
# TRUST SCORE DISTRIBUTION
# =========================================================

st.write("## 🛡️ Trust Score Distribution")

score_distribution = get_score_distribution()

score_dataframe = pd.DataFrame(
    score_distribution
)

if score_dataframe.empty:
    st.info(
        "No verification score data is available."
    )
else:
    st.bar_chart(
        score_dataframe.set_index(
            "score_range"
        ),
        y="report_count",
    )

    st.dataframe(
        score_dataframe,
        use_container_width=True,
        hide_index=True,
        column_config={
            "score_range": "Trust Score Range",
            "report_count": "Report Count",
        },
    )


st.divider()


# =========================================================
# USER ACTIVITY
# =========================================================

st.write("## 👥 User Activity")

user_activity = get_user_activity()

if not user_activity:
    st.info(
        "No registered user data is available."
    )
else:
    st.dataframe(
        user_activity,
        use_container_width=True,
        hide_index=True,
        column_config={
            "user_id": "User ID",
            "username": "Username",
            "email": "Email",
            "role": "Role",
            "verification_count": (
                "Verification Count"
            ),
            "average_trust_score": (
                st.column_config.ProgressColumn(
                    "Average Trust Score",
                    min_value=0,
                    max_value=100,
                    format="%.2f%%",
                )
            ),
            "last_verification": (
                "Last Verification"
            ),
        },
    )


st.divider()


# =========================================================
# RECENT VERIFICATIONS
# =========================================================

st.write("## 📚 Recent Verification Reports")

recent_verifications = get_recent_verifications(
    limit=30
)

if not recent_verifications:
    st.info(
        "No verification reports are available."
    )
else:
    st.dataframe(
        recent_verifications,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": "Record ID",
            "username": "User",
            "created_at": "Generated At",
            "document_name": "Document",
            "question": "Question",
            "overall_score": (
                st.column_config.ProgressColumn(
                    "Trust Score",
                    min_value=0,
                    max_value=100,
                    format="%d%%",
                )
            ),
            "trust_level": "Trust Level",
        },
    )


st.divider()


# =========================================================
# RECENT USERS
# =========================================================

st.write("## 🆕 Recently Registered Users")

recent_users = get_recent_users(
    limit=20
)

if not recent_users:
    st.info(
        "No user accounts are available."
    )
else:
    st.dataframe(
        recent_users,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": "User ID",
            "username": "Username",
            "email": "Email",
            "role": "Role",
            "created_at": "Registered At",
        },
    )


st.divider()

st.info(
    "The Admin Dashboard is read-only. "
    "It displays system analytics without deleting "
    "or modifying user reports."
)