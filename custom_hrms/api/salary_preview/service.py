import frappe
from frappe import _
from frappe.utils import add_years, getdate, get_first_day, get_last_day, today





# Validation
def validate_inputs(employee: str, effective_date: str):
    if not employee:
        return _("employee' is required."), None

    if not effective_date:
        return _("effective_date is required."), None

    try:
        parsed = getdate(effective_date)
    except Exception:
        return _("'effective_date' must be a valid ISO date (YYYY-MM-DD). Got: {0}").format(
            effective_date
        ), None

    lower = add_years(getdate(today()), -10)
    upper = add_years(getdate(today()), 1)
    if not (lower <= parsed <= upper):
        return _(
            "effective_date {0} is out of the allowed range ({1} to {2})."
        ).format(effective_date, lower, upper), None

    if not frappe.db.exists("Employee", employee):
        return _("Employee '{0}' does not exist.").format(employee), None

    return None, getdate(effective_date)




def get_salary_structure_assignment(employee: str, on_date):
    SSA = frappe.qb.DocType("Salary Structure Assignment")

    rows = (
        frappe.qb.from_(SSA)
        .select(
            SSA.name,
            SSA.salary_structure,
            SSA.from_date,
            SSA.base,
            SSA.variable,
            SSA.currency,
            SSA.income_tax_slab,
            SSA.payroll_payable_account,
        )
        .where(SSA.employee  == employee)
        .where(SSA.docstatus == 1)
        .where(SSA.from_date <= on_date)
        .orderby(SSA.from_date, order=frappe.qb.desc)
        .limit(1)
    ).run(as_dict=True)

    return rows[0] if rows else None




def build_preview_salary_slip(salary_structure: str, employee: str, posting_date):
    """
    Builds a fresh transient Salary Slip on every call.

    Calls only the two methods needed for a breakdown:
        get_emp_and_working_day_details()  — loads components
        calculate_net_pay()                — computes all amounts

    Skips validate(), check_existing(), compute_year_to_date(),
    compute_month_to_date() — not needed and cause fiscal year errors.

    Nothing is inserted / saved / submitted.
    """
    frappe.local.document_cache = {}

    start_date = get_first_day(posting_date)
    end_date   = get_last_day(posting_date)

    ss = frappe.new_doc("Salary Slip")
    ss.employee          = employee
    ss.salary_structure  = salary_structure
    ss.posting_date      = str(posting_date)
    ss.start_date        = str(start_date)
    ss.end_date          = str(end_date)
    ss.payroll_frequency = frappe.db.get_value(
        "Salary Structure", salary_structure, "payroll_frequency"
    )
    ss.company = frappe.db.get_value(
        "Salary Structure", salary_structure, "company"
    )

    ss.get_emp_and_working_day_details()
    ss.calculate_net_pay()

    return ss



def serialize(salary_slip, assignment, effective_date) -> dict:
    def fmt_components(rows):
        return [
            {
                "component":                row.salary_component,
                "abbr":                     row.abbr,
                "amount":                   _flt(row.amount),
                "default_amount":           _flt(row.default_amount),
                "additional_amount":        _flt(row.additional_amount),
                "depends_on_payment_days":  bool(row.depends_on_payment_days),
                "is_tax_applicable":        bool(row.is_tax_applicable),
                "do_not_include_in_total":  bool(row.do_not_include_in_total),
                "exempted_from_income_tax": bool(row.get("exempted_from_income_tax")),
            }
            for row in (rows or [])
        ]

    return {
        "employee":           salary_slip.employee,
        "employee_name":      salary_slip.employee_name or frappe.db.get_value(
                                  "Employee", salary_slip.employee, "employee_name"
                              ),
        "salary_structure":   salary_slip.salary_structure,
        "assignment":         assignment["name"],
        "effective_date":     str(effective_date),
        "slip_start_date":    str(salary_slip.start_date),
        "slip_end_date":      str(salary_slip.end_date),
        "base":               _flt(assignment.get("base")),
        "variable":           _flt(assignment.get("variable")),
        "currency":           salary_slip.currency or assignment.get("currency"),
        "payment_days":       float(salary_slip.payment_days or 0),
        "total_working_days": float(salary_slip.total_working_days or 0),
        "gross_pay":          _flt(salary_slip.gross_pay),
        "total_deduction":    _flt(salary_slip.total_deduction),
        "net_pay":            _flt(salary_slip.net_pay),
        "rounded_total":      _flt(salary_slip.rounded_total),
        "earnings":           fmt_components(salary_slip.earnings),
        "deductions":         fmt_components(salary_slip.deductions),
    }



def _flt(value) -> float:
    return round(float(value or 0), 2)