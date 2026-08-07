import frappe


def _delete_records(doctype, filters=None):
    filters = filters or {}

    records = frappe.get_all(
        doctype,
        filters=filters,
        pluck="name",
    )

    print(f"\n{doctype}: {len(records)} record(s) found.")

    deleted = 0
    skipped = 0

    for record in records:
        try:
            frappe.delete_doc(
                doctype,
                record,
                force=True,
                ignore_permissions=True,
            )
            print(f"  ✓ {record}")
            deleted += 1

        except Exception as e:
            print(f"  ✗ {record} ({e})")
            skipped += 1

    print(f"Deleted: {deleted}, Skipped: {skipped}")


def _cleanup_departments():
    departments = frappe.get_all(
        "Department",
        filters={"is_group": 0},
        pluck="name",
    )

    print(f"\nDepartment: {len(departments)} leaf department(s) found.")

    deleted = 0
    skipped = 0

    for department in departments:
        try:
            frappe.delete_doc(
                "Department",
                department,
                force=True,
                ignore_permissions=True,
            )
            print(f"  ✓ {department}")
            deleted += 1

        except Exception as e:
            print(f"  ✗ {department} ({e})")
            skipped += 1

    print(f"Deleted: {deleted}, Skipped: {skipped}")


def _configure_payroll_payable_account():
    accounts = frappe.get_all(
        "Account",
        filters={"account_name": "Payroll Payable"},
        pluck="name",
    )

    if not accounts:
        print("\nPayroll Payable account not found. Skipping.")
        return

    for account in accounts:
        frappe.db.set_value(
            "Account",
            account,
            "account_type",
            "Payable",
            update_modified=False,
        )
        print(f"  ✓ Set '{account}' Account Type to Payable")


def cleanup_hrms():
    print("\nCleaning default HRMS master data...")

    _delete_records("Employment Type")
    _delete_records("Designation")
    _delete_records("Leave Type")
    _delete_records("Gender")
    _cleanup_departments()
    _delete_records("Expense Claim Type")

    _configure_payroll_payable_account()

    frappe.db.commit()

    print("\nHRMS cleanup completed.")