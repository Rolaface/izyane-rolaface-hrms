import frappe
from frappe.utils import flt, today
from frappe.utils.file_manager import save_file
import os

from .utils import (
    assign_salary_structure,
    assign_leave_policy,
    assign_holiday_list,
    ALLOWED_EMPLOYEE_FIELDS,
    ALLOWED_EXTENDED_FIELDS,
    RETURN_EMPLOYEE_FIELDS_GET_ALL,
    RETURN_EMPLOYEE_FIELDS_GET_BY_ID,
    build_advanced_filters,
)


def create_employee(data):
    default_company = frappe.defaults.get_user_default("Company")
    current_date = today()

    try:
        employee = frappe.new_doc("Employee")

        for field in ALLOWED_EMPLOYEE_FIELDS:
            if field in data and data.get(field) is not None:
                employee.set(field, data.get(field))

        if not employee.get("company"):
            employee.company = default_company

        if not employee.get("date_of_joining"):
            employee.date_of_joining = current_date

        current_company = employee.get("company")

        if not employee.get("holiday_list") and current_company:
            default_holiday = frappe.db.get_value(
                "Company", current_company, "default_holiday_list"
            )
            if default_holiday:
                employee.holiday_list = default_holiday

        ext_details_data = {}
        for ext_field in ALLOWED_EXTENDED_FIELDS:
            if ext_field in data and data.get(ext_field) is not None:
                ext_details_data[ext_field] = data.get(ext_field)

        if ext_details_data:
            child_row = employee.append("custom_extended_details", {})
            child_row.update(ext_details_data)

        employee.insert(ignore_permissions=True)

        if data.get("salary_structure"):
            assign_salary_structure(
                employee=employee.name,
                salary_structure=data.get("salary_structure"),
                company=current_company,
                from_date=employee.get("date_of_joining"),
                base_salary=data.get("base_salary", 0),
                income_tax_slab=data.get("income_tax_slab"),
            )

        if data.get("leave_policy"):
            assign_leave_policy(employee.name, data.get("leave_policy"))

        if employee.get("holiday_list"):
            assign_holiday_list(
                employee.name,
                employee.get("holiday_list"),
                employee.get("date_of_joining"),
            )

        return get_employee_by_id(employee.name)

    except Exception as e:
        frappe.db.rollback()
        raise e


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

    if any(k in data for k in ["salary_structure", "base_salary", "income_tax_slab"]):
        current_assignment = frappe.db.get_value(
            "Salary Structure Assignment",
            {"employee": employee_id, "docstatus": 1},
            ["salary_structure", "base", "income_tax_slab"],
            as_dict=True,
            order_by="from_date desc, creation desc",
        )

        if current_assignment:
            new_structure = data.get("salary_structure", current_assignment.get("salary_structure"))
            new_base = data.get("base_salary", current_assignment.get("base"))
            new_slab = data.get("income_tax_slab", current_assignment.get("income_tax_slab"))

            if (new_structure != current_assignment.get("salary_structure") or 
                flt(new_base) != flt(current_assignment.get("base")) or 
                new_slab != current_assignment.get("income_tax_slab")):
                
                assign_salary_structure(
                    employee=employee.name,
                    salary_structure=new_structure,
                    company=employee.company,
                    from_date=data.get("effective_date") or today(),
                    base_salary=new_base,
                    income_tax_slab=new_slab,
                )
        else:
            if data.get("salary_structure"):
                assign_salary_structure(
                    employee=employee.name,
                    salary_structure=data.get("salary_structure"),
                    company=employee.company,
                    from_date=data.get("effective_date") or today(),
                    base_salary=data.get("base_salary", 0),
                    income_tax_slab=data.get("income_tax_slab"),
                )

    if data.get("leave_policy"):
        current_leave = frappe.db.get_value(
            "Leave Policy Assignment",
            {"employee": employee_id, "docstatus": 1},
            "leave_policy",
            order_by="effective_from desc, creation desc"
        )
        if current_leave != data.get("leave_policy"):
            assign_leave_policy(employee.name, data.get("leave_policy"))

    if data.get("holiday_list"):
        current_holiday = frappe.db.get_value(
            "Holiday List Assignment",
            {"employee": employee_id, "docstatus": 1},
            "holiday_list",
        )
        if current_holiday != data.get("holiday_list"):
            assign_holiday_list(
                employee.name,
                data.get("holiday_list"),
                data.get("effective_date") or today(),
            )

    return get_employee_by_id(employee.name)


def get_employee_by_id(employee_id):
    employee_data = frappe.db.get_value(
        "Employee", employee_id, RETURN_EMPLOYEE_FIELDS_GET_BY_ID, as_dict=True
    )

    salary_assignment = frappe.db.get_value(
        "Salary Structure Assignment",
        {"employee": employee_id, "docstatus": 1},
        ["salary_structure", "income_tax_slab", "base"],
        as_dict=True,
        order_by="from_date desc, creation desc", # Ensure we get the latest assignment if multiple exist should be from date but because of the way we are assigning it can be multiple with same from date so using creation date to get the latest one
    )

    if salary_assignment:
        employee_data["salary_structure"] = salary_assignment.get("salary_structure")
        employee_data["income_tax_slab"] = salary_assignment.get("income_tax_slab")
        employee_data["base_salary"] = salary_assignment.get("base")
    else:
        employee_data["salary_structure"] = None
        employee_data["income_tax_slab"] = None
        employee_data["base_salary"] = 0

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

    if employee_data.get("leave_approver"):
        employee_data["leave_approver_name"] = frappe.db.get_value(
            "User",
            employee_data.get("leave_approver"),
            "full_name"
        )
    else:
        employee_data["leave_approver_name"] = None

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

    employee_names = [emp["name"] for emp in employees]

    if employee_names:
        fields_to_fetch = ["parent"] + ALLOWED_EXTENDED_FIELDS
        all_extended_details = frappe.get_all(
            "Custom Employee Extended Details",
            filters={"parent": ["in", employee_names], "parenttype": "Employee"},
            fields=fields_to_fetch,
        )

        details_map = {row["parent"]: row for row in all_extended_details}

        for emp in employees:
            emp_details = details_map.get(emp["name"], {})
            emp_details.pop("parent", None)

            if emp_details:
                for key, value in emp_details.items():
                    emp[key] = value
            else:
                for field in ALLOWED_EXTENDED_FIELDS:
                    emp[field] = None

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
