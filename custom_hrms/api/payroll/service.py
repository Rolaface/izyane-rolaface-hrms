import frappe


def run_payroll(payroll_entry_id):
    payroll_entry = frappe.get_doc("Payroll Entry", payroll_entry_id)

    if payroll_entry.docstatus == 2:
        frappe.throw("Cannot process cancelled Payroll Entry.")

    submitted_slips_count = frappe.db.count(
        "Salary Slip",
        {
            "payroll_entry": payroll_entry.name,
            "docstatus": 1,
        },
    )

    if submitted_slips_count > 0:
        frappe.throw("Salary slips already submitted for this Payroll Entry.")

    if payroll_entry.docstatus == 0:
        payroll_entry.submit()
        payroll_entry.reload()

    salary_slips = frappe.get_all(
        "Salary Slip",
        filters={
            "payroll_entry": payroll_entry.name,
        },
        pluck="name",
    )

    if not salary_slips:
        frappe.throw("No salary slips found for this Payroll Entry.")

    payroll_entry.submit_salary_slips()

    payroll_entry.reload()

    submitted_slips = frappe.get_all(
        "Salary Slip",
        filters={
            "payroll_entry": payroll_entry.name,
            "docstatus": 1,
        },
        fields=[
            "name",
            "employee",
            "employee_name",
            "net_pay",
            "start_date",
            "end_date",
        ],
        order_by="employee asc",
    )

    return {
        "payroll_entry": payroll_entry.name,
        "total_submitted_slips": len(submitted_slips),
        "submitted_salary_slips": submitted_slips,
    }
