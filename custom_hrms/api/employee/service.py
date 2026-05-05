import frappe
from frappe.utils import today
from frappe.utils.file_manager import save_file
import os

from .utils import (
    assign_salary_structure,
    assign_leave_policy,
    ALLOWED_EMPLOYEE_FIELDS,
    ALLOWED_EXTENDED_FIELDS,
    RETURN_EMPLOYEE_FIELDS_GET_ALL,
    RETURN_EMPLOYEE_FIELDS_GET_BY_ID,
    build_advanced_filters,
)


def create_employee(data):
    employee = frappe.new_doc("Employee")

    for field in ALLOWED_EMPLOYEE_FIELDS:
        if field in data and data.get(field) is not None:
            employee.set(field, data.get(field))

    if not employee.company:
        employee.company = frappe.defaults.get_user_default("Company")
    if not employee.date_of_joining:
        employee.date_of_joining = today()

    ext_details_data = {}
    for ext_field in ALLOWED_EXTENDED_FIELDS:
        if ext_field in data and data.get(ext_field) is not None:
            ext_details_data[ext_field] = data.get(ext_field)

    if ext_details_data:
        employee.append("custom_extended_details", ext_details_data)

    employee.insert(ignore_permissions=True)

    if data.get("salary_structure"):
        assign_salary_structure(
            employee.name,
            data.get("salary_structure"),
            employee.company,
            employee.date_of_joining,
            data.get("base_salary", 0),
        )
    if data.get("leave_policy"):
        assign_leave_policy(
            employee.name, data.get("leave_policy"), employee.date_of_joining
        )

    return get_employee_by_id(employee.name)


def update_employee(employee_id, data):
    employee = frappe.get_doc("Employee", employee_id)

    for field in ALLOWED_EMPLOYEE_FIELDS:
        if field in data and data.get(field) is not None:
            employee.set(field, data.get(field))

    if any(field in data for field in ALLOWED_EXTENDED_FIELDS):
        ext_details_data = {}
        for ext_field in ALLOWED_EXTENDED_FIELDS:
            if ext_field in data and data.get(ext_field) is not None:
                ext_details_data[ext_field] = data.get(ext_field)

        employee.set("custom_extended_details", [])
        if ext_details_data:
            employee.append("custom_extended_details", ext_details_data)

    employee.save(ignore_permissions=True)

    if data.get("salary_structure"):
        assign_salary_structure(
            employee.name,
            data.get("salary_structure"),
            employee.company,
            data.get("effective_date") or today(),
            data.get("base_salary", 0),
        )
    if data.get("leave_policy"):
        assign_leave_policy(
            employee.name,
            data.get("leave_policy"),
            data.get("effective_date") or today(),
        )

    return get_employee_by_id(employee.name)


def get_employee_by_id(employee_id):
    employee_data = frappe.db.get_value(
        "Employee", employee_id, RETURN_EMPLOYEE_FIELDS_GET_BY_ID, as_dict=True
    )

    employee_data["salary_structure"] = frappe.db.get_value(
        "Salary Structure Assignment",
        {"employee": employee_id, "docstatus": 1},
        "salary_structure",
        order_by="from_date desc",
    )
    employee_data["leave_policy"] = frappe.db.get_value(
        "Leave Policy Assignment",
        {"employee": employee_id, "docstatus": 1},
        "leave_policy",
        order_by="effective_from desc",
    )

    extended_details = frappe.get_all(
        "Custom Employee Extended Details",
        filters={"parent": employee_id, "parenttype": "Employee"},
        fields=ALLOWED_EXTENDED_FIELDS,
    )

    if extended_details:
        for key, value in extended_details[0].items():
            employee_data[key] = value
    else:
        for field in ALLOWED_EXTENDED_FIELDS:
            employee_data[field] = None

    return employee_data


def get_employees(
    filters, page, page_size, search, sort_by="creation", sort_order="desc"
):
    start = (page - 1) * page_size

    or_filters = []
    if search:
        search = str(search).strip()
        or_filters = [
            ["name", "like", f"%{search}%"],
            ["employee_name", "like", f"%{search}%"],
            ["department", "like", f"%{search}%"],
            ["designation", "like", f"%{search}%"],
            ["personal_email", "like", f"%{search}%"],
        ]

    safe_filters = build_advanced_filters(filters)

    if sort_by not in ALLOWED_EMPLOYEE_FIELDS and sort_by not in [
        "name",
        "creation",
        "modified",
    ]:
        sort_by = "creation"
    if sort_order.lower() not in ["asc", "desc"]:
        sort_order = "desc"

    order_by_string = f"{sort_by} {sort_order}"

    employees = frappe.get_all(
        "Employee",
        filters=safe_filters,
        or_filters=or_filters if search else None,
        fields=RETURN_EMPLOYEE_FIELDS_GET_ALL,
        limit_start=start,
        limit_page_length=page_size,
        order_by=order_by_string,
    )

    total_employees = len(
        frappe.get_all(
            "Employee",
            filters=safe_filters,
            or_filters=or_filters if search else None,
            pluck="name",
        )
    )

    total_pages = (total_employees + page_size - 1) // page_size

    return employees, total_employees, total_pages


def delete_employee(employee_id):
    frappe.db.delete("Salary Structure Assignment", {"employee": employee_id})
    frappe.db.delete("Leave Policy Assignment", {"employee": employee_id})
    frappe.delete_doc("Employee", employee_id, ignore_permissions=True)


def update_employee_status(employee_id, status):
    employee = frappe.get_doc("Employee", employee_id)
    employee.status = status
    employee.save(ignore_permissions=True)

    return {
        "id": employee.name,
        "status": employee.status,
        "employee_name": employee.employee_name,
    }


def upload_employee_image(employee_id, filename, file_content):
    saved_file = save_file(
        fname=filename,
        content=file_content,
        dt="Employee",
        dn=employee_id,
        folder="Home/Attachments",
        is_private=0,
    )

    frappe.db.set_value(
        "Employee", employee_id, "image", saved_file.file_url, update_modified=True
    )

    return saved_file.file_url


def update_employee_image(employee_id, filename, file_content):

    remove_employee_image(employee_id)

    new_file_url = upload_employee_image(
        employee_id=employee_id, filename=filename, file_content=file_content
    )

    return new_file_url


def remove_employee_image(employee_id):
    employee = frappe.get_doc("Employee", employee_id)

    if employee.image:
        file_doc = frappe.db.get_value(
            "File",
            {
                "file_url": employee.image,
                "attached_to_doctype": "Employee",
                "attached_to_name": employee_id,
            },
            "name",
        )

        if file_doc:
            frappe.delete_doc("File", file_doc, ignore_permissions=True)

        employee.image = None
        employee.save(ignore_permissions=True)

    return True


def upload_employee_document(employee_id, filename, file_content, document_name):
    safe_doc_name = str(document_name).replace(" ", "_").replace("/", "-")

    extension = os.path.splitext(filename)[1]
    final_filename = f"{safe_doc_name}{extension}"

    saved_file = save_file(
        fname=final_filename,
        content=file_content,
        dt="Employee",
        dn=employee_id,
        folder="Home/Attachments",
        is_private=1,
    )

    return saved_file


def get_employee_documents(employee_id):
    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Employee", "attached_to_name": employee_id},
        fields=[
            "name as file_id",
            "file_name as document_name",
            "file_url",
            "is_private",
            "creation",
        ],
        order_by="creation desc",
    )
    return files


def get_employee_document_by_id(file_id):
    file_doc = frappe.get_doc("File", file_id)
    return {
        "file_id": file_doc.name,
        "document_name": file_doc.file_name,
        "file_url": file_doc.file_url,
        "is_private": file_doc.is_private,
        "attached_to": file_doc.attached_to_name,
        "creation": file_doc.creation,
    }


def update_employee_document(
    file_id, new_document_name=None, new_file_content=None, new_filename=None
):
    file_doc = frappe.get_doc("File", file_id)

    if new_document_name:
        safe_doc_name = str(new_document_name).replace(" ", "_").replace("/", "-")

        if new_filename:
            extension = os.path.splitext(new_filename)[1]
        else:
            extension = os.path.splitext(file_doc.file_name)[1]

        file_doc.file_name = f"{safe_doc_name}{extension}"

    if new_file_content:
        file_doc.content = new_file_content

    file_doc.save(ignore_permissions=True)
    return file_doc


def delete_employee_document(file_id):
    frappe.delete_doc("File", file_id, ignore_permissions=True)
