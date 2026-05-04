import frappe
import json
from frappe.utils import flt

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
]

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}


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
    employee, salary_structure, company, from_date, base_salary
):
    if not frappe.db.exists("Salary Structure", salary_structure):
        frappe.throw(f"Salary Structure '{salary_structure}' not found.")

    existing = frappe.db.exists(
        "Salary Structure Assignment",
        {"employee": employee, "from_date": from_date, "docstatus": 1},
    )

    if existing:
        return

    assignment = frappe.new_doc("Salary Structure Assignment")
    assignment.employee = employee
    assignment.salary_structure = salary_structure
    assignment.company = company
    assignment.from_date = from_date
    assignment.base = flt(base_salary)

    assignment.insert(ignore_permissions=True)
    assignment.submit()


def assign_leave_policy(employee, leave_policy, from_date):
    if not frappe.db.exists("Leave Policy", leave_policy):
        frappe.throw(f"Leave Policy '{leave_policy}' not found.")

    assignment = frappe.new_doc("Leave Policy Assignment")
    assignment.employee = employee
    assignment.leave_policy = leave_policy
    assignment.assignment_based_on = "Leave Period"

    leave_period = frappe.db.get_value(
        "Leave Period",
        {"from_date": ["<=", from_date], "to_date": [">=", from_date], "is_active": 1},
        "name",
    )

    if leave_period:
        assignment.leave_period = leave_period
    else:
        assignment.assignment_based_on = None
        assignment.effective_from = from_date
        assignment.effective_to = frappe.utils.add_days(
            frappe.utils.add_months(from_date, 12), -1
        )

    assignment.insert(ignore_permissions=True)
    assignment.submit()
