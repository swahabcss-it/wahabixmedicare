"""
Sub-module registry — the canonical list of granular features inside each
top-level module (reception, laboratory, doctor, pharmacy, billing, hr,
assets). Two different screens read this SAME registry:

  1. Super Admin -> Clinic Detail: decides which sub-modules are even
     available to a given clinic's subscription plan (Clinic.submodule_map).
  2. Clinic Admin -> Staff Edit: decides, from what the clinic actually has
     enabled, which sub-modules a specific staff member can use
     (StaffProfile.enabled_submodules).

A staff member's access is always the INTERSECTION of both layers — see
`effective_submodules()` below. This mirrors the platform's three-layer
model: Super Admin (subscription) -> Clinic Admin (staff assignment) ->
action-level flags (StaffProfile.can_delete_lab_results etc.).

Insurance/TPA sub-modules are intentionally NOT included yet (module is
paused for the current build phase).
"""

SUBMODULE_REGISTRY = {
    "reception": [
        ("token_queue", "Live Token Queue"),
        ("patient_registration", "Patient Registration"),
        ("vitals_logging", "Vitals Logging"),
        ("shift_management", "Cash Shift Management"),
    ],
    "doctor": [
        ("consultation", "Consultation / EHR"),
        ("prescriptions", "Prescription Writing"),
        ("treatment_templates", "Treatment Templates"),
        ("patient_history", "Full Patient History"),
    ],
    "lab": [
        ("sample_collection", "Sample Collection"),
        ("result_entry", "Result Entry"),
        ("report_generation", "Graphical Report Generation"),
        ("stock_requests", "Consumables / Stock Requests"),
    ],
    "pharmacy": [
        ("dispense_prescription", "Dispense Against Prescription"),
        ("walkin_pos", "Walk-in POS Sale"),
        ("inventory_management", "Inventory / Batch Management"),
        ("expiry_alerts", "Near-Expiry Alerts"),
    ],
    "billing": [
        ("invoicing", "Invoice Generation"),
        ("payments", "Payment Collection"),
        ("ledger", "General Ledger"),
        ("balance_sheet", "Balance Sheet / P&L"),
    ],
    "hr": [
        ("employee_directory", "Employee Directory"),
        ("attendance", "Attendance"),
        ("leave_management", "Leave Management"),
        ("payroll", "Payroll / Salary Slips"),
    ],
    "assets": [
        ("asset_registry", "Asset Registry"),
        ("depreciation", "Depreciation Tracking"),
        ("service_logs", "Service / Calibration Logs"),
        ("stock_requisition", "Stock Requisition Approval"),
    ],
}

MODULE_LABELS = {
    "reception": "Reception", "doctor": "Doctor / OPD", "lab": "Laboratory",
    "pharmacy": "Pharmacy", "billing": "Billing & Accounts",
    "hr": "HR & Payroll", "assets": "Asset Management",
}

# Maps each top-level module to the Clinic boolean flag that gates it.
MODULE_CLINIC_FLAG = {
    "reception": "is_reception_enabled", "doctor": "is_doctor_enabled",
    "lab": "is_lab_enabled", "pharmacy": "is_pharmacy_enabled",
    "billing": "is_billing_enabled", "hr": "is_hr_enabled",
    "assets": "is_assets_enabled",
}


def default_submodule_map() -> dict:
    """Everything on by default for a brand-new clinic (Super Admin can trim later)."""
    return {
        module: {key: True for key, _label in items}
        for module, items in SUBMODULE_REGISTRY.items()
    }


def clinic_enabled_submodules(clinic) -> dict:
    """What the CLINIC (subscription) has access to, module -> {key: bool}."""
    stored = clinic.submodule_map or {}
    result = {}
    for module, items in SUBMODULE_REGISTRY.items():
        if not getattr(clinic, MODULE_CLINIC_FLAG[module], True):
            result[module] = {key: False for key, _ in items}
            continue
        stored_module = stored.get(module, {})
        result[module] = {key: stored_module.get(key, True) for key, _ in items}
    return result


def effective_submodules(staff_profile) -> dict:
    """
    What THIS STAFF MEMBER can actually use: intersection of clinic-level
    (subscription) access and staff-level (Clinic Admin assigned) access.
    """
    clinic_level = clinic_enabled_submodules(staff_profile.clinic)
    staff_level = staff_profile.enabled_submodules or {}
    result = {}
    for module, subs in clinic_level.items():
        staff_module = staff_level.get(module, {})
        result[module] = {
            key: bool(clinic_on) and bool(staff_module.get(key, False))
            for key, clinic_on in subs.items()
        }
    return result


def has_submodule(staff_profile, module: str, submodule: str) -> bool:
    if staff_profile.role == "clinic_admin":
        # Clinic Admins always see everything the clinic's subscription allows.
        return clinic_enabled_submodules(staff_profile.clinic).get(module, {}).get(submodule, False)
    return effective_submodules(staff_profile).get(module, {}).get(submodule, False)
