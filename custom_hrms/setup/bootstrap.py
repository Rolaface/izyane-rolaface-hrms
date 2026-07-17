from .cleanup_hrms import cleanup_hrms
# from .zambia_hrms import setup_zambia_hrms


def bootstrap():
    print("=" * 70)
    print("Starting HRMS Bootstrap")
    print("=" * 70)

    cleanup_hrms()

    # setup_zambia_hrms()

    # frappe.db.commit()

    print("\nHRMS Bootstrap Completed Successfully.")