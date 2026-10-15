import json

import frappe


def create_project_team_field():
    fields = [
        {
            "fieldname": "custom_project_team",
            "label": "Project Team",
            "fieldtype": "Table",
            "options": "Project User Details",
            "insert_after": "users",
        },
        {
            "fieldname": "custom_synced_team_users",
            "label": "Synchronized Team Users",
            "fieldtype": "Small Text",
            "hidden": 1,
            "read_only": 1,
        },
    ]

    for field in fields:
        field_name = field["fieldname"]

        if not frappe.db.exists(
            "Custom Field",
            f"Project-{field_name}",
        ):
            frappe.get_doc(
                {
                    "doctype": "Custom Field",
                    "dt": "Project",
                    **field,
                }
            ).insert(ignore_permissions=True)

    frappe.clear_cache(doctype="Project")


def sync_project_team_to_project_users(doc, method=None):
    team_users = {
        row.user
        for row in (doc.get("custom_project_team") or [])
        if row.user
    }

    try:
        previously_synced = set(
            json.loads(doc.get("custom_synced_team_users") or "[]")
        )
    except (TypeError, ValueError):
        previously_synced = set()

    existing_users = {
        row.user: row
        for row in (doc.get("users") or [])
        if row.user
    }

    for user in sorted(team_users):
        user_details = frappe.db.get_value(
            "User",
            user,
            ["full_name", "email", "user_image"],
            as_dict=True,
        )

        if user in existing_users:
            row = existing_users[user]
        else:
            row = doc.append(
                "users",
                {
                    "user": user,
                },
            )
            existing_users[user] = row

        if user_details:
            row.full_name = user_details.full_name or ""
            row.email = user_details.email or user
            row.image = user_details.user_image or ""

    for user in previously_synced - team_users:
        row = existing_users.get(user)

        if row and user in previously_synced:
            doc.users.remove(row)

    doc.custom_synced_team_users = json.dumps(sorted(team_users))