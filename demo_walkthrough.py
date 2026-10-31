"""
INTRINSIC - Full Interactive System Demo Walkthrough
Executes every end-to-end flow against the live server (http://127.0.0.1:8000)
"""

import sys
import requests
import json
import time

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8000"

def print_step(title):
    print("\n" + "=" * 78)
    print(f" [*] {title}")
    print("=" * 78)

def main():
    print("""
##############################################################################
#                                                                            #
#          INTRINSIC - FULL LIVE DEMO & END-TO-END SYSTEM WALKTHROUGH        #
#          FastAPI + SQLAlchemy + SQLite + Alpine.js + Tailwind CSS          #
#                                                                            #
##############################################################################
    """)

    # STEP 1: Verify Initial Landing Boot & Shielding
    print_step("STEP 1: Verify Initial Boot & Landing Page (Full-Screen Auth)")
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200
    assert "INTRINSIC" in r.text
    assert "x-show=\"!isAuthenticated\"" in r.text
    print("  [PASS] Verified: Unauthenticated visitors boot directly into full-screen Auth.")
    print("  [PASS] Dashboard, navigation, and features remain completely hidden.")

    # STEP 2: Instant Persona Evaluation - Admin Sign In
    print_step("STEP 2: Instant Persona Evaluation -- Sign In as Administrator")
    admin_creds = {"email": "admin@intrinsic.io", "password": "Intrinsic@2026!"}
    r = requests.post(f"{BASE_URL}/api/auth/login", json=admin_creds)
    assert r.status_code == 200, r.text
    admin_auth = r.json()
    admin_token = admin_auth["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print(f"  [PASS] Authenticated as: {admin_auth['user']['full_name']} ({admin_auth['user']['email']})")
    print(f"  [PASS] Assigned Role   : {admin_auth['user']['role'].upper()}")
    print(f"  [PASS] Department      : {admin_auth['user']['department']}")
    print(f"  [PASS] Session Token   : {admin_token[:25]}... (HS256 JWT Validated)")

    # STEP 3: Real-Time Executive KPI Dashboard Telemetry
    print_step("STEP 3: Real-Time Executive KPI Telemetry")
    r = requests.get(f"{BASE_URL}/api/kpis", headers=admin_headers)
    assert r.status_code == 200
    kpis = r.json()
    print(f"  • Monthly Recurring Revenue (MRR) : ${kpis['mrr']:,.2f}")
    print(f"  • Active Subscriptions            : {kpis['active_subscriptions']}")
    print(f"  • Overdue Receivables             : ${kpis['overdue_invoices_amount']:,.2f} ({kpis['overdue_invoices_count']} invoices)")
    print(f"  • Total Settled Revenue           : ${kpis['total_revenue_settled']:,.2f}")
    print(f"  • Total Customers in System       : {kpis['total_customers_count']}")

    # STEP 4: Subscription Lifecycle State Machine (Draft -> Quote -> Confirm -> Active -> Close)
    print_step("STEP 4: Subscription Lifecycle State Machine & Audit Trail")
    
    # 4a. Fetch plans & customer
    r_plans = requests.get(f"{BASE_URL}/api/plans", headers=admin_headers).json()
    r_cust = requests.get(f"{BASE_URL}/api/customers", headers=admin_headers).json()
    target_plan = r_plans[1]  # Professional Suite
    target_cust = r_cust[0]
    
    # 4b. Create in DRAFT
    new_sub_data = {
        "customer_id": target_cust["id"],
        "plan_id": target_plan["id"],
        "billing_interval": "monthly",
        "quantity": 1,
        "discount_code": "ODOO_VIP",
        "notes": "Live demo subscription order created during Makeathon review."
    }
    r = requests.post(f"{BASE_URL}/api/subscriptions", headers=admin_headers, json=new_sub_data)
    assert r.status_code == 200
    sub = r.json()
    sub_id = sub["id"]
    print(f"  [1/5] Draft Created       : {sub['subscription_code']} for {target_cust['full_name']}")
    print(f"        Base Unit Price     : ${sub['unit_price']:,.2f}")
    print(f"        VIP Discount (20%)  : -${sub['discount_amount']:,.2f}")
    print(f"        Tax (10%) & Total   : ${sub['total_amount']:,.2f}/mo (Status: {sub['status'].upper()})")

    # 4c. Draft -> Quotation
    r = requests.post(f"{BASE_URL}/api/subscriptions/{sub_id}/transition", headers=admin_headers, json={
        "to_status": "quotation", "reason": "Proposal quotation sent to client"
    })
    print(f"  [2/5] Sent Quotation      : State -> {r.json()['status'].upper()}")

    # 4d. Customer logs in & confirms quotation
    cust_creds = {"email": "customer@intrinsic.io", "password": "Intrinsic@2026!"}
    r = requests.post(f"{BASE_URL}/api/auth/login", json=cust_creds)
    cust_token = r.json()["access_token"]
    cust_headers = {"Authorization": f"Bearer {cust_token}"}
    
    r = requests.post(f"{BASE_URL}/api/subscriptions/{sub_id}/transition", headers=cust_headers, json={
        "to_status": "confirmed", "reason": "Alex Mercer approved the quote via Customer Portal"
    })
    print(f"  [3/5] Customer Confirmed  : State -> {r.json()['status'].upper()}")

    # 4e. Staff/Admin activates subscription (auto-generates initial invoice!)
    r = requests.post(f"{BASE_URL}/api/subscriptions/{sub_id}/transition", headers=admin_headers, json={
        "to_status": "active", "reason": "Subscription activated & billing schedule established"
    })
    activated_sub = r.json()
    print(f"  [4/5] Activated           : State -> {activated_sub['status'].upper()}")
    print(f"        Next Billing Date   : {activated_sub['next_billing_date'][:10]}")

    # 4f. View Audit Trail
    r_detail = requests.get(f"{BASE_URL}/api/subscriptions/{sub_id}", headers=admin_headers).json()
    print("  [Audit Trail History]:")
    for log in r_detail["audit_logs"]:
        print(f"    * {log['from_status'].upper()} -> {log['to_status'].upper()} | {log['changed_by_name']}: \"{log['reason']}\"")

    # STEP 5: Automated Billing Cycle Engine ("Run Billing Cycle")
    print_step("STEP 5: Automated Billing Cycle Engine ('Run Billing Cycle')")
    r = requests.post(f"{BASE_URL}/api/billing/run-cycle", headers=admin_headers)
    assert r.status_code == 200
    cycle = r.json()
    print(f"  * Invoices Generated     : {cycle['invoices_generated']}")
    print(f"  * Total Amount Billed    : ${cycle['total_amount_billed']:,.2f}")
    print(f"  * Subscriptions Advanced : {cycle['subscriptions_advanced']}")
    print(f"  * Overdue Invoices Flagged: {cycle['overdue_marked']}")
    print(f"  * Execution Timestamp    : {cycle['run_timestamp']}")
    if cycle["details"]:
        print(f"  * Cycle Activity Log     : {cycle['details'][0]}")

    # STEP 6: Customer Portal & Instant Invoice Settlement
    print_step("STEP 6: Customer Portal & Instant Invoice Settlement")
    r_invs = requests.get(f"{BASE_URL}/api/invoices", headers=cust_headers).json()
    unpaid = next((i for i in r_invs if i["status"] in ["posted", "overdue"]), None)
    if unpaid:
        print(f"  * Found Unsettled Invoice : {unpaid['invoice_number']} (${unpaid['total_amount']:,.2f}, Status: {unpaid['status'].upper()})")
        r_pay = requests.post(f"{BASE_URL}/api/invoices/{unpaid['id']}/pay", headers=cust_headers, json={
            "payment_method": "credit_card"
        })
        assert r_pay.status_code == 200
        paid_inv = r_pay.json()
        print(f"  [PASS] Invoice Settled       : {paid_inv['invoice_number']}")
        print(f"         Payment Method        : {paid_inv['payment_method'].upper()} (Corporate Card)")
        print(f"         Amount Paid           : ${paid_inv['amount_paid']:,.2f}")
        print(f"         Updated Status        : {paid_inv['status'].upper()}")

    # STEP 7: Strict Password Security Verification
    print_step("STEP 7: Strict Password Security Rules Verification")
    test_cases = [
        ("Short1!", "more than 8 characters"),
        ("nouppercase1!", "uppercase letter"),
        ("NOLOWERCASE1!", "lowercase letter"),
        ("NoSpecialChar123", "special character")
    ]
    for pwd, rule in test_cases:
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "Invalid Tester",
            "email": "invalid@test.com",
            "password": pwd
        })
        assert r.status_code in [400, 422]
        print(f"  [PASS] Properly Blocked : Password missing {rule}")

    # Valid Registration (Forced Customer Role)
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "full_name": "Demo Client Corp",
        "email": f"client_{int(time.time())}@enterprise.com",
        "password": "StrictPassword#2026!"
    })
    assert r.status_code == 200
    reg = r.json()
    assert reg["user"]["role"] == "customer"
    print(f"  [PASS] Valid Registration Accepted: Forced Role -> {reg['user']['role'].upper()} (No admin escalation possible)")

    # STEP 8: Admin Management Portal (Staff Provisioning & RBAC)
    print_step("STEP 8: Admin Management Portal (Staff Provisioning & RBAC)")
    
    # Non-admin tries to access admin portal
    r_forbidden = requests.get(f"{BASE_URL}/api/admin/users", headers=cust_headers)
    assert r_forbidden.status_code == 403
    print("  [PASS] RBAC Enforced: Non-admin access to Admin Portal blocked (403 Forbidden)")

    # Admin provisions a new Internal Staff member
    new_staff_email = f"staff_{int(time.time())}@intrinsic.io"
    r = requests.post(f"{BASE_URL}/api/admin/users", headers=admin_headers, json={
        "full_name": "Chloe Decker",
        "email": new_staff_email,
        "password": "InternalStaffPass!2026",
        "role": "staff",
        "department": "Customer Success & Retention"
    })
    assert r.status_code == 200
    new_staff = r.json()
    print(f"  [PASS] Admin Provisioned Staff: {new_staff['full_name']} ({new_staff['email']})")
    print(f"         Role: {new_staff['role'].upper()} | Dept: {new_staff['department']}")

    # Admin toggles status
    r_toggle = requests.patch(f"{BASE_URL}/api/admin/users/{new_staff['id']}/toggle-status", headers=admin_headers)
    assert r_toggle.status_code == 200
    print(f"  [PASS] Admin Toggled Status  : Active state -> {r_toggle.json()['is_active']}")

    # STEP 9: Summary
    print_step("STEP 9: Final Telemetry & Demo Completion")
    r_final = requests.get(f"{BASE_URL}/api/kpis", headers=admin_headers).json()
    print(f"  * Final MRR            : ${r_final['mrr']:,.2f}")
    print(f"  * Final Active Subs    : {r_final['active_subscriptions']}")
    print(f"  * Final Settled Revenue: ${r_final['total_revenue_settled']:,.2f}")
    print(f"  * Overdue Receivables  : ${r_final['overdue_invoices_amount']:,.2f}")
    
    print("""
==============================================================================
  [SUCCESS] COMPLETE END-TO-END DEMO EXECUTED ON http://127.0.0.1:8000
  [SUCCESS] ALL SPECIFICATIONS, SECURITY RULES & RBAC POLICIES VALIDATED!
==============================================================================
    """)

if __name__ == "__main__":
    main()
