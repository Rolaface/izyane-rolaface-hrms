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
            # doc.submit()

        elif status == "Cancelled":
            if current_docstatus == 1:
                doc.cancel()
                # doc.submit()
            else:
                # Draft — just delete or mark cancelled directly
                doc.approval_status = "Cancelled"
                doc.save(ignore_permissions=True)

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
        if db := getattr(frappe.local, "db", None):
            db.rollback(chain=True)
        frappe.log_error(frappe.get_traceback(), "Update Expense Claim Status Error")
        return send_response(
            status="fail",
            message=str(e),
            data=None,
            status_code=500,
            http_status=500
        )

@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_by_id():
    claim_id = frappe.request.args.get("id")

    if not claim_id:
        return send_response(
            status="fail",
            message="Expense Claim ID is required.",
            data=None,
            status_code=400,
            http_status=400
        )

    try:
        expense_claim = frappe.get_doc("Expense Claim", claim_id).as_dict()
        account_details = frappe.db.get_value("Account", expense_claim.get("payable_account"), 
                                              ["account_name", "account_number"], as_dict=True
                                              )
        if account_details["account_number"]:
            expense_claim["payable_account_name"] = f"{account_details.get('account_number', '')} - {account_details.get('account_name', '')}"
        else:
            expense_claim["payable_account_name"] = account_details.get("account_name", "")

        meta_fields = frappe.db.get_value(
                                            "Expense Claim",
                                            claim_id,
                                            ["_comments"],
                                            as_dict=True
                                        )
        attachments = frappe.db.get_all(
                                        "File",
                                        filters={
                                            "attached_to_doctype": "Expense Claim",
                                            "attached_to_name": expense_claim.name,
                                        },
                                        fields=[
                                            "name",
                                            "file_name",
                                            "file_url",
                                            "file_size",
                                            "file_type",
                                            "is_private",
                                            "creation",
                                        ],
                                        order_by="creation desc",
                                    )
        expense_claim["attachments"] = attachments
        expense_claim["comments"] = meta_fields.get("_comments", None)
        if expense_claim.get("advances"):
            for advance in expense_claim["advances"]:
                advance_doc = frappe.get_doc("Employee Advance", advance.employee_advance)
                advance["purpose"] = advance_doc.purpose

        return send_response(
            status="success",
            message="Expense Claim retrieved successfully.",
            data=expense_claim
        )
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Get Expense Claim By ID API Error",
        )

        return send_response(
            status="error",
            message=str(e),
            data=None,
            status_code=500,
            http_status=500,
        )
    
@frappe.whitelist(allow_guest=False, methods=["PUT"])
def update():
    try:
        claim_id = frappe.request.args.get("id")
        data = frappe.local.form_dict

        if not claim_id:
            return send_response(
                status="fail",
                message="Expense Claim ID is required.",
                data=None,
                status_code=400,
                http_status=400
            )

        doc = frappe.get_doc("Expense Claim", claim_id)
        doc.update(data)

        doc.save(ignore_permissions=True)

        return send_response(
            status="success",
            message="Expense Claim updated successfully.",
            data=doc,
            status_code=200,
            http_status=200
        )

    except Exception as e:
        if db := getattr(frappe.local, "db", None):
            db.rollback(chain=True)
        else:
            frappe.db.rollback()

        frappe.log_error(frappe.get_traceback(), "Update Expense Claim API Error")

        return send_response(
            status="fail",
            message=str(e),
            data=None,
            status_code=500,
            http_status=500
        )