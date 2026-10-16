import frappe
from frappe.utils import flt, getdate

GROUP_BY_OPTIONS = ("employee", "project", "date", "month")


def get_employee_group_field():
    meta = frappe.get_meta("Employee")

    if meta.has_field("employee_group"):
        return "employee_group"

    return None


def parse_group_by(value):
    """
    Accepts None, "project", "project,employee", '["project","employee"]'
    or a list. Returns an ordered list of unique, valid group levels.
    """
    if not value:
        return []

    if isinstance(value, str):
        value = value.strip()

        if value.startswith("["):
            value = frappe.parse_json(value)
        else:
            value = [part.strip() for part in value.split(",")]

    if not isinstance(value, (list, tuple)):
        frappe.throw("Group By must be provided as a list.")

    levels = [level for level in value if level]

    invalid = [level for level in levels if level not in GROUP_BY_OPTIONS]

    if invalid:
        frappe.throw(
            "Invalid Group By: "
            + ", ".join(invalid)
            + ". Allowed: "
            + ", ".join(GROUP_BY_OPTIONS)
            + "."
        )

    if len(set(levels)) != len(levels):
        frappe.throw("Group By levels must be unique.")

    return levels


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

    timesheets = frappe.get_all(
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

        matching_employees = frappe.get_all(
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

    timesheet_employee_ids = list({row.employee for row in timesheets})

    designation_map = {}

    if timesheet_employee_ids:
        designation_rows = frappe.get_all(
            "Employee",
            filters={"name": ["in", timesheet_employee_ids]},
            fields=["name", "designation"],
        )

        designation_map = {
            row.name: row.designation
            for row in designation_rows
        }

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

    projects = frappe.get_all(
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

    customers = frappe.get_all(
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
        doc = frappe.get_doc("Timesheet", timesheet_row.name)

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
                "designation": designation_map.get(doc.employee) or None,
                "status": doc.status,
                "detail_id": detail.name,
                "from_time": detail.from_time,
                "to_time": detail.to_time,
                "date": entry_date.isoformat(),
                "day_name": entry_date.strftime("%A"),
                "month": entry_date.strftime("%Y-%m"),
                "month_name": entry_date.strftime("%B %Y"),
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

    employee_dates = {}
    employee_project_dates = {}

    for row in rows:
        employee_dates.setdefault(row["employee"], set()).add(row["date"])
        employee_project_dates.setdefault(
            (row["employee"], row["project"]), set()
        ).add(row["date"])

    for row in rows:
        row["work_days"] = len(employee_dates[row["employee"]])
        row["project_work_days"] = len(
            employee_project_dates[(row["employee"], row["project"])]
        )

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

    work_dates = {
        row.get("date")
        for row in rows
        if row.get("date")
    }

    month_keys = {
        row.get("month")
        for row in rows
        if row.get("month")
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
        "total_work_days": len(work_dates),
        "total_months": len(month_keys),
        "total_hours": total_hours,
        "billable_hours": billable_hours,
        "non_billable_hours": non_billable_hours,
        "total_billable_amount": billable_amount,
        "total_costing_amount": costing_amount,
    }


def _group_identity(row, field):
    if field == "employee":
        group_id = row.get("employee") or "Unassigned"
        return group_id, row.get("employee_name") or group_id

    if field == "project":
        group_id = row.get("project") or "Unassigned"
        return group_id, row.get("project_name") or group_id

    if field == "month":
        group_id = row.get("month") or "Unassigned"
        return group_id, row.get("month_name") or group_id

    group_id = row.get("date") or "Unassigned"
    return group_id, group_id


def _aggregate(rows):
    total_hours = 0
    billable_hours = 0
    billable_amount = 0
    costing_amount = 0
    work_dates = set()

    for row in rows:
        hours = flt(row.get("hours"))

        total_hours += hours
        costing_amount += flt(row.get("costing_amount"))

        if row.get("is_billable"):
            billable_hours += hours
            billable_amount += flt(row.get("billing_amount"))

        if row.get("date"):
            work_dates.add(row["date"])

    return {
        "total_hours": total_hours,
        "billable_hours": billable_hours,
        "non_billable_hours": total_hours - billable_hours,
        "total_billable_amount": billable_amount,
        "total_costing_amount": costing_amount,
        "work_days": len(work_dates),
        "entry_count": len(rows),
    }


def _build_groups(rows, levels):
    field, remaining = levels[0], levels[1:]

    buckets = {}

    for row in rows:
        group_id, group_name = _group_identity(row, field)

        bucket = buckets.setdefault(
            group_id,
            {
                "name": group_name,
                "day_name": row.get("day_name") if field == "date" else None,
                "rows": [],
            },
        )

        bucket["rows"].append(row)

    result = []

    for group_id in sorted(buckets):
        bucket = buckets[group_id]

        node = {
            "group": bucket["name"],
            "group_id": group_id,
            "level": field,
            **_aggregate(bucket["rows"]),
        }

        if field == "date":
            node["day_name"] = bucket["day_name"]

        if remaining:
            node["children"] = _build_groups(bucket["rows"], remaining)
        else:
            node["entries"] = bucket["rows"]

        result.append(node)

    return result


def group_report_data(rows, group_by):
    """
    group_by: ordered list of levels, e.g. ["project", "employee"].
    Returns a nested tree. Every node carries its own totals; only the
    last level carries `entries`, the levels above carry `children`.
    """
    levels = parse_group_by(group_by)

    if not levels:
        return []

    return _build_groups(rows, levels)