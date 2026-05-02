import frappe
from frappe.utils import today
from frappe.utils.file_manager import save_file


from .utils import (
    assign_salary_structure, 
    assign_leave_policy, 
    ALLOWED_EMPLOYEE_FIELDS,
    RETURN_EMPLOYEE_FIELDS_GET_ALL,
    RETURN_EMPLOYEE_FIELDS_GET_BY_ID,
    build_advanced_filters
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
        
    employee.insert(ignore_permissions=True)
    
    if data.get("salary_structure"):
        assign_salary_structure(
            employee=employee.name,
            salary_structure=data.get("salary_structure"),
            company=employee.company,
            from_date=employee.date_of_joining,
            base_salary=data.get("base_salary", 0)
        )

    if data.get("leave_policy"):
        assign_leave_policy(
            employee=employee.name,
            leave_policy=data.get("leave_policy"),
            from_date=employee.date_of_joining
        )
        
    return get_employee_by_id(employee.name)


def update_employee(employee_id, data):
    employee = frappe.get_doc("Employee", employee_id)
    
    for field in ALLOWED_EMPLOYEE_FIELDS:
        if field in data and data.get(field) is not None:
            employee.set(field, data.get(field))
            
    employee.save(ignore_permissions=True)

    if data.get("salary_structure"):
        assign_salary_structure(
            employee=employee.name,
            salary_structure=data.get("salary_structure"),
            company=employee.company,
            from_date=data.get("effective_date") or today(),
            base_salary=data.get("base_salary", 0)
        )

    if data.get("leave_policy"):
        assign_leave_policy(
            employee=employee.name,
            leave_policy=data.get("leave_policy"),
            from_date=data.get("effective_date") or today()
        )

    return get_employee_by_id(employee.name)


def get_employee_by_id(employee_id):
    employee_data = frappe.db.get_value(
        "Employee", 
        employee_id, 
        RETURN_EMPLOYEE_FIELDS_GET_BY_ID, 
        as_dict=True
    )
    
    active_salary_structure = frappe.db.get_value(
        "Salary Structure Assignment", 
        {"employee": employee_id, "docstatus": 1}, 
        "salary_structure",
        order_by="from_date desc"
    )
    
    active_leave_policy = frappe.db.get_value(
        "Leave Policy Assignment",
        {"employee": employee_id, "docstatus": 1},
        "leave_policy",
        order_by="effective_from desc"
    )

    employee_data["salary_structure"] = active_salary_structure
    employee_data["leave_policy"] = active_leave_policy

    return employee_data


def get_employees(filters, page, page_size, search, sort_by="creation", sort_order="desc"):
    start = (page - 1) * page_size

    or_filters = []
    if search:
        search = str(search).strip()
        or_filters = [
            ["name", "like", f"%{search}%"],
            ["employee_name", "like", f"%{search}%"],
            ["department", "like", f"%{search}%"],
            ["designation", "like", f"%{search}%"],
            ["personal_email", "like", f"%{search}%"]
        ]

    safe_filters = build_advanced_filters(filters)

    if sort_by not in ALLOWED_EMPLOYEE_FIELDS and sort_by not in ["name", "creation", "modified"]:
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

    total_employees = len(frappe.get_all(
        "Employee",
        filters=safe_filters,
        or_filters=or_filters if search else None,
        pluck="name"
    ))

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
        "employee_name": employee.employee_name
    }

def upload_employee_image(employee_id, filename, file_content):
    saved_file = save_file(
        fname=filename,
        content=file_content,
        dt="Employee",
        dn=employee_id,
        folder="Home/Attachments",
        is_private=0
    )
    
    frappe.db.set_value(
        "Employee", 
        employee_id, 
        "image", 
        saved_file.file_url,
        update_modified=True
    )
    
    return saved_file.file_url