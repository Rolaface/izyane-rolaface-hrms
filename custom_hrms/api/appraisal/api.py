import frappe
from frappe.utils import cint
from custom_hrms.utils.response import send_response, send_response_list
from . import service

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_eligible_employees():
    try:
        page = cint(frappe.request.args.get("page", 1))
        page_size = cint(frappe.request.args.get("page_size", 20))
        company = frappe.request.args.get("company") or frappe.defaults.get_user_default("Company")

        filters = {"status": "Active"}
        if company:
            filters["company"] = company
            
        if frappe.request.args.get("department"):
            filters["department"] = frappe.request.args.get("department")
        if frappe.request.args.get("branch"):
            filters["branch"] = frappe.request.args.get("branch")
        if frappe.request.args.get("designation"):
            filters["designation"] = frappe.request.args.get("designation")
        if frappe.request.args.get("search"):
            search_term = frappe.request.args.get("search")
            filters["employee_name"] = ["like", f"%{search_term}%"]

        data, total_count, total_pages = service.get_eligible_employees(
            filters=filters, page=page, page_size=page_size
        )

        response_data = {
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            }
        }

        return send_response_list(
            status="success", 
            message="Employees retrieved successfully.", 
            status_code=200, 
            data=response_data, 
            http_status=200
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Eligible Employees API Error")
        return send_response(
            status="error", 
            message=f"Internal Server Error: {str(e)}", 
            status_code=500, 
            http_status=500
        )

@frappe.whitelist(allow_guest=False, methods=["POST"])
def start_appraisal_cycle(id=None):
    try:
        appraisal_cycle_id = id or frappe.request.args.get("id") or frappe.local.form_dict.get("id")

        if not appraisal_cycle_id:
            return send_response(status="fail", message="'id' is required.", status_code=400, http_status=400)

        if not frappe.db.exists("Appraisal Cycle", appraisal_cycle_id):
            return send_response(status="fail", message="Appraisal Cycle not found.", status_code=404, http_status=404)

        result = service.run_appraisal_cycle(appraisal_cycle_id)

        if isinstance(result, dict) and result.get("status") == "error":
            frappe.db.rollback()
            return send_response(
                status="error",
                message=result.get("message", "Appraisal Cycle processing failed."),
                data=result,
                status_code=400,
                http_status=400,
            )

        frappe.db.commit()

        return send_response(
            status="success",
            message="Appraisal Cycle processed successfully.",
            data=result,
            status_code=200,
            http_status=200,
        )

    except frappe.ValidationError as e:
        frappe.db.rollback()
        return send_response(status="fail", message=str(e), status_code=400, http_status=400)

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Start Appraisal Cycle API Error")
        return send_response(status="error", message="Failed to start cycle.", data={"error": str(e)}, status_code=500, http_status=500)

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_appraisal_cycles():
    try:
        page = cint(frappe.request.args.get("page", 1))
        page_size = cint(frappe.request.args.get("page_size", 20))
        company = frappe.request.args.get("company") or frappe.defaults.get_user_default("Company")

        search = frappe.request.args.get("search", "")
        sort_by = frappe.request.args.get("sort_by", "creation")
        sort_order = frappe.request.args.get("sort_order", "desc")

        filters = {}
        if company: filters["company"] = company
        if frappe.request.args.get("status"): filters["status"] = frappe.request.args.get("status")

        data, total_count, total_pages = service.get_appraisal_cycle_list(
            filters=filters, page=page, page_size=page_size, search=search, sort_by=sort_by, sort_order=sort_order
        )

        response_data = {
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            }
        }

        return send_response_list(status="success", message="Appraisal cycles retrieved successfully.", status_code=200, data=response_data, http_status=200)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Custom Get Appraisal Cycles API Error")
        return send_response(status="error", message=f"Internal Server Error: {str(e)}", status_code=500, http_status=500)

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_appraisal_cycle(id=None):
    try:
        appraisal_cycle_id = id or frappe.request.args.get("id")

        if not appraisal_cycle_id:
            return send_response(status="fail", message="'id' is required.", status_code=400, http_status=400)

        if not frappe.db.exists("Appraisal Cycle", appraisal_cycle_id):
            return send_response(status="fail", message="Appraisal Cycle not found.", status_code=404, http_status=404)

        result = service.get_appraisal_cycle_details(appraisal_cycle_id)

        return send_response(status="success", message="Appraisal cycle details retrieved successfully.", data=result, status_code=200, http_status=200)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Custom Get Appraisal Cycle Details API Error")
        return send_response(status="error", message=f"Internal Server Error: {str(e)}", status_code=500, http_status=500)