import frappe


# ---------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------

def create_notification(user, subject, doctype, docname, notif_type="Alert"):
	"""Create a Notification Log entry + push realtime event to the user."""
	if not user:
		return

	frappe.get_doc({
		"doctype": "Notification Log",
		"subject": subject,
		"for_user": user,
		"type": notif_type,
		"document_type": doctype,
		"document_name": docname
	}).insert(ignore_permissions=True)

	frappe.publish_realtime(
		event="employee_notification",
		message={
			"subject": subject,
			"doctype": doctype,
			"doc": docname
		},
		user=user
	)


def get_user_from_employee(employee):
	"""Fetch the linked User (user_id) for a given Employee."""
	if not employee:
		return None
	return frappe.db.get_value("Employee", employee, "user_id")


# ---------------------------------------------------------------------
# 1. Leave Application
# ---------------------------------------------------------------------

def notify_leave_status(doc, method):
	if doc.status not in ["Approved", "Rejected"]:
		return

	before = doc.get_doc_before_save()
	if before and before.status == doc.status:
		return  # status didn't actually change, skip duplicate notification

	user = get_user_from_employee(doc.employee)
	subject = f"Your Leave Application ({doc.leave_type}) has been {doc.status}"
	create_notification(user, subject, "Leave Application", doc.name)


# ---------------------------------------------------------------------
# 2. Expense Claim
# ---------------------------------------------------------------------

def notify_expense_status(doc, method):
	if doc.approval_status not in ["Approved", "Rejected"]:
		return

	before = doc.get_doc_before_save()
	if before and before.approval_status == doc.approval_status:
		return

	user = get_user_from_employee(doc.employee)
	subject = f"Your Expense Claim of {doc.total_claimed_amount} has been {doc.approval_status}"
	create_notification(user, subject, "Expense Claim", doc.name)


# ---------------------------------------------------------------------
# 3. Salary Slip (Payslip generated)
# ---------------------------------------------------------------------

def notify_payslip_generated(doc, method):
	user = get_user_from_employee(doc.employee)
	subject = f"Payslip for {doc.start_date} to {doc.end_date} has been generated"
	create_notification(user, subject, "Salary Slip", doc.name)


# ---------------------------------------------------------------------
# 4. Holiday List (notify only when new holiday dates are added)
# ---------------------------------------------------------------------

def notify_holiday_update(doc, method):
	before = doc.get_doc_before_save()

	if before:
		old_dates = {h.holiday_date for h in before.holidays}
		new_dates = {h.holiday_date for h in doc.holidays}
		added = new_dates - old_dates
		if not added:
			return  # no new holiday added, skip

	employees = frappe.get_all(
		"Employee",
		filters={"holiday_list": doc.name, "status": "Active"},
		fields=["user_id"]
	)

	subject = "New holiday(s) added to your holiday list"
	for emp in employees:
		create_notification(emp.user_id, subject, "Holiday List", doc.name)


@frappe.whitelist()
def get_employee_notifications(limit=20):
	user = frappe.session.user

	notifications = frappe.get_all(
		"Notification Log",
		filters={"for_user": user},
		fields=["name", "subject", "document_type", "document_name",
				"read", "creation", "type"],
		order_by="creation desc",
		limit=limit
	)

	unread_count = frappe.db.count("Notification Log", {
		"for_user": user,
		"read": 0
	})

	return {
		"notifications": notifications,
		"unread_count": unread_count
	}


@frappe.whitelist()
def mark_as_read(notification_name):
	frappe.db.set_value("Notification Log", notification_name, "read", 1)
	frappe.db.commit()
	return {"success": True}


@frappe.whitelist()
def mark_all_as_read():
	frappe.db.sql("""
		UPDATE `tabNotification Log`
		SET `read` = 1
		WHERE for_user = %s AND `read` = 0
	""", (frappe.session.user,))
	frappe.db.commit()
	return {"success": True}