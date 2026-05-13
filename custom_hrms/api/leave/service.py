import math

from hrms.hr.doctype.department_approver.department_approver import (
    get_approvers,
)


def get_leave_approvers(filters, page=1, page_size=20):
    approvers = list(
        get_approvers(
            txt="",
            doctype="User",
            searchfield="name",
            start=0,
            page_len=999999,
            filters=filters,
        )
    )

    total_approvers = len(approvers)
    total_pages = math.ceil(total_approvers / page_size)

    start = (page - 1) * page_size
    end = start + page_size

    paginated_approvers = approvers[start:end]

    data = [
        {
            "value": approver[0],
            "label": " ".join(filter(None, approver[1:])).strip(),
            "description": approver[0],
        }
        for approver in paginated_approvers
    ]

    return data, total_approvers, total_pages
