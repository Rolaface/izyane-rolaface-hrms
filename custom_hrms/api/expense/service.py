import math
import frappe

EXPENSE_CLAIM_TYPE_SORT_FIELDS = [
    "name",
    "expense_type",
    "creation",
    "modified",
]

EXPENSE_CLAIM_SORT_FIELDS = [
    "name",
    "employee",
    "employee_name",
    "expense_approver",
    "posting_date",
    "approval_status",
    "clearance_date",
    "total_claimed_amount",
    "creation",
    "modified",
]


def get_expense_claim_types(
    page=1,
    page_size=20,
    search=None,
    sort_by="modified",
    sort_order="desc",
):
    if sort_by not in EXPENSE_CLAIM_TYPE_SORT_FIELDS:
        sort_by = "modified"

    if sort_order.lower() not in ["asc", "desc"]:
        sort_order = "desc"

    filters = {}

    if search:
        filters["expense_type"] = ["like", f"%{search}%"]

    total = frappe.db.count(
        "Expense Claim Type",
        filters=filters,
    )

    total_pages = math.ceil(total / page_size) if total else 1

    start = (page - 1) * page_size

    expense_claim_types = frappe.get_all(
        "Expense Claim Type",
        filters=filters,
        fields=[
            "name",
            "expense_type",
            "creation",
            "modified",
            "owner",
        ],
        order_by=f"{sort_by} {sort_order}",
        limit_start=start,
        limit_page_length=page_size,
    )

    names = [d.name for d in expense_claim_types]

    accounts = []

    if names:
        accounts = frappe.get_all(
            "Expense Claim Account",
            filters={
                "parent": ["in", names],
            },
            fields=[
                "parent",
                "company",
                "default_account",
            ],
        )

    accounts_map = {}

    for acc in accounts:
        accounts_map.setdefault(acc.parent, []).append(
            {
                "company": acc.company,
                "default_account": acc.default_account,
            }
        )

    result = []

    for row in expense_claim_types:
        result.append(
            {
                "name": row.name,
                "expense_type": row.expense_type,
                "creation": row.creation,
                "modified": row.modified,
                "owner": row.owner,
                "accounts": accounts_map.get(row.name, []),
            }
        )

    return result, total, total_pages


def get_expense_claims(
    page=1,
    page_size=20,
    search=None,
    employee=None,
    company=None,
    approval_status=None,
    sort_by="modified",
    sort_order="desc",
):
    if sort_by not in EXPENSE_CLAIM_SORT_FIELDS:
        sort_by = "modified"

    if sort_order.lower() not in ["asc", "desc"]:
        sort_order = "desc"

    filters = {}

    if employee:
        filters["employee"] = employee

    if company:
        filters["company"] = company

    if approval_status:
        filters["approval_status"] = approval_status

    if search:
        filters["name"] = ["like", f"%{search}%"]

    total = frappe.db.count(
        "Expense Claim",
        filters=filters,
    )

    total_pages = math.ceil(total / page_size) if total else 1

    start = (page - 1) * page_size

    expense_claims = frappe.get_all(
        "Expense Claim",
        filters=filters,
        fields=[
            "name",
            "employee",
            "employee_name",
            "expense_approver",
            "company",
            "posting_date",
            "approval_status",
            "docstatus",
            "currency",
            "total_claimed_amount",
            "total_sanctioned_amount",
            "clearance_date",
            "remark",
            "creation",
            "modified",
            "owner",
        ],
        order_by=f"{sort_by} {sort_order}",
        limit_start=start,
        limit_page_length=page_size,
    )

    claim_names = [d.name for d in expense_claims]

    expenses = []

    if claim_names:
        expenses = frappe.get_all(
            "Expense Claim Detail",
            filters={
                "parent": ["in", claim_names],
            },
            fields=[
                "parent",
                "name",
                "expense_date",
                "expense_type",
                "default_account",
                "description",
                "amount",
                "sanctioned_amount",
            ],
        )

    expenses_map = {}

    for exp in expenses:
        expenses_map.setdefault(exp.parent, []).append(
            {
                "name": exp.name,
                "expense_date": exp.expense_date,
                "expense_type": exp.expense_type,
                "default_account": exp.default_account,
                "description": exp.description,
                "amount": exp.amount,
                "sanctioned_amount": exp.sanctioned_amount,
            }
        )

    result = []

    for row in expense_claims:
        result.append(
            {
                "name": row.name,
                "employee": row.employee,
                "employee_name": row.employee_name,
                "expense_approver": row.expense_approver,
                "company": row.company,
                "posting_date": row.posting_date,
                "approval_status": row.approval_status,
                "docstatus": row.docstatus,
                "currency": row.currency,
                "total_claimed_amount": row.total_claimed_amount,
                "total_sanctioned_amount": row.total_sanctioned_amount,
                "clearance_date": row.clearance_date,
                "remark": row.remark,
                "creation": row.creation,
                "modified": row.modified,
                "owner": row.owner,
                "expenses": expenses_map.get(row.name, []),
            }
        )

    return result, total, total_pages
