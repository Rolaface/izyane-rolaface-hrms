import frappe
from frappe.utils import flt, getdate


def get_employee_group_field():
    meta = frappe.get_meta("Employee")

    if meta.has_field("employee_group"):
        return "employee_group"

    return None


def get_report_data(filters):
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))

    if from_date > to_date:
        frappe.throw("From Date cannot be after To Date.")

    employee_ids = filters.get("employees")
    employee = filters.get("employee")

    if isinstance(employee_ids, str):
        employee_ids = frappe.parse_json(employee_ids)

    if employee_ids is not None and not isinstance(
        employee_ids, (list, tuple)
    ):
        frappe.throw("Employees must be provided as a list.")

    if employee_ids:
        employee_ids = list(dict.fromkeys(employee_ids))

    timesheet_filters = {
        "docstatus": 1,
    }

    if employee_ids:
        timesheet_filters["employee"] = ["in", employee_ids]
    elif employee:
        timesheet_filters["employee"] = employee

    if filters.get("status"):
        timesheet_filters["status"] = filters["status"]

    timesheets = frappe.get_list(
        "Timesheet",
        filters=timesheet_filters,
        fields=[
            "name",
            "employee",
            "employee_name",
            "status",
        ],
        order_by="employee asc, name asc",
    )

    employee_group = filters.get("employee_group")

    if employee_group:
        group_field = get_employee_group_field()

        if not group_field:
            frappe.throw(
                "Employee Group filter is unavailable because the Employee "
                "DocType does not have an employee_group field."
            )

        matching_employees = frappe.get_list(
            "Employee",
            filters={group_field: employee_group},
            fields=["name"],
        )

        matching_employee_ids = {row.name for row in matching_employees}

        timesheets = [
            row
            for row in timesheets
            if row.employee in matching_employee_ids
        ]

    # ---- Project filter (single + multiple) ----
    project_ids_filter = filters.get("projects")

    if isinstance(project_ids_filter, str):
        project_ids_filter = frappe.parse_json(project_ids_filter)

    if project_ids_filter is not None and not isinstance(
        project_ids_filter, (list, tuple)
    ):
        frappe.throw("Projects must be provided as a list.")

    project_list = list(dict.fromkeys(project_ids_filter or []))

    if filters.get("project") and filters["project"] not in project_list:
        project_list.append(filters["project"])

    project_filters = {}

    if project_list:
        project_filters["name"] = ["in", project_list]

    if filters.get("customer"):
        project_filters["customer"] = filters["customer"]

    projects = frappe.get_list(
        "Project",
        filters=project_filters,
        fields=[
            "name",
            "project_name",
            "customer",
        ],
    )

    project_map = {project.name: project for project in projects}

    if project_list or filters.get("customer"):
        allowed_project_ids = set(project_map)
    else:
        allowed_project_ids = None

    customer_ids = {
        project.customer
        for project in projects
        if project.customer
    }

    customers = frappe.get_list(
        "Customer",
        filters={"name": ["in", list(customer_ids)]}
        if customer_ids
        else {"name": ["=", ""]},
        fields=["name", "customer_name"],
    )

    customer_map = {
        customer.name: customer.customer_name
        for customer in customers
    }

    rows = []

    for timesheet_row in timesheets:
        doc = frappe.get_doc(
            "Timesheet",
            timesheet_row.name,
            check_permission=True,
        )

        for detail in doc.get("time_logs", []):
            if not detail.from_time:
                continue

            entry_date = getdate(detail.from_time)

            if not (from_date <= entry_date <= to_date):
                continue

            project_id = detail.project

            if (
                allowed_project_ids is not None
                and project_id not in allowed_project_ids
            ):
                continue

            project = project_map.get(project_id)

            if filters.get("customer") and not project:
                continue

            task_name = None

            if detail.task:
                task_name = frappe.db.get_value(
                    "Task",
                    detail.task,
                    "subject",
                )

            hours = flt(detail.hours)
            is_billable = bool(detail.is_billable)

            if (
                filters.get("include_non_billable") in (0, "0", False)
                and not is_billable
            ):
                continue

            customer_id = project.customer if project else None

            rows.append({
                "timesheet": doc.name,
                "timesheet_title": doc.get("title"),
                "employee": doc.employee,
                "employee_name": doc.employee_name,
                "status": doc.status,
                "detail_id": detail.name,
                "from_time": detail.from_time,
                "to_time": detail.to_time,
                "date": entry_date.isoformat(),
                "day_name": entry_date.strftime("%A"),
                "hours": hours,
                "project": project_id,
                "project_name": project.project_name if project else None,
                "customer": customer_id,
                "customer_name": customer_map.get(customer_id),
                "task": detail.task,
                "task_name": task_name,
                "task_subject": task_name,
                "activity_type": detail.activity_type,
                "description": detail.description,
                "is_billable": is_billable,
                "billing_rate": flt(detail.billing_rate),
                "costing_rate": flt(detail.costing_rate),
                "billing_amount": flt(detail.billing_amount),
                "costing_amount": flt(detail.costing_amount),
                "completed": bool(detail.completed),
            })

    rows.sort(
        key=lambda row: (
            row.get("employee") or "",
            row.get("from_time") or "",
            row.get("timesheet") or "",
        )
    )

    return rows


def build_summary(rows):
    employee_ids = {
        row.get("employee")
        for row in rows
        if row.get("employee")
    }

    project_ids = {
        row.get("project")
        for row in rows
        if row.get("project")
    }

    total_hours = sum(flt(row.get("hours")) for row in rows)

    billable_hours = sum(
        flt(row.get("hours"))
        for row in rows
        if row.get("is_billable")
    )

    non_billable_hours = total_hours - billable_hours

    billable_amount = sum(
        flt(row.get("billing_amount"))
        for row in rows
        if row.get("is_billable")
    )

    costing_amount = sum(flt(row.get("costing_amount")) for row in rows)

    return {
        "total_entries": len(rows),
        "total_employees": len(employee_ids),
        "total_projects": len(project_ids),
        "total_hours": total_hours,
        "billable_hours": billable_hours,
        "non_billable_hours": non_billable_hours,
        "total_billable_amount": billable_amount,
        "total_costing_amount": costing_amount,
    }


def group_report_data(rows, group_by):
    if group_by not in ("employee", "project", "date"):
        group_by = "employee"

    grouped = {}

    for row in rows:
        if group_by == "employee":
            group_id = row.get("employee") or "Unassigned"
            group_name = row.get("employee_name") or group_id

        elif group_by == "project":
            group_id = row.get("project") or "Unassigned"
            group_name = row.get("project_name") or group_id

        else:
            group_id = row.get("date") or "Unassigned"
            group_name = group_id

            if row.get("day_name"):
                group_name = f"{group_id} ({row['day_name']})"

        if group_id not in grouped:
            grouped[group_id] = {
                "group": group_name,
                "group_id": group_id,
                "entries": [],
                "total_hours": 0,
                "billable_hours": 0,
                "non_billable_hours": 0,
                "total_billable_amount": 0,
            }

        group = grouped[group_id]

        group["entries"].append(row)
        group["total_hours"] += flt(row.get("hours"))

        if row.get("is_billable"):
            group["billable_hours"] += flt(row.get("hours"))
            group["total_billable_amount"] += flt(row.get("billing_amount"))
        else:
            group["non_billable_hours"] += flt(row.get("hours"))

    return list(grouped.values())