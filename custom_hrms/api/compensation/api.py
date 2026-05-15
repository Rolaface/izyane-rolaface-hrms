import frappe
from frappe.utils import flt
from frappe.utils.safe_exec import safe_eval


@frappe.whitelist()
def preview_compensation(
    salary_structure: str,
    tax_slab: str,
    base: float,
    standard_deduction: float = 70000,
):

    base = flt(base)
    standard_deduction = flt(
        standard_deduction
    )

    context = {
        "base": base,
        "BS": base,
    }

    structure = frappe.get_doc(
        "Salary Structure",
        salary_structure,
    )

    slab = frappe.get_doc(
        "Income Tax Slab",
        tax_slab,
    )

    earnings = []
    deductions = []

    gross_monthly = 0

    # -----------------------------------
    # EARNINGS
    # -----------------------------------

    for row in structure.earnings:

        amount = 0

        if row.amount:
            amount = flt(row.amount)

        elif row.formula:

            amount = evaluate_formula(
                row.formula,
                context,
            )

        if row.abbr:
            context[row.abbr] = amount

        earnings.append(
            {
                "salary_component": row.salary_component,
                "abbr": row.abbr,
                "amount": round(amount, 2),
            }
        )

        gross_monthly += amount

    # -----------------------------------
    # ANNUAL TAXABLE INCOME
    # -----------------------------------

    gross_annual = gross_monthly * 12

    taxable_income = (
        gross_annual
        - standard_deduction
    )

    if taxable_income < 0:
        taxable_income = 0

    # -----------------------------------
    # SLAB TAX
    # -----------------------------------

    annual_tax = calculate_tax(
        taxable_income,
        slab,
    )

    monthly_tax = annual_tax / 12

    deductions.append(
        {
            "salary_component": "Income Tax",
            "abbr": "TAX",
            "amount": round(monthly_tax, 2),
        }
    )

    net_monthly = (
        gross_monthly
        - monthly_tax
    )

    # -----------------------------------
    # RESPONSE
    # -----------------------------------

    return {
        "earnings": earnings,
        "deductions": deductions,
        "gross_monthly": round(
            gross_monthly,
            2,
        ),
        "gross_annual": round(
            gross_annual,
            2,
        ),
        "annual_taxable_income": round(
            taxable_income,
            2,
        ),
        "annual_tax": round(
            annual_tax,
            2,
        ),
        "monthly_tax": round(
            monthly_tax,
            2,
        ),
        "net_monthly": round(
            net_monthly,
            2,
        ),
        "net_annual": round(
            net_monthly * 12,
            2,
        ),
    }


def calculate_tax(
    taxable_income,
    slab_doc,
):

    total_tax = 0

    slabs = sorted(
        slab_doc.slabs,
        key=lambda x: x.from_amount,
    )

    for slab in slabs:

        from_amount = flt(
            slab.from_amount
        )

        to_amount = flt(
            slab.to_amount or 999999999
        )

        percent = flt(
            slab.percent_deduction
        )

        if taxable_income <= from_amount:
            continue

        taxable_in_slab = (
            min(
                taxable_income,
                to_amount,
            )
            - from_amount
        )

        if taxable_in_slab < 0:
            taxable_in_slab = 0

        slab_tax = (
            taxable_in_slab
            * percent
            / 100
        )

        total_tax += slab_tax

    # -----------------------------------
    # CESS (4%)
    # -----------------------------------

    cess = total_tax * 0.04

    total_tax += cess

    return round(total_tax, 2)


def evaluate_formula(
    formula,
    context,
):

    try:

        value = safe_eval(
            formula,
            None,
            context,
        )

        return flt(value)

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "Salary Formula Error",
        )

        return 0