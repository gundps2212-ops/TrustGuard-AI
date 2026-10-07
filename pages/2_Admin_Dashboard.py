from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.admin_manager import (
    change_user_role,
    get_admin_statistics,
    get_claim_status_distribution,
    get_recent_users,
    get_recent_verifications,
    get_score_distribution,
    get_user_activity,
    get_user_details,
)


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Admin Dashboard",
    page_icon="📊",
    layout="wide",
)


# =========================================================
# LOGIN CHECK
# =========================================================

if not st.session_state.get(
    "logged_in",
    False,
):
    st.warning(
        "Please login from the main TrustGuard AI page."
    )

    st.stop()


# =========================================================
# SUPABASE SESSION
# =========================================================

admin_user_id = st.session_state.get(
    "user_id"
)

username = st.session_state.get(
    "username",
    "Admin",
)

user_role = st.session_state.get(
    "user_role",
    "user",
)

access_token = st.session_state.get(
    "access_token",
    "",
)

refresh_token = st.session_state.get(
    "refresh_token",
    "",
)


# =========================================================
# ADMIN ACCESS CHECK
# =========================================================

if not admin_user_id:
    st.error(
        "Invalid Supabase user session."
    )
    st.stop()


if not access_token or not refresh_token:
    st.error(
        "Supabase authentication tokens are missing. "
        "Please logout and login again."
    )
    st.stop()


if user_role != "admin":
    st.error(
        "Access denied. This page is available "
        "only for administrator accounts."
    )
    st.stop()


# =========================================================
# HEADER
# =========================================================

st.title(
    "📊 TrustGuard AI Admin Dashboard"
)

st.success(
    f"Logged in as Administrator: {username}"
)

st.write(
    "Monitor users, verification activity, "
    "trust scores, evaluation data and user roles."
)

st.divider()


# =========================================================
# MAIN STATISTICS
# =========================================================

try:
    statistics = get_admin_statistics(
        user_id=admin_user_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )

except Exception as error:
    st.error(
        "Unable to load Admin Dashboard."
    )

    st.code(
        str(error)
    )

    st.stop()


st.write(
    "## 📌 System Overview"
)


(
    users_column,
    verification_column,
    active_column,
    evaluation_column,
) = st.columns(4)


with users_column:
    st.metric(
        label="Total Users",
        value=statistics[
            "total_users"
        ],
    )


with verification_column:
    st.metric(
        label="Total Verifications",
        value=statistics[
            "total_verifications"
        ],
    )


with active_column:
    st.metric(
        label="Active Users",
        value=statistics[
            "active_users"
        ],
    )


with evaluation_column:
    st.metric(
        label="Evaluated Claims",
        value=statistics[
            "total_evaluated_claims"
        ],
    )


(
    average_column,
    highest_column,
    lowest_column,
) = st.columns(3)


with average_column:
    st.metric(
        label="Average Trust Score",
        value=(
            f"{statistics['average_score']:.2f}%"
        ),
    )


with highest_column:
    st.metric(
        label="Highest Trust Score",
        value=(
            f"{statistics['highest_score']}%"
        ),
    )


with lowest_column:
    st.metric(
        label="Lowest Trust Score",
        value=(
            f"{statistics['lowest_score']}%"
        ),
    )


st.divider()


# =========================================================
# CLAIM STATUS DISTRIBUTION
# =========================================================

st.write(
    "## 🔎 Claim Status Distribution"
)


try:
    claim_status_data = (
        get_claim_status_distribution(
            user_id=admin_user_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )
    )

except Exception as error:
    claim_status_data = []

    st.warning(
        f"Unable to load claim analytics: {error}"
    )


if claim_status_data:

    status_columns = st.columns(
        len(
            claim_status_data
        )
    )


    for column, item in zip(
        status_columns,
        claim_status_data,
    ):

        with column:
            st.metric(
                label=item[
                    "status"
                ],
                value=item[
                    "claim_count"
                ],
            )


    claim_dataframe = pd.DataFrame(
        claim_status_data
    )


    st.bar_chart(
        claim_dataframe.set_index(
            "status"
        ),
        y="claim_count",
    )


else:
    st.info(
        "No claim analytics are available."
    )


st.divider()


# =========================================================
# SCORE DISTRIBUTION
# =========================================================

st.write(
    "## 🛡️ Trust Score Distribution"
)


score_distribution = get_score_distribution(
    user_id=admin_user_id,
    access_token=access_token,
    refresh_token=refresh_token,
)


score_dataframe = pd.DataFrame(
    score_distribution
)


if not score_dataframe.empty:

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
    )


st.divider()


# =========================================================
# USER ACTIVITY
# =========================================================

st.write(
    "## 👥 User Activity"
)


user_activity = get_user_activity(
    user_id=admin_user_id,
    access_token=access_token,
    refresh_token=refresh_token,
)


if not user_activity:

    st.info(
        "No registered users are available."
    )


else:

    st.dataframe(
        user_activity,
        use_container_width=True,
        hide_index=True,

        column_config={
            "user_id": (
                "Supabase User UUID"
            ),

            "username": (
                "Username"
            ),

            "role": (
                "Role"
            ),

            "registered_at": (
                "Registered At"
            ),

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

st.write(
    "## 📚 Recent Verification Reports"
)


recent_verifications = (
    get_recent_verifications(
        user_id=admin_user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        limit=30,
    )
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
            "id": (
                "Report ID"
            ),

            "username": (
                "User"
            ),

            "created_at": (
                "Generated At"
            ),

            "document_name": (
                "Document"
            ),

            "question": (
                "Question"
            ),

            "overall_score": (
                st.column_config.ProgressColumn(
                    "Trust Score",
                    min_value=0,
                    max_value=100,
                    format="%d%%",
                )
            ),

            "trust_level": (
                "Trust Level"
            ),
        },
    )


st.divider()


# =========================================================
# RECENT USERS
# =========================================================

st.write(
    "## 🆕 Recent Users"
)


recent_users = get_recent_users(
    user_id=admin_user_id,
    access_token=access_token,
    refresh_token=refresh_token,
    limit=20,
)


if recent_users:

    st.dataframe(
        recent_users,
        use_container_width=True,
        hide_index=True,

        column_config={
            "id": (
                "Supabase UUID"
            ),

            "username": (
                "Username"
            ),

            "role": (
                "Role"
            ),

            "created_at": (
                "Registered At"
            ),
        },
    )


st.divider()


# =========================================================
# USER ROLE MANAGEMENT
# =========================================================

st.write(
    "## ⚙️ User Role Management"
)


manageable_users = [
    user
    for user in user_activity
    if str(
        user["user_id"]
    )
    != str(
        admin_user_id
    )
]


if not manageable_users:

    st.info(
        "No other user accounts are available "
        "for role management."
    )


else:

    user_options = {
        (
            f"{user['username']} | "
            f"Role: {user['role']} | "
            f"Reports: "
            f"{user['verification_count']}"
        ): user[
            "user_id"
        ]

        for user
        in manageable_users
    }


    selected_user_label = st.selectbox(
        label="Select user",
        options=list(
            user_options.keys()
        ),
    )


    selected_user_id = user_options[
        selected_user_label
    ]


    selected_user = get_user_details(
        target_user_id=(
            selected_user_id
        ),
        acting_admin_id=(
            admin_user_id
        ),
        access_token=(
            access_token
        ),
        refresh_token=(
            refresh_token
        ),
    )


    if selected_user:

        st.write(
            "### Selected User"
        )


        (
            selected_name_column,
            selected_role_column,
            selected_reports_column,
            selected_score_column,
        ) = st.columns(4)


        with selected_name_column:

            st.metric(
                label="Username",
                value=selected_user[
                    "username"
                ],
            )


        with selected_role_column:

            st.metric(
                label="Current Role",
                value=str(
                    selected_user[
                        "role"
                    ]
                ).title(),
            )


        with selected_reports_column:

            st.metric(
                label="Verifications",
                value=selected_user[
                    "verification_count"
                ],
            )


        with selected_score_column:

            st.metric(
                label="Average Score",
                value=(
                    f"{selected_user['average_trust_score']:.2f}%"
                ),
            )


        current_role = str(
            selected_user[
                "role"
            ]
        ).lower()


        default_role_index = (
            1
            if current_role
            == "admin"
            else 0
        )


        with st.form(
            key=(
                "change_role_form_"
                f"{selected_user_id}"
            )
        ):

            new_role = st.selectbox(
                label="New Role",
                options=[
                    "user",
                    "admin",
                ],
                index=(
                    default_role_index
                ),
            )


            confirmation = st.checkbox(
                "I confirm this role change."
            )


            update_role_button = (
                st.form_submit_button(
                    label=(
                        "Update User Role"
                    ),
                    use_container_width=True,
                    type="primary",
                    disabled=(
                        not confirmation
                    ),
                )
            )


        if update_role_button:

            success, message = (
                change_user_role(
                    target_user_id=(
                        selected_user_id
                    ),
                    new_role=(
                        new_role
                    ),
                    acting_admin_id=(
                        admin_user_id
                    ),
                    access_token=(
                        access_token
                    ),
                    refresh_token=(
                        refresh_token
                    ),
                )
            )


            if success:

                st.success(
                    message
                )

                st.rerun()


            else:

                st.error(
                    message
                )


st.divider()


# =========================================================
# SECURITY
# =========================================================

st.info(
    "Admin analytics use the logged-in Supabase "
    "session and Row Level Security. "
    "Secret/service-role keys are not used by "
    "this dashboard."
)