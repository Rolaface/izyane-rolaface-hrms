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