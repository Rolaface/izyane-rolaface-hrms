import frappe
import json
from frappe.utils import flt
from frappe.utils import flt, getdate, add_days, add_months ,today

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

ALLOWED_SORT_FIELDS = {
    "name",
    "creation",
    "modified",
    "employee_name",
    "employee_number",
    "department",
    "designation",
    "company",
    "branch",
    "status",
    "employment_type",
    "date_of_joining",
    "date_of_birth",
    "date_of_retirement",
    "relieving_date",
    "scheduled_confirmation_date",
    "final_confirmation_date",
    "grade",
    "reports_to",
    "gender",
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


# def assign_salary_structure(employee, salary_structure, company, from_date, base_salary, income_tax_slab=None):
#     if not frappe.db.exists("Salary Structure", salary_structure):
#         frappe.throw(f"Salary Structure '{salary_structure}' not found.")

#     target_date = getdate(from_date)

#     existing_assignment_name = frappe.db.get_value(
#         "Salary Structure Assignment",
#         {"employee": employee, "docstatus": 1},
#         "name",
#         order_by="from_date desc, creation desc",
#     )

#     if existing_assignment_name:
#         old_assignment = frappe.get_doc("Salary Structure Assignment", existing_assignment_name)
#         old_date = getdate(old_assignment.from_date)
#         old_structure_name = old_assignment.salary_structure

#         if old_date == target_date:
#             old_assignment.cancel()
#             frappe.delete_doc("Salary Structure Assignment", old_assignment.name, ignore_permissions=True)

#             if str(old_structure_name).startswith(f"SS-{employee}-"):
#                 try:
#                     old_structure = frappe.get_doc("Salary Structure", old_structure_name)
#                     if old_structure.docstatus == 1:
#                         old_structure.cancel()
#                     frappe.delete_doc("Salary Structure", old_structure_name, ignore_permissions=True)
#                 except Exception:
#                     frappe.db.set_value("Salary Structure", old_structure_name, "is_active", "No")
#         else:
#             old_assignment.cancel()

#     assignment = frappe.new_doc("Salary Structure Assignment")
#     assignment.employee = employee
#     assignment.salary_structure = salary_structure
#     assignment.company = company
#     assignment.from_date = target_date
#     assignment.base = flt(base_salary)

#     selected_tax_slab = income_tax_slab
#     if not selected_tax_slab:
#         selected_tax_slab = frappe.db.get_value(
#             "Income Tax Slab",
#             {"company": company, "disabled": 0},
#             "name",
#             order_by="creation asc",
#         )

#     if selected_tax_slab:
#         assignment.income_tax_slab = selected_tax_slab

#     assignment.insert(ignore_permissions=True)
#     assignment.submit()

#     return assignment

def assign_salary_structure(
    employee: str,
    salary_structure: str,
    company: str,
    from_date: str,
    base_salary: float,
    income_tax_slab: str = None,
):

    if not frappe.db.exists("Salary Structure", salary_structure):
        frappe.throw(_("Salary Structure '{0}' not found.").format(salary_structure))

    target_date = getdate(from_date)

    existing_assignment_name = frappe.db.get_value(
        "Salary Structure Assignment",
        {"employee": employee, "docstatus": 1},
        "name",
        order_by="from_date desc, creation desc",
    )

    if existing_assignment_name:
        old_assignment = frappe.get_doc("Salary Structure Assignment", existing_assignment_name)
        old_date = getdate(old_assignment.from_date)
        old_structure_name = old_assignment.salary_structure

        # --- CASE A: SAME-DATE REPLACEMENT (CORRECTION) ---
        if old_date == target_date:
            # Cancel and remove the duplicate same-day assignment
            old_assignment.cancel()
            frappe.delete_doc("Salary Structure Assignment", old_assignment.name, ignore_permissions=True)

            # Only delete if it is an auto-generated employee-specific structure
            if str(old_structure_name).startswith(f"SS-{employee}-") and old_structure_name != salary_structure:
                _cleanup_custom_salary_structure(old_structure_name)

        # --- CASE B: FUTURE/PAST DATE VERSIONING (PROMOTION/RAISE) ---
        else:
            # Standard Frappe versioning: simply cancel the old assignment
            old_assignment.cancel()

    # 3. Resolve Income Tax Slab
    selected_tax_slab = income_tax_slab or _get_default_tax_slab(company)

    # 4. Create & Submit New Assignment
    new_assignment = frappe.new_doc("Salary Structure Assignment")
    new_assignment.employee = employee
    new_assignment.salary_structure = salary_structure
    new_assignment.company = company
    new_assignment.from_date = target_date
    new_assignment.base = flt(base_salary)

    if selected_tax_slab:
        new_assignment.income_tax_slab = selected_tax_slab

    new_assignment.insert(ignore_permissions=True)
    new_assignment.submit()

    return new_assignment


def _cleanup_custom_salary_structure(structure_name: str):
    try:
        old_structure = frappe.get_doc("Salary Structure", structure_name)
        
        
        if old_structure.docstatus == 1:
            old_structure.cancel()
            
        frappe.delete_doc("Salary Structure", structure_name, ignore_permissions=True)
    except Exception:
        frappe.db.set_value("Salary Structure", structure_name, "is_active", "No")


def _get_default_tax_slab(company: str) -> str:
    """Helper to fetch the active default Income Tax Slab for a company."""
    return frappe.db.get_value(
        "Income Tax Slab",
        {"company": company, "disabled": 0},
        "name",
        order_by="creation asc",
    )


def assign_leave_policy(employee, leave_policy, from_date=None):
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

    company = frappe.db.get_value("Employee", employee, "company")
    current_date = today()

    leave_period_data = frappe.db.get_value(
        "Leave Period",
        {
            "is_active": 1,
            "company": company,
            "from_date": ["<=", current_date],
            "to_date": [">=", current_date],
        },
        ["name", "from_date", "to_date"],
        as_dict=True,
    )

    if not leave_period_data:
        frappe.throw(
            f"No active Leave Period found for {company} covering the current date. Please create or activate a Leave Period."
        )

    assignment = frappe.new_doc("Leave Policy Assignment")
    assignment.employee = employee
    assignment.leave_policy = leave_policy
    assignment.assignment_based_on = "Leave Period"
    assignment.leave_period = leave_period_data.name
    assignment.effective_from = leave_period_data.from_date
    assignment.effective_to = leave_period_data.to_date

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
