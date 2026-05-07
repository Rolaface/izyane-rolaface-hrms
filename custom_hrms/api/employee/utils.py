import frappe
import json
from frappe.utils import flt
from frappe.utils import flt, getdate, add_days, add_months

ALLOWED_EMPLOYEE_FIELDS = {
    "valid_upto",
    "user_id",
    "unsubscribed",
    "status",
    "shift_request_approver",
    "scheduled_confirmation_date",
    "salutation",
    "salary_mode",
    "salary_currency",
    "resignation_letter_date",
    "reports_to",
    "relieving_date",
    "relation",
    "reason_for_leaving",
    "prefered_email",
    "prefered_contact_email",
    "place_of_issue",
    "personal_email",
    "person_to_be_contacted",
    "permanent_address",
    "permanent_accommodation_type",
    "payroll_cost_center",
    "passport_number",
    "notice_number_of_days",
    "new_workplace",
    "naming_series",
    "middle_name",
    "marital_status",
    "leave_encashed",
    "leave_approver",
    "last_name",
    "job_applicant",
    "image",
    "iban",
    "holiday_list",
    "held_on",
    "health_insurance_provider",
    "health_insurance_no",
    "health_details",
    "grade",
    "gender",
    "first_name",
    "final_confirmation_date",
    "feedback",
    "family_background",
    "expense_approver",
    "encashment_date",
    "employment_type",
    "employee_number",
    "employee_name",
    "employee_advance_account",
    "employee",
    "emergency_phone_number",
    "designation",
    "department",
    "default_shift",
    "date_of_retirement",
    "date_of_joining",
    "date_of_issue",
    "date_of_birth",
    "current_address",
    "current_accommodation_type",
    "ctc",
    "create_user_permission",
    "create_user_automatically",
    "contract_end_date",
    "company_email",
    "company",
    "cell_number",
    "branch",
    "blood_group",
    "bio",
    "bank_name",
    "bank_ac_no",
    "attendance_device_id",
    "holiday_list",
}

RETURN_EMPLOYEE_FIELDS_GET_ALL = [
    "name",
    "employee_name",
    "employee_number",
    "gender",
    "date_of_joining",
    "designation",
    "department",
    "grade",
    "branch",
    "status",
    "personal_email",
    "company_email",
    "cell_number",
    "ctc",
    "reports_to",
    "image",
]

RETURN_EMPLOYEE_FIELDS_GET_BY_ID = [
    "valid_upto",
    "user_id",
    "unsubscribed",
    "status",
    "shift_request_approver",
    "scheduled_confirmation_date",
    "salutation",
    "salary_mode",
    "salary_currency",
    "resignation_letter_date",
    "reports_to",
    "relieving_date",
    "relation",
    "reason_for_leaving",
    "prefered_email",
    "prefered_contact_email",
    "place_of_issue",
    "personal_email",
    "person_to_be_contacted",
    "permanent_address",
    "permanent_accommodation_type",
    "payroll_cost_center",
    "passport_number",
    "notice_number_of_days",
    "new_workplace",
    "naming_series",
    "middle_name",
    "marital_status",
    "leave_encashed",
    "leave_approver",
    "last_name",
    "job_applicant",
    "image",
    "iban",
    "holiday_list",
    "held_on",
    "health_insurance_provider",
    "health_insurance_no",
    "health_details",
    "grade",
    "gender",
    "first_name",
    "final_confirmation_date",
    "feedback",
    "family_background",
    "expense_approver",
    "encashment_date",
    "employment_type",
    "employee_number",
    "employee_name",
    "employee_advance_account",
    "employee",
    "emergency_phone_number",
    "designation",
    "department",
    "default_shift",
    "date_of_retirement",
    "date_of_joining",
    "date_of_issue",
    "date_of_birth",
    "current_address",
    "current_accommodation_type",
    "ctc",
    "create_user_permission",
    "create_user_automatically",
    "contract_end_date",
    "company_email",
    "company",
    "cell_number",
    "branch",
    "blood_group",
    "bio",
    "bank_name",
    "bank_ac_no",
    "attendance_device_id",
    "holiday_list",
]

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}

ALLOWED_EXTENDED_FIELDS = [
    "national_identification_number",
    "tax_identification_number",
    "universal_account_number",
    "health_insurance_number",
]


def build_advanced_filters(raw_filters):
    safe_filters = {}
    if not raw_filters:
        return safe_filters

    if isinstance(raw_filters, str):
        try:
            raw_filters = json.loads(raw_filters)
        except json.JSONDecodeError:
            frappe.throw("Invalid JSON format for filters.")

    for field, condition in raw_filters.items():
        if field in ALLOWED_EMPLOYEE_FIELDS or field == "name":
            safe_filters[field] = condition

    return safe_filters


def assign_salary_structure(
    employee,
    salary_structure,
    company,
    from_date,
    base_salary,
    income_tax_slab=None,
):
    if not frappe.db.exists("Salary Structure", salary_structure):
        frappe.throw(f"Salary Structure '{salary_structure}' not found.")

    existing = frappe.db.get_value(
        "Salary Structure Assignment",
        {"employee": employee, "docstatus": 1},
        "name",
    )

    if existing:
        frappe.throw(
            f"An active Salary Structure Assignment ({existing}) already exists for {employee}."
        )

    assignment = frappe.new_doc("Salary Structure Assignment")
    assignment.employee = employee
    assignment.salary_structure = salary_structure
    assignment.company = company
    assignment.from_date = from_date
    assignment.base = flt(base_salary)

    selected_tax_slab = income_tax_slab

    if not selected_tax_slab:
        selected_tax_slab = frappe.db.get_value(
            "Income Tax Slab",
            {
                "company": company,
                "disabled": 0,
            },
            "name",
            order_by="creation asc",
        )

    if selected_tax_slab:
        assignment.income_tax_slab = selected_tax_slab

    assignment.insert(ignore_permissions=True)
    assignment.submit()

    return assignment


def assign_leave_policy(employee, leave_policy, from_date):
    if not frappe.db.exists("Leave Policy", leave_policy):
        frappe.throw(f"Leave Policy '{leave_policy}' not found.")

    existing = frappe.db.exists(
        "Leave Policy Assignment",
        {"employee": employee, "docstatus": 1},
    )

    if existing:
        frappe.throw(
            f"An active Leave Policy Assignment already exists for {employee}."
        )

    assignment = frappe.new_doc("Leave Policy Assignment")
    assignment.employee = employee
    assignment.leave_policy = leave_policy
    assignment.assignment_based_on = "Leave Period"

    leave_period_data = frappe.db.get_value(
        "Leave Period",
        {"from_date": ["<=", from_date], "to_date": [">=", from_date], "is_active": 1},
        ["name", "from_date", "to_date"],
        as_dict=True,
    )

    if leave_period_data:
        assignment.leave_period = leave_period_data.name
        assignment.effective_from = leave_period_data.from_date
        assignment.effective_to = leave_period_data.to_date
    else:
        assignment.assignment_based_on = None
        assignment.effective_from = from_date
        assignment.effective_to = add_days(add_months(from_date, 12), -1)

    assignment.insert(ignore_permissions=True)
    assignment.submit()


def assign_holiday_list(employee, holiday_list, from_date):
    if not frappe.db.exists("Holiday List", holiday_list):
        frappe.throw(f"Holiday List '{holiday_list}' not found.")

    hl_start_date, hl_end_date = frappe.db.get_value(
        "Holiday List", holiday_list, ["from_date", "to_date"]
    )

    assignment_date = getdate(from_date)

    if hl_start_date and assignment_date < getdate(hl_start_date):
        assignment_date = getdate(hl_start_date)

    if hl_end_date and assignment_date > getdate(hl_end_date):
        return

    existing_assignment = frappe.db.exists(
        "Holiday List Assignment", {"employee": employee, "docstatus": 1}
    )

    if existing_assignment:
        frappe.throw(
            f"An active Holiday List Assignment already exists for {employee}."
        )

    assignment = frappe.new_doc("Holiday List Assignment")

    assignment.employee = employee
    assignment.assigned_to = employee
    assignment.holiday_list = holiday_list
    assignment.from_date = assignment_date

    assignment.insert(ignore_permissions=True)
    assignment.submit()
