import frappe

from custom_hrms.utils.response import (
    send_response,
    send_response_list,
)

from . import service


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_expense_claim_types():
    try:
        page = int(frappe.request.args.get("page", 1))
        page_size = int(frappe.request.args.get("page_size", 20))

        search = frappe.request.args.get("search")

        sort_by = frappe.request.args.get(
            "sort_by",
            "modified",
        )

        sort_order = frappe.request.args.get(
            "sort_order",
            "desc",
        )

        (
            expense_claim_types,
            total,
            total_pages,
        ) = service.get_expense_claim_types(
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return send_response_list(
            status="success",
            message="Expense claim types retrieved successfully.",
            status_code=200,
            http_status=200,
            data={
                "success": True,
                "message": "Expense claim types retrieved successfully.",
                "data": expense_claim_types,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
            },
        )

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Get Expense Claim Types API Error",
        )

        return send_response(
            status="error",
            message=str(e),
            status_code=500,
            http_status=500,
        )


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_expense_claims():
    try:
        page = int(frappe.request.args.get("page", 1))
        page_size = int(frappe.request.args.get("page_size", 20))

        search = frappe.request.args.get("search")
        employee = frappe.request.args.get("employee")
        company = frappe.request.args.get("company")
        approval_status = frappe.request.args.get("approval_status")

        sort_by = frappe.request.args.get(
            "sort_by",
            "modified",
        )

        sort_order = frappe.request.args.get(
            "sort_order",
            "desc",
        )

        (
            expense_claims,
            total,
            total_pages,
        ) = service.get_expense_claims(
            page=page,
            page_size=page_size,
            search=search,
            employee=employee,
            company=company,
            approval_status=approval_status,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return send_response_list(
            status="success",
            message="Expense claims retrieved successfully.",
            status_code=200,
            http_status=200,
            data={
                "success": True,
                "message": "Expense claims retrieved successfully.",
                "data": expense_claims,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
            },
        )

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Get Expense Claims API Error",
        )

        return send_response(
            status="error",
            message=str(e),
            status_code=500,
            http_status=500,
        )

@frappe.whitelist(allow_guest=False, methods=["PUT"])
def update_expense_claim_status(claim_id: str, status: str):

    VALID_STATUSES = {"Draft", "Submitted", "Approved", "Rejected", "Cancelled"}

    if status not in VALID_STATUSES:
        return send_response(
            status="fail",
            message=f"Invalid status '{status}'. Allowed: {', '.join(VALID_STATUSES)}",
            data=None,
            status_code=400,
            http_status=400
        )

    if not frappe.db.exists("Expense Claim", claim_id):
        return send_response(
            status="fail",
            message=f"Expense Claim '{claim_id}' not found.",
            data=None,
            status_code=404,
            http_status=404
        )

    doc = frappe.get_doc("Expense Claim", claim_id)
    current_status = doc.status
    current_docstatus = doc.docstatus

    try:

        if status == "Approved" and current_docstatus == 0:
            doc.approval_status = "Approved"
            doc.status = "Approved"
            doc.approved_by = frappe.session.user
            doc.save(ignore_permissions=True)
            doc.submit()

        elif status == "Rejected" and current_docstatus == 0:
            doc.approval_status = "Rejected"
            doc.status = "Rejected"
            doc.approved_by = frappe.session.user
            doc.save(ignore_permissions=True)
            doc.submit()

        elif status == "Cancelled":
            if current_docstatus == 1:
                doc.cancel()
            else:
                # Draft — just delete or mark cancelled directly
                doc.status = "Cancelled"
                doc.save(ignore_permissions=True)
            doc.submit()

        return send_response(
            status="success",
            message=f"Expense Claim status updated from '{current_status}' to '{status}'.",
            data={
                "id":             doc.name,
                "previous_status": current_status,
                "current_status":  status,
                "updated_by":      frappe.session.user,
            },
            status_code=200,
            http_status=200
        )

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Update Expense Claim Status Error")
        return send_response(
            status="fail",
            message=str(e),
            data=None,
            status_code=500,
            http_status=500
        )