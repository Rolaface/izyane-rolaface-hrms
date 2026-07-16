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
        accounts_map[acc.parent] = {
            "account_company": acc.company,
            "default_account": acc.default_account,
        }

    result = []

    for row in expense_claim_types:
        account_data = accounts_map.get(row.name, {})

        result.append(
            {
                "name": row.name,
                "expense_type": row.expense_type,
                "creation": row.creation,
                "account": account_data.get("default_account"),
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

    or_filters = []

    if approval_status:
        if approval_status not in ["Paid", "Unpaid"]:
            filters["approval_status"] = approval_status
        else:
            filters["status"] = approval_status

    if search:
        expense_type_claims = frappe.get_all(
            "Expense Claim Detail",
            filters={
                "expense_type": ["like", f"%{search}%"]
            },
            pluck="parent"
        )
        or_filters.extend([
            ["name", "like", f"%{search}%"],
            ["employee_name", "like", f"%{search}%"],
            ["expense_approver", "like", f"%{search}%"],
            ["employee", "like", f"%{search}%"],
            ["name", "in", expense_type_claims]
        ])

    total = frappe.db.count(
        "Expense Claim",
        filters=filters,
    )

    total_pages = math.ceil(total / page_size) if total else 1

    start = (page - 1) * page_size
    fields=[
            "name",
            "employee",
            "employee_name",
            "expense_approver",
            "company",
            "posting_date",
            "approval_status",
            "status",
            "currency",
            "total_claimed_amount",
            "total_sanctioned_amount",
            "clearance_date",
            "remark",
            "creation",
            "modified",
            "owner",
            "total_amount_reimbursed"
        ]

    expense_claims = frappe.call(
                                 frappe.client.get_list, 
                                 "Expense Claim", 
                                 fields=fields, 
                                 filters=filters,
                                 or_filters=or_filters, 
                                 order_by=f"{sort_by} {sort_order}", 
                                 limit_start=start, 
                                 limit_page_length=page_size
                                )

    # expense_claims = frappe.get_all(
    #     "Expense Claim",
    #     filters=filters,
    #     or_filters = or_filters,
    #     fields=fields,
    #     order_by=f"{sort_by} {sort_order}",
    #     limit_start=start,
    #     limit_page_length=page_size,
    # )

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

    expense_map = {}

    for exp in expenses:
        expense_map[exp.parent] = {
            "expense_row_id": exp.name,
            "expense_date": exp.expense_date,
            "expense_type": exp.expense_type,
            "default_account": exp.default_account,
            "description": exp.description,
            "amount": exp.amount,
            "sanctioned_amount": exp.sanctioned_amount,
        }

    approver_names = {}

    approver_ids = list(
        {row.expense_approver for row in expense_claims if row.expense_approver}
    )

    users = []

    if approver_ids:
        users = frappe.get_all(
            "User",
            filters={
                "name": ["in", approver_ids],
            },
            fields=[
                "name",
                "full_name",
            ],
        )

    for user in users:
        approver_names[user.name] = user.full_name

    result = []

    for row in expense_claims:
        expense_data = expense_map.get(row.name, {})
        if row.approval_status  == "Cancelled" or row.approval_status == "Rejected":
            row.status = row.approval_status
        
        result.append(
            {
                "name": row.name,
                "employee": row.employee,
                "employee_name": row.employee_name,
                "expense_approver": row.expense_approver,
                "expense_approver_name": approver_names.get(row.expense_approver),
                "posting_date": row.posting_date,
                "approval_status": row.status,
                "currency": row.currency,
                "total_claimed_amount": row.total_claimed_amount,
                "clearance_date": row.clearance_date,
                "expense_type": expense_data.get("expense_type"),
                "expense_date": expense_data.get("expense_date"),
                "total_amount_reimbursed": row.total_amount_reimbursed,
            }
        )

    return result, total, total_pages
