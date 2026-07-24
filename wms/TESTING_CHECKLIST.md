# Wahabix Medicare Solution — Full Testing Checklist

Test in this order (top to bottom) — later modules depend on data created
in earlier ones (e.g. Doctor needs a Reception token first).

**Demo logins** (username / password — all passwords are `Demo@12345`):
`wahabix` (Super Admin) · `admin_demo` (Clinic Admin) · `doctor_demo` ·
`lab_demo` · `reception_demo` · `pharmacy_demo` · `hr_demo` · `accounts_demo`

---

## 1. Login Page
- [ ] Page is fully styled (dark theme, logo, gradient button) — not plain HTML
- [ ] Demo quick-login buttons visible below Sign In
- [ ] Clicking a demo button logs in immediately (no typing needed)
- [ ] Wrong password shows an error message, doesn't crash

## 2. Super Admin (`wahabix`)
- [ ] Dashboard shows correct counts (clinics, staff, patients, audit logs)
- [ ] Clinics table — no overlapping/ghosted rows
- [ ] **Add Clinic** — create a new clinic, upload a logo → should save without error
- [ ] **Edit Clinic** — toggle modules on/off (Lab, Pharmacy, HR, Assets, etc.), save
- [ ] **Suspend / Activate** a clinic — staff of that clinic should be logged out on suspend
- [ ] Staff Management — list loads, no overlap
- [ ] Audit Logs — list loads, shows real actions with timestamps
- [ ] **Platform Settings** — change theme, save → applies to login page + every clinic

## 3. Clinic Admin (`admin_demo`)
- [ ] Dashboard loads
- [ ] Profile page — upload/change logo → should save (no InvalidStorageError)
- [ ] Staff list / add new staff member with a role

## 4. Reception (`reception_demo`)
- [ ] **Register Patient** — new patient saves, gets a Patient ID
- [ ] **Issue Token** — enter fee amount → Invoice auto-created, redirects to print
- [ ] Token print — print dialog opens directly, no new tab, no manual "back"
- [ ] Token List — Invoice column shows the linked invoice number
- [ ] **Pending Lab Payments** — empty until a doctor orders a lab test (see step 5)
- [ ] **Invoices** section — list, create new ad-hoc invoice, view, download, print
- [ ] Patient search/list — no overlapping rows

## 5. Doctor (`doctor_demo`)
- [ ] Dashboard — waiting queue shows today's tokens
- [ ] Patient Queue — "Call In" a patient
- [ ] **Write Prescription** — add medicines + select lab tests → save
- [ ] After saving with lab tests selected: check Reception → Pending Lab Payments — a new unpaid invoice should appear
- [ ] Prescription Detail — "🖨️ Print (Letterhead)" button → matches hospital Rx format with Urdu instructions
- [ ] Prescription list — 🖨️ quick-print icon works per row

## 6. Reception (again) — Collect Lab Payment
- [ ] Pending Lab Payments — the invoice from step 5 appears
- [ ] Click 🧾 to view invoice before paying
- [ ] Click "Collect Payment" → confirm dialog appears and actually submits (no silent fail)
- [ ] Invoice moves to "Recently Collected" section, still downloadable/printable

## 7. Laboratory (`lab_demo`)
- [ ] Lab Dashboard loads
- [ ] Test Catalog — 20 seeded tests visible, no row overlap
- [ ] **Add Test** — create a new test, saves correctly
- [ ] Lab Orders — the order from step 5 appears
- [ ] **Enter Results** — fill in results, click "Save Results & Mark Complete" → actually saves (this used to silently fail — confirm it's fixed)
- [ ] Result PDF — view, download, and 🖨️ print all work

## 8. Pharmacy (`pharmacy_demo`)
- [ ] Medicines list — 20 seeded medicines with stock visible
- [ ] **Smart POS** — fetch a token's RX cart → medicines matching stock should auto-load (test with a prescription using a seeded medicine name)
- [ ] Add item via search, confirm sale → total calculates correctly (no Decimal/float crash)
- [ ] Sales list — 📄 PDF view/download/🖨️ print all work

## 9. HR / Payroll (`hr_demo`)
- [ ] Staff attendance / list loads
- [ ] **Generate Payroll** — click "Generate Payroll Slips", confirm dialog → actually generates (confirm fix)
- [ ] Payroll list — 📄 PDF and 🖨️ Print both work

## 10. Accounts / Billing (`accounts_demo`)
- [ ] Dashboard loads
- [ ] Invoices — full list visible (including reception + lab-generated ones)
- [ ] Ledger Report — entries show for every collected payment (consultation, lab, pharmacy)
- [ ] Ledger 🖨️ Print button works
- [ ] Insurance Panels / Claims — batch-approve confirm dialog actually submits (confirm fix)

## 11. Assets (`admin_demo` or `hr_demo`)
- [ ] Asset Dashboard loads
- [ ] Register a new asset — saves with depreciation auto-calculating
- [ ] Log a service/maintenance entry against an asset

## 12. Cross-Cutting Checks
- [ ] Resize browser to phone width — sidebar collapses to hamburger menu, tables remain usable
- [ ] No page shows unstyled/plain HTML anywhere
- [ ] No page shows overlapping table headers/rows
- [ ] Every "Print" button opens the OS print dialog directly (not a blank page, not a new tab you have to close)

---

**When something's wrong:** screenshot the page (whole browser window, including the
URL bar) and send it — that's usually enough for me to find the exact bug.
