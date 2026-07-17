import frappe
from datetime import date, timedelta


# ==========================================
# 1. GENDERS
# ==========================================
def _create_gender(name):
    if frappe.db.exists("Gender", name):
        print(f"  • Gender '{name}' already exists.")
        return

    gender = frappe.get_doc(
        {
            "doctype": "Gender",
            "gender": name,
        }
    )

    gender.insert(ignore_permissions=True)
    print(f"  ✓ Created Gender: {name}")


def create_genders():
    print("\nCreating Genders...")
    for gender in ["Male", "Female", "Other"]:
        _create_gender(gender)


# ==========================================
# 2. LEAVE TYPES
# ==========================================
def _create_leave_type(name):
    if frappe.db.exists("Leave Type", name):
        print(f"  • Leave Type '{name}' already exists.")
        return

    doc = frappe.get_doc(
        {
            "doctype": "Leave Type",
            "leave_type_name": name,
        }
    )

    doc.insert(ignore_permissions=True)
    print(f"  ✓ Created Leave Type: {name}")


def create_leave_types():
    print("\nCreating Leave Types...")
    leave_types = [
        "Annual Leave",
        "Sick Leave",
        "Maternity Leave",
        "Paternity Leave",
        "Compassionate Leave",
        "Family Responsibility Leave",
        "Mother's Day Leave",
        "Study Leave",
        "Leave Without Pay",
    ]
    for leave_type in leave_types:
        _create_leave_type(leave_type)


# ==========================================
# 3. HOLIDAY LIST
# ==========================================
def create_holiday_list():
    year = date.today().year
    holiday_list_name = f"Holidays and Observances in Zambia in {year}"

    if frappe.db.exists("Holiday List", holiday_list_name):
        print(f"  • Holiday List '{holiday_list_name}' already exists.")
        holiday_list = frappe.get_doc("Holiday List", holiday_list_name)
    else:
        holiday_list = frappe.get_doc(
            {
                "doctype": "Holiday List",
                "holiday_list_name": holiday_list_name,
                "from_date": date(year, 1, 1),
                "to_date": date(year, 12, 31),
            }
        )

        current = holiday_list.from_date

        while current <= holiday_list.to_date:
            if current.weekday() == 6:  # Sunday
                holiday_list.append(
                    "holidays",
                    {
                        "holiday_date": current,
                        "description": "Weekly Off",
                        "weekly_off": 1,
                    },
                )
            current += timedelta(days=1)

        holiday_list.insert(ignore_permissions=True)
        print(f"  ✓ Created Holiday List: {holiday_list_name}")

    _assign_holiday_list_to_companies(holiday_list.name)


# def _assign_holiday_list_to_companies(holiday_list):
#     companies = frappe.get_all("Company", pluck="name")
    
#     start_date, end_date = frappe.db.get_value(
#         "Holiday List",
#         holiday_list,
#         ["from_date", "to_date"]
#     )

#     for company in companies:
#         frappe.db.set_value(
#             "Company",
#             company,
#             "default_holiday_list",
#             holiday_list,
#             update_modified=False,
#         )

#         if not frappe.db.exists(
#             "Holiday List Assignment",
#             {
#                 "assigned_to": company,
#                 "holiday_list": holiday_list,
#             },
#         ):
#             frappe.get_doc(
#                 {
#                     "doctype": "Holiday List Assignment",
#                     "assignment_based_on": "Company", 
#                     "assigned_to": company,          
#                     "holiday_list": holiday_list,
#                     "from_date": start_date,         
#                     "to_date": end_date
#                 }
#             ).insert(ignore_permissions=True)

#         print(f"  ✓ Assigned Holiday List to Company: {company}")

def _assign_holiday_list_to_companies(holiday_list):
    companies = frappe.get_all("Company", pluck="name")

    for company in companies:
        frappe.db.set_value(
            "Company",
            company,
            "default_holiday_list",
            holiday_list,
            update_modified=False,
        )

        print(f"  ✓ Assigned Holiday List to Company: {company}")

def _get_active_fiscal_year(company):
    # 1. Check if the company has a specific default set
    fy = frappe.get_cached_value("Company", company, "default_fiscal_year")
    if fy:
        return fy
        
    # 2. Fallback to the system's global default year
    fy = frappe.defaults.get_global_default("year")
    if fy:
        return fy
        
    # 3. Final fallback: Grab the most recent enabled fiscal year
    active_fys = frappe.get_all(
        "Fiscal Year", 
        filters={"disabled": 0}, 
        order_by="year_start_date desc", 
        pluck="name", 
        limit=1
    )
    if active_fys:
        return active_fys[0]
        
    return None


# ==========================================
# 4. PERIODS (PAYROLL & LEAVE)
# ==========================================
def create_periods():
    print("\nCreating Leave Periods and Payroll Periods...")
    companies = frappe.get_all("Company", pluck="name")

    for company in companies:
        fiscal_year = _get_active_fiscal_year(company)

        if not fiscal_year:
            print(f"  ✗ {company}: No active Fiscal Year could be found in the system.")
            continue

        fy = frappe.get_doc("Fiscal Year", fiscal_year)
        _create_leave_period(company, fy)
        _create_payroll_period(company, fy)

def _create_payroll_period(company, fiscal_year):
    if frappe.db.exists("Payroll Period", {
        "company": company,
        "payroll_frequency": "Monthly",
        "start_date": fiscal_year.year_start_date,
        "end_date": fiscal_year.year_end_date,
    }):
        print(f"  • Payroll Period already exists for {company}")
        return

    doc = frappe.get_doc({
        "doctype": "Payroll Period",
        "company": company,
        "payroll_frequency": "Monthly",
        "start_date": fiscal_year.year_start_date,
        "end_date": fiscal_year.year_end_date,
    })
    doc.insert(ignore_permissions=True)
    print(f"  ✓ Created Payroll Period for {company}")

def _create_leave_period(company, fiscal_year):
    if frappe.db.exists("Leave Period", {
        "company": company,
        "from_date": fiscal_year.year_start_date,
        "to_date": fiscal_year.year_end_date,
        "is_active": 1,
    }):
        print(f"  • Leave Period already exists for {company}")
        return

    doc = frappe.get_doc({
        "doctype": "Leave Period",
        "leave_period_name": f"{company} - {fiscal_year.name}",
        "company": company,
        "from_date": fiscal_year.year_start_date,
        "to_date": fiscal_year.year_end_date,
        "is_active": 1,
    })
    doc.insert(ignore_permissions=True)
    print(f"  ✓ Created Leave Period for {company}")


# ==========================================
# 5. INCOME TAX SLABS (PAYE)
# ==========================================
def create_income_tax_slabs():
    print("\nCreating Zambia PAYE Income Tax Slabs...")
    companies = frappe.get_all("Company", pluck="name")

    for company in companies:
        fiscal_year = _get_active_fiscal_year(company)

        if not fiscal_year:
            print(f"  ✗ {company}: No active Fiscal Year could be found in the system.")
            continue

        _create_income_tax_slab(company, fiscal_year)

def _create_income_tax_slab(company, fiscal_year):
    fy = frappe.get_doc("Fiscal Year", fiscal_year)

    if frappe.db.exists("Income Tax Slab", {
        "company": company,
        "effective_from": fy.year_start_date,
    }):
        print(f"  • Income Tax Slab already exists for {company}")
        return

    slab = frappe.get_doc({
        "doctype": "Income Tax Slab",
        "slab_name": f"{company} - PAYE - {fy.name}",
        "company": company,
        "disabled": 0,
        "effective_from": fy.year_start_date,
        "allow_tax_exemption": 1,
    })

    slabs = [
        {"from_amount": 0, "to_amount": 61200, "percent_deduction": 0},
        {"from_amount": 61200.01, "to_amount": 85200, "percent_deduction": 20},
        {"from_amount": 85200.01, "to_amount": 110400, "percent_deduction": 30},
        {"from_amount": 110400.01, "percent_deduction": 37},
    ]

    for s in slabs:
        slab.append("slabs", s)

    slab.insert(ignore_permissions=True)
    print(f"  ✓ Created PAYE Income Tax Slab for {company}")


# ==========================================
# 6. GL ACCOUNTS
# ==========================================
def _get_parent_account(company, company_abbr, root_type, search_terms):
    for term in search_terms:
        parent_name = f"{term} - {company_abbr}"
        if frappe.db.exists("Account", parent_name):
            return parent_name

    fallback = frappe.db.get_value(
        "Account", {"company": company, "is_group": 1, "root_type": root_type}, "name"
    )
    return fallback


def create_zambia_gl_accounts():
    print("\nCreating Zambia-specific GL Accounts...")
    companies = frappe.get_all("Company", fields=["name", "abbr"])

    accounts_to_create = [
        # Liabilities
        {
            "name": "NHIMA Payable",
            "root_type": "Liability",
            "parents": ["Duties and Taxes", "Current Liabilities"],
            "account_type": "Payable",
        },
        {
            "name": "NAPSA Payable",
            "root_type": "Liability",
            "parents": ["Duties and Taxes", "Current Liabilities"],
            "account_type": "Payable",
        },
        {
            "name": "PAYE Payable",
            "root_type": "Liability",
            "parents": ["Duties and Taxes", "Current Liabilities"],
            "account_type": "Payable",
        },
        # Expenses
        {
            "name": "Salary Expense",
            "root_type": "Expense",
            "parents": ["Indirect Expenses", "Expenses"],
            "account_type": "Expense Account",
        },
        {
            "name": "NHIMA Employer",
            "root_type": "Expense",
            "parents": ["Indirect Expenses", "Expenses"],
            "account_type": "Expense Account",
        },
        {
            "name": "NAPSA Employer",
            "root_type": "Expense",
            "parents": ["Indirect Expenses", "Expenses"],
            "account_type": "Expense Account",
        },
        # Assets
        {
            "name": "Salary Advance",
            "root_type": "Asset",
            "parents": ["Current Assets", "Loans and Advances (Assets)"],
            "account_type": "Receivable",
        },
        {
            "name": "Employee Loan",
            "root_type": "Asset",
            "parents": ["Current Assets", "Loans and Advances (Assets)"],
            "account_type": "Receivable",
        },
    ]

    for company in companies:
        for acc in accounts_to_create:
            full_account_name = f"{acc['name']} - {company.abbr}"

            if frappe.db.exists("Account", full_account_name):
                print(f"  • Account '{full_account_name}' already exists.")
                continue

            parent_account = _get_parent_account(
                company.name, company.abbr, acc["root_type"], acc["parents"]
            )

            if not parent_account:
                print(
                    f"  ✗ Could not find a suitable parent account for '{acc['name']}' in {company.name}. Skipping."
                )
                continue

            doc = frappe.get_doc(
                {
                    "doctype": "Account",
                    "account_name": acc["name"],
                    "company": company.name,
                    "parent_account": parent_account,
                    "is_group": 0,
                    "root_type": acc["root_type"],
                    "account_type": acc.get("account_type", ""),
                }
            )

            try:
                doc.insert(ignore_permissions=True)
                print(
                    f"  ✓ Created GL Account: {full_account_name} (Under {parent_account})"
                )
            except Exception as e:
                print(f"  ✗ Failed to create {full_account_name}: {e}")


# ==========================================
# 7. SALARY COMPONENTS (WITH ACCOUNT MAPPING)
# ==========================================
def _create_salary_component(component, companies):
    existing = frappe.db.exists(
        "Salary Component", {"salary_component": component["salary_component"]}
    )

    if existing:
        print(f"  • Salary Component '{component['salary_component']}' already exists.")
        return

    # Extract the base account name if provided
    base_account_name = component.pop("default_account_name", None)

    defaults = {
        "doctype": "Salary Component",
        "depends_on_payment_days": 0,
        "is_tax_applicable": 0,
        "deduct_full_tax_on_selected_payroll_date": 0,
        "variable_based_on_taxable_salary": 0,
        "is_income_tax_component": 0,
        "exempted_from_income_tax": 0,
        "round_to_the_nearest_integer": 0,
        "statistical_component": 0,
        "accrual_component": 0,
        "do_not_include_in_total": 0,
        "do_not_include_in_accounts": 0,
        "remove_if_zero_valued": 1,
        "arrear_component": 0,
        "disabled": 0,
        "amount": 0,
        "amount_based_on_formula": 0,
        "formula": "",
        "is_flexible_benefit": 0,
        "payout_method": "",
        "final_cycle_accrual_payout": 0,
        "max_benefit_amount": 0,
    }

    defaults.update(component)
    doc = frappe.get_doc(defaults)

    # Map the GL accounts per company in the child table
    if base_account_name:
        for company in companies:
            full_account_name = f"{base_account_name} - {company.abbr}"
            if frappe.db.exists("Account", full_account_name):
                doc.append(
                    "accounts",
                    {"company": company.name, "default_account": full_account_name},
                )
            else:
                print(
                    f"  ⚠ Warning: GL Account '{full_account_name}' not found for {company.name}."
                )

    doc.insert(ignore_permissions=True)
    print(f"  ✓ Created Salary Component: {doc.salary_component}")


def create_salary_components():
    print("\nCreating Salary Components...")
    companies = frappe.get_all("Company", fields=["name", "abbr"])

    salary_components = [
        # --- Standard Earnings (Map to Salary Expense) ---
        {
            "salary_component": "Basic Salary",
            "salary_component_abbr": "BS",
            "type": "Earning",
            "depends_on_payment_days": 1,
            "is_tax_applicable": 1,
            "amount_based_on_formula": 1,
            "formula": "base * 1",
            "default_account_name": "Salary Expense",
        },
        {
            "salary_component": "Housing Allowance",
            "salary_component_abbr": "HA",
            "type": "Earning",
            "is_tax_applicable": 1,
            "default_account_name": "Salary Expense",
        },
        {
            "salary_component": "Transport Allowance",
            "salary_component_abbr": "TA",
            "type": "Earning",
            "is_tax_applicable": 1,
            "default_account_name": "Salary Expense",
        },
        {
            "salary_component": "Medical Allowance",
            "salary_component_abbr": "MA",
            "type": "Earning",
            "is_tax_applicable": 1,
            "default_account_name": "Salary Expense",
        },
        {
            "salary_component": "Lunch Allowance",
            "salary_component_abbr": "LA",
            "type": "Earning",
            "is_tax_applicable": 1,
            "default_account_name": "Salary Expense",
        },
        {
            "salary_component": "Allowances",
            "salary_component_abbr": "ALLOW",
            "type": "Earning",
            "is_tax_applicable": 1,
            "default_account_name": "Salary Expense",
        },
        {
            "salary_component": "Bonus",
            "salary_component_abbr": "BONUS",
            "type": "Earning",
            "is_tax_applicable": 1,
            "default_account_name": "Salary Expense",
        },
        {
            "salary_component": "Leave Encashment",
            "salary_component_abbr": "LE",
            "type": "Earning",
            "is_tax_applicable": 1,
            "default_account_name": "Salary Expense",
        },
        # --- Loan / Advance Earnings (Map to their respective Assets) ---
        {
            "salary_component": "Salary Advance",
            "salary_component_abbr": "SALADV",
            "type": "Earning",
            "default_account_name": "Salary Advance",
        },
        {
            "salary_component": "Loan",
            "salary_component_abbr": "LOAN",
            "type": "Earning",
            "default_account_name": "Employee Loan",
        },
        # --- Employer Contributions (Earnings but statistical) ---
        {
            "salary_component": "NAPSA Employer",
            "salary_component_abbr": "NAPSAR",
            "type": "Earning",
            "amount_based_on_formula": 1,
            "formula": "(gross_pay * 0.05) if ((gross_pay * 0.05) < 1861.80) else 1861.80",
            "do_not_include_in_total": 1,
            "default_account_name": "NAPSA Employer",
        },
        {
            "salary_component": "NHIMA Employer",
            "salary_component_abbr": "NHIMAR",
            "type": "Earning",
            "amount_based_on_formula": 1,
            "formula": "BS * 0.01",
            "do_not_include_in_total": 1,
            "default_account_name": "NHIMA Employer",
        },
        # --- Deductions ---
        {
            "salary_component": "PAYE",
            "salary_component_abbr": "PAYE",
            "type": "Deduction",
            "variable_based_on_taxable_salary": 1,
            "is_income_tax_component": 1,
            "default_account_name": "PAYE Payable",
        },
        {
            "salary_component": "NAPSA Employee",
            "salary_component_abbr": "NAPSAE",
            "type": "Deduction",
            "amount_based_on_formula": 1,
            "formula": "(gross_pay * 0.05) if ((gross_pay * 0.05) < 1861.80) else 1861.80",
            "default_account_name": "NAPSA Payable",
        },
        {
            "salary_component": "NHIMA Employee",
            "salary_component_abbr": "NHIMAE",
            "type": "Deduction",
            "amount_based_on_formula": 1,
            "formula": "BS * 0.01",
            "default_account_name": "NHIMA Payable",
        },
        {
            "salary_component": "Salary Advance Repayment",
            "salary_component_abbr": "SALREPAY",
            "type": "Deduction",
            "default_account_name": "Salary Advance",
        },
        {
            "salary_component": "Loan Repayment",
            "salary_component_abbr": "LOANREPAY",
            "type": "Deduction",
            "default_account_name": "Employee Loan",
        }
    ]

    for component in salary_components:
        _create_salary_component(component, companies)


# ==========================================
# 8. MAIN RUNNER
# ==========================================
def setup_zambia_hrms():
    print("\nSetting up Zambia HRMS...")

    create_genders()
    create_leave_types()
    create_holiday_list()
    create_periods()
    create_income_tax_slabs()
    create_zambia_gl_accounts()  # Must run BEFORE salary components
    create_salary_components()

    frappe.db.commit()

    print("\nZambia HRMS setup completed.")
