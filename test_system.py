"""
Comprehensive Direct Test Suite for INTRINSIC - Odoo Makeathon Edition
Verifies all authentication, RBAC, strict password security, state machine transitions,
billing engine, and KPI calculations directly against database and routes.
"""

from backend.database import SessionLocal, Base, engine
from backend.seed import seed_database
from backend.models import User, Subscription, Invoice, ProductPlan
from backend.schemas import (
    UserRegister, UserLogin, UserCreateAdmin, 
    SubscriptionCreate, SubscriptionTransition, 
    InvoicePayRequest, DiscountRuleCreate
)
from backend.routes.auth import login, register
from backend.routes.admin import list_team_users, create_team_user, toggle_user_status
from backend.routes.subscriptions import (
    get_subscriptions, create_subscription, transition_subscription_status
)
from backend.routes.invoices import get_invoices, pay_invoice, void_invoice
from backend.routes.billing import run_billing_cycle
from backend.routes.kpis import get_kpis
from backend.security import validate_password_rules
from fastapi import HTTPException

def run_tests():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_database(db)

    print("\n" + "="*70)
    print(">>> STARTING INTRINSIC DIRECT SYSTEM TEST SUITE")
    print("="*70)

    # 1. Test Seeded Personas
    admin_user = db.query(User).filter(User.email == "admin@intrinsic.io").first()
    staff_user = db.query(User).filter(User.email == "staff@intrinsic.io").first()
    customer_user = db.query(User).filter(User.email == "customer@intrinsic.io").first()

    assert admin_user and admin_user.role == "admin"
    assert staff_user and staff_user.role == "staff"
    assert customer_user and customer_user.role == "customer"
    print("[PASS] 1. Demo personas successfully seeded (Admin, Staff, Customer).")

    # 2. Test Login for all personas
    for email in ["admin@intrinsic.io", "staff@intrinsic.io", "customer@intrinsic.io"]:
        token_resp = login(UserLogin(email=email, password="Intrinsic@2026!"), db)
        assert token_resp["access_token"]
        assert token_resp["user"].email == email
        print(f"[PASS] 2. Login successful for {token_resp['user'].role.upper()} ({email})")

    # 3. Test Strict Password Validation Rules
    invalid_cases = [
        ("Short1!", "more than 8 characters"),
        ("nouppercase1!", "uppercase letter"),
        ("NOLOWERCASE1!", "lowercase letter"),
        ("NoSpecialChar1", "special character")
    ]
    for pwd, rule in invalid_cases:
        caught = False
        try:
            validate_password_rules(pwd)
        except ValueError:
            caught = True
        assert caught, f"Failed to reject password missing {rule}: {pwd}"
        print(f"[PASS] 3. Strict password security rejected: Missing {rule}")

    # 4. Test Customer-Only Public Registration
    new_reg = register(UserRegister(
        full_name="Makeathon Tester",
        email="makeathontester@enterprise.com",
        password="ValidPassword#2026!",
        company_name="Makeathon Ventures",
        billing_address="100 Tech Blvd",
        phone="+1 555 4321"
    ), db)
    assert new_reg["user"].role == "customer", "Public registration must force customer role!"
    print(f"[PASS] 4. Public registration strictly created role: {new_reg['user'].role}")

    # 5. Test Admin Management Portal
    # Admin creates new Staff account
    new_staff = create_team_user(UserCreateAdmin(
        full_name="Operations Specialist",
        email="ops_spec@intrinsic.io",
        password="StaffPassword@2026!",
        role="staff",
        department="Billing Operations"
    ), current_admin=admin_user, db=db)
    assert new_staff.role == "staff"
    assert new_staff.department == "Billing Operations"
    print(f"[PASS] 5a. Admin provisioned new Staff account ({new_staff.email}).")

    # Admin toggles status
    toggled = toggle_user_status(new_staff.id, current_admin=admin_user, db=db)
    assert toggled.is_active is False
    toggled = toggle_user_status(new_staff.id, current_admin=admin_user, db=db)
    assert toggled.is_active is True
    print("[PASS] 5b. Admin toggled staff account status (active/inactive).")

    # 6. Test Subscription Lifecycle State Machine
    plan = db.query(ProductPlan).first()
    sub_resp = create_subscription(
        SubscriptionCreate(
            customer_id=customer_user.id,
            plan_id=plan.id,
            billing_interval="monthly",
            quantity=2,
            discount_code="WELCOME10",
            notes="Makeathon evaluation subscription"
        ),
        current_user=staff_user,
        db=db
    )
    sub_id = sub_resp["id"]
    assert sub_resp["status"] == "draft"
    print(f"[PASS] 6a. Created subscription in DRAFT status ({sub_resp['subscription_code']}).")

    # Draft -> Quotation
    trans = transition_subscription_status(
        sub_id,
        SubscriptionTransition(to_status="quotation", reason="Dispatched quote to customer"),
        current_user=staff_user,
        db=db
    )
    assert trans["status"] == "quotation"
    print("[PASS] 6b. Transitioned DRAFT -> QUOTATION.")

    # Quotation -> Confirmed (Customer approves)
    trans = transition_subscription_status(
        sub_id,
        SubscriptionTransition(to_status="confirmed", reason="Customer approved quotation online"),
        current_user=customer_user,
        db=db
    )
    assert trans["status"] == "confirmed"
    print("[PASS] 6c. Transitioned QUOTATION -> CONFIRMED by customer.")

    # Confirmed -> Active (Activates & auto-generates invoice)
    trans = transition_subscription_status(
        sub_id,
        SubscriptionTransition(to_status="active", reason="Subscription activated and billed"),
        current_user=staff_user,
        db=db
    )
    assert trans["status"] == "active"
    print("[PASS] 6d. Transitioned CONFIRMED -> ACTIVE (Auto-generated cycle invoice).")

    # Active -> Closed
    trans = transition_subscription_status(
        sub_id,
        SubscriptionTransition(to_status="closed", reason="Customer closed subscription"),
        current_user=customer_user,
        db=db
    )
    assert trans["status"] == "closed"
    print("[PASS] 6e. Transitioned ACTIVE -> CLOSED.")

    # Illegal transition: Closed -> Confirmed
    caught_illegal = False
    try:
        transition_subscription_status(
            sub_id,
            SubscriptionTransition(to_status="confirmed"),
            current_user=staff_user,
            db=db
        )
    except HTTPException as e:
        if e.status_code == 400:
            caught_illegal = True
    assert caught_illegal, "Illegal state transition should raise HTTP 400"
    print("[PASS] 6f. Illegal state machine transition rejected with HTTP 400.")

    # 7. Test Invoices & Settlement
    invs = get_invoices(customer_id=customer_user.id, current_user=customer_user, db=db)
    assert len(invs) > 0
    unpaid = next((i for i in invs if i["status"] in ["posted", "overdue"]), None)
    if unpaid:
        paid = pay_invoice(
            unpaid["id"],
            InvoicePayRequest(payment_method="credit_card"),
            current_user=customer_user,
            db=db
        )
        assert paid["status"] == "paid"
        assert paid["amount_paid"] > 0
        print(f"[PASS] 7. Settled invoice {paid['invoice_number']} via Credit Card.")

    # 8. Test Automated Billing Engine ("Run Billing Cycle")
    cycle_res = run_billing_cycle(current_user=staff_user, db=db)
    assert cycle_res["invoices_generated"] >= 1
    assert cycle_res["subscriptions_advanced"] >= 1
    print(f"[PASS] 8. Run Billing Cycle generated {cycle_res['invoices_generated']} invoices (${cycle_res['total_amount_billed']:,.2f}) & flagged {cycle_res['overdue_marked']} overdue.")

    # 9. Test Real-time KPIs
    kpis = get_kpis(current_user=admin_user, db=db)
    assert kpis["mrr"] > 0
    assert kpis["active_subscriptions"] > 0
    assert kpis["total_revenue_settled"] > 0
    print(f"[PASS] 9. KPIs verified: MRR=${kpis['mrr']:,.2f}, Active={kpis['active_subscriptions']}, Overdue Amount=${kpis['overdue_invoices_amount']:,.2f}, Total Settled=${kpis['total_revenue_settled']:,.2f}")

    db.close()
    print("="*70)
    print(">>> ALL TEST SUITES PASSED COMPLETELY AND FLAWLESSLY! <<<")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_tests()
