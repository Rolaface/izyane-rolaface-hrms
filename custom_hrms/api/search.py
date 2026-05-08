import frappe
from custom_hrms.utils.response import send_response, send_response_list
from frappe.desk.search import build_for_autosuggest, search_widget

def _get_pagination_args():
    try:
        page = int(frappe.request.args.get("page", 1))
        page_size = int(frappe.request.args.get("page_size", 10))
    except ValueError:
        page, page_size = 1, 10
    return page, page_size

def _fetch_paginated_autosuggest(
    doctype,
    filters=None,
    search_fields=None,
    field_map=None,
):
    txt = frappe.request.args.get("search", "").strip()
    page, page_size = _get_pagination_args()
    start = (page - 1) * page_size

    filters = filters or {}
    search_fields = search_fields or ["name"]

    or_filters = []
    if txt:
        for field in search_fields:
            or_filters.append([doctype, field, "like", f"%{txt}%"])

    required_fields = {"name"}
    if field_map:
        for value in field_map.values():
            if isinstance(value, str):
                required_fields.add(value)
            elif isinstance(value, (list, tuple)):
                required_fields.update(value)

    rows = frappe.get_all(
        doctype,
        filters=filters,
        or_filters=or_filters if txt else None,
        fields=list(required_fields),
        limit_start=start,
        limit_page_length=page_size,
        order_by="modified desc",
    )

    def resolve(row, mapper):
        if callable(mapper):
            return mapper(row)
        if isinstance(mapper, str):
            return row.get(mapper)
        if isinstance(mapper, (list, tuple)):
            return " ".join(str(row.get(f) or "") for f in mapper).strip()
        return None

    response_data = []
    for row in rows:
        if field_map:
            item = {key: resolve(row, mapper) for key, mapper in field_map.items()}
        else:
            item = {
                "value": row.get("name"),
                "label": row.get("name"),
                "description": row.get("name"),
            }
        response_data.append(item)

    if txt and search_fields:
        count_result = frappe.get_all(
            doctype,
            filters=filters,
            or_filters=or_filters,
            fields=[{"COUNT": "name"}],
            as_list=True,
        )
        total_items = count_result[0][0] if count_result and count_result[0] else 0
    else:
        total_items = frappe.db.count(doctype, filters=filters)

    total_pages = ((total_items + page_size - 1) // page_size if page_size else 1)

    return {
        "data": response_data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "items_in_page": len(response_data),
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
    }
    
# @frappe.whitelist(allow_guest=False, methods=["GET"])
# def get_items():
#     try:
#         filters = frappe._dict({})

#         is_fixed_asset = frappe.request.args.get("is_fixed_asset")
#         if is_fixed_asset is not None:
#             filters["is_fixed_asset"] = int(is_fixed_asset)

#         data = _fetch_paginated_autosuggest(
#             doctype="Item",
#             filters=filters,
#             search_fields=["name", "item_name"],
#             field_map={
#                 "value": "name",
#                 "label": "item_name",
#                 "description": "name",
#             },
#         )

#         return send_response_list(
#             "success", "Item Codes fetched successfully.", data
#         )

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Get Item Codes API Error")
#         return send_response("fail", str(e), None, 500, 500)
    
@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_designations():
    try:
        data = _fetch_paginated_autosuggest(
            doctype="Designation",
            filters=frappe._dict({}),
            search_fields=["name", "designation_name"],
            field_map={
                "value": "name",
                "label": "designation_name",
                "description": "name",
            },
        )
        return send_response_list("success", "Designations fetched successfully.", data)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Designations API Error")
        return send_response("fail", str(e), None, 500, 500)

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_salary_structures():
    try:
        data = _fetch_paginated_autosuggest(
            doctype="Salary Structure",
            filters=frappe._dict({}),
            search_fields=["name"],
            field_map={
                "value": "name",
                "label": "name",
                "description": "name",
            },
        )
        return send_response_list("success", "Salary Structures fetched successfully.", data)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Salary Structures API Error")
        return send_response("fail", str(e), None, 500, 500)

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_leave_policies():
    try:
        data = _fetch_paginated_autosuggest(
            doctype="Leave Policy",
            filters=frappe._dict({}),
            search_fields=["name", "title"],
            field_map={
                "value": "name",
                "label": "title",
                "description": "name",
            },
        )
        return send_response_list("success", "Leave Policies fetched successfully.", data)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Leave Policies API Error")
        return send_response("fail", str(e), None, 500, 500)

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_leave_types():
    try:
        data = _fetch_paginated_autosuggest(
            doctype="Leave Type",
            filters=frappe._dict({}),
            search_fields=["name", "leave_type_name"],
            field_map={
                "value": "name",
                "label": "leave_type_name",
                "description": "name",
            },
        )
        return send_response_list("success", "Leave Types fetched successfully.", data)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Leave Types API Error")
        return send_response("fail", str(e), None, 500, 500)
    
@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_departments():
    try:
        data = _fetch_paginated_autosuggest(
            doctype="Department",
            filters=frappe._dict({}),
            search_fields=["name", "department_name"],
            field_map={
                "value": "name",
                "label": "department_name",
                "description": "name",
            },
        )
        return send_response_list("success", "Departments fetched successfully.", data)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Departments API Error")
        return send_response("fail", str(e), None, 500, 500)

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_employment_types():
    try:
        data = _fetch_paginated_autosuggest(
            "Employment Type", frappe._dict({}), ["name", "employment_type_name"]
        )
        return send_response_list("success", "Employment Types fetched successfully.", data)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Employment Types API Error")
        return send_response("fail", str(e), None, 500, 500)

@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_users():
    try:
        data = _fetch_paginated_autosuggest(
            doctype="User",
            filters=frappe._dict({}),
            search_fields=["name", "full_name"],
            field_map={
                "value": "name",
                "label": "full_name",
                "description": "name",
            },
        )
        return send_response_list("success", "Users fetched successfully.", data)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Users API Error")
        return send_response("fail", str(e), None, 500, 500)
    
@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_employee_grades():
    try:
        data = _fetch_paginated_autosuggest(
            "Employee Grade", frappe._dict({}), ["name", "employee_grade_name"]
        )
        return send_response_list("success", "Employee Grades fetched successfully.", data)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Employee Grades API Error")
        return send_response("fail", str(e), None, 500, 500)
    
@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_employees():
    try:
        data = _fetch_paginated_autosuggest(
            doctype="Employee",
            filters=frappe._dict({}),
            search_fields=["name", "employee_name"],
            field_map={
                "value": "name",
                "label": "employee_name",
                "description": "name",
            },
        )

        return send_response_list("success","Employees fetched successfully.",data,)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(),"Get Employees API Error")
        return send_response("fail",str(e),None,500,500)
    