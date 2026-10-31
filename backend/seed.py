import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models import (
    User, CustomerProfile, ProductPlan, DiscountRule, 
    Subscription, SubscriptionAuditLog, Invoice, InvoiceLineItem
)
from backend.security import hash_password

def seed_database(db: Session):
    # Check if database is already seeded
    admin_exists = db.query(User).filter(User.email == "admin@intrinsic.io").first()
    if admin_exists:
        return

    print("[*] INTRINSIC Database Seeder: Initializing demo dataset...")

    # Default compliant password for all demo personas: "Intrinsic@2026!"
    # (Length: 15 > 8, Uppercase: I, Lowercase: ntrinsic, Number: 2026, Special: @ and !)
    default_hashed_pwd = hash_password("Intrinsic@2026!")

    # 1. Create Users
    admin_user = User(
        email="admin@intrinsic.io",
        hashed_password=default_hashed_pwd,
        full_name="Sarah Connor",
        role="admin",
        department="Executive & Architecture",
        is_active=True,
        created_at=datetime.utcnow() - timedelta(days=90)
    )
    staff_user = User(
        email="staff@intrinsic.io",
        hashed_password=default_hashed_pwd,
        full_name="Marcus Vance",
        role="staff",
        department="Billing Operations",
        is_active=True,
        created_at=datetime.utcnow() - timedelta(days=60)
    )
    staff_user_2 = User(
        email="devon@intrinsic.io",
        hashed_password=default_hashed_pwd,
        full_name="Devon Reed",
        role="staff",
        department="Customer Success",
        is_active=True,
        created_at=datetime.utcnow() - timedelta(days=45)
    )
    customer_user_1 = User(
        email="customer@intrinsic.io",
        hashed_password=default_hashed_pwd,
        full_name="Alex Mercer",
        role="customer",
        is_active=True,
        created_at=datetime.utcnow() - timedelta(days=50)
    )
    customer_user_2 = User(
        email="customer2@intrinsic.io",
        hashed_password=default_hashed_pwd,
        full_name="Elena Rostova",
        role="customer",
        is_active=True,
        created_at=datetime.utcnow() - timedelta(days=40)
    )

    db.add_all([admin_user, staff_user, staff_user_2, customer_user_1, customer_user_2])
    db.flush()

    # 2. Customer Profiles
    profile_1 = CustomerProfile(
        user_id=customer_user_1.id,
        company_name="Acme Enterprise Corp",
        tax_id="US-TAX-984210",
        billing_address="742 Evergreen Terrace, Suite 400, San Francisco, CA 94107",
        phone="+1 (555) 019-2834",
        currency="USD"
    )
    profile_2 = CustomerProfile(
        user_id=customer_user_2.id,
        company_name="Globex Dynamics Ltd",
        tax_id="GB-VAT-445892",
        billing_address="88 King William St, Bank Floor, London, EC4N 7TW",
        phone="+44 20 7946 0912",
        currency="USD"
    )
    db.add_all([profile_1, profile_2])

    # 3. Product Plans
    plan_starter = ProductPlan(
        name="Starter Growth Plan",
        code="PLAN-STARTER",
        description="Essential recurring billing & invoicing for rapid startup teams.",
        billing_interval="monthly",
        unit_price=49.00,
        setup_fee=0.0,
        features_json=json.dumps(["Up to 50 active subscriptions", "Automated email invoices", "Standard webhook sync"]),
        is_active=True
    )
    plan_pro = ProductPlan(
        name="Professional Suite",
        code="PLAN-PRO",
        description="Scalable subscription management with multi-currency & tax automation.",
        billing_interval="monthly",
        unit_price=149.00,
        setup_fee=50.0,
        features_json=json.dumps(["Unlimited subscriptions", "Real-time Odoo ledger export", "Custom discount engine", "Priority support"]),
        is_active=True
    )
    plan_enterprise = ProductPlan(
        name="Enterprise Cloud",
        code="PLAN-ENTERPRISE",
        description="High-throughput subscription orchestrator with automated dunning & RBAC audit.",
        billing_interval="monthly",
        unit_price=499.00,
        setup_fee=100.0,
        features_json=json.dumps(["Dedicated billing node", "Custom SLA & 24/7 hotline", "Odoo Makeathon VIP connector", "Full audit logging"]),
        is_active=True
    )
    plan_odoo_sync = ProductPlan(
        name="Custom Odoo ERP Sync",
        code="PLAN-ODOO-SYNC",
        description="Dedicated yearly sync bridge connecting INTRINSIC state machine to Odoo accounting.",
        billing_interval="annually",
        unit_price=1200.00,
        setup_fee=0.0,
        features_json=json.dumps(["Bi-directional invoice ledger", "Chart of accounts mapping", "Automated reconciliation"]),
        is_active=True
    )
    db.add_all([plan_starter, plan_pro, plan_enterprise, plan_odoo_sync])
    db.flush()

    # 4. Discount Rules
    rule_welcome = DiscountRule(
        code="WELCOME10",
        description="10% discount on new subscriptions for first 3 months",
        discount_type="percentage",
        value=10.0,
        min_spend=0.0,
        valid_from=datetime.utcnow() - timedelta(days=30),
        valid_until=datetime.utcnow() + timedelta(days=180),
        is_active=True,
        usage_count=4
    )
    rule_odoo = DiscountRule(
        code="ODOO_VIP",
        description="Special 20% discount for Odoo Makeathon submissions & partners",
        discount_type="percentage",
        value=20.0,
        min_spend=100.0,
        valid_from=datetime.utcnow() - timedelta(days=10),
        valid_until=datetime.utcnow() + timedelta(days=90),
        is_active=True,
        usage_count=2
    )
    rule_startup = DiscountRule(
        code="STARTUP50",
        description="$50 flat off on eligible enterprise contracts",
        discount_type="fixed",
        value=50.0,
        min_spend=200.0,
        valid_from=datetime.utcnow() - timedelta(days=15),
        valid_until=datetime.utcnow() + timedelta(days=60),
        is_active=True,
        usage_count=1
    )
    db.add_all([rule_welcome, rule_odoo, rule_startup])
    db.flush()

    # Helper calculation function
    def calc_totals(price, qty, discount_rule, tax_rate=10.0):
        subtotal = round(price * qty, 2)
        discount_amount = 0.0
        if discount_rule:
            if discount_rule.discount_type == "percentage":
                discount_amount = round(subtotal * (discount_rule.value / 100.0), 2)
            else:
                discount_amount = min(discount_rule.value, subtotal)
        taxable = max(0.0, subtotal - discount_amount)
        tax_amount = round(taxable * (tax_rate / 100.0), 2)
        total = round(taxable + tax_amount, 2)
        return subtotal, discount_amount, tax_amount, total

    # 5. Subscriptions (across all states: Draft, Quotation, Confirmed, Active, Closed)
    
    # Sub 1: Active Enterprise for Acme
    sub, disc, tax, tot = calc_totals(plan_enterprise.unit_price, 1, rule_odoo)
    sub_1 = Subscription(
        subscription_code="SUB-2026-001",
        customer_id=customer_user_1.id,
        plan_id=plan_enterprise.id,
        status="active",
        billing_interval="monthly",
        quantity=1,
        unit_price=plan_enterprise.unit_price,
        discount_rule_id=rule_odoo.id,
        discount_amount=disc,
        subtotal=sub,
        tax_rate=10.0,
        tax_amount=tax,
        total_amount=tot,
        start_date=datetime.utcnow() - timedelta(days=45),
        next_billing_date=datetime.utcnow() + timedelta(days=15),
        auto_renew=True,
        notes="Enterprise core infrastructure contract with Odoo Makeathon discount.",
        created_by_id=staff_user.id,
        created_at=datetime.utcnow() - timedelta(days=45)
    )

    # Sub 2: Active Pro for Globex
    sub, disc, tax, tot = calc_totals(plan_pro.unit_price, 1, rule_welcome)
    sub_2 = Subscription(
        subscription_code="SUB-2026-002",
        customer_id=customer_user_2.id,
        plan_id=plan_pro.id,
        status="active",
        billing_interval="monthly",
        quantity=1,
        unit_price=plan_pro.unit_price,
        discount_rule_id=rule_welcome.id,
        discount_amount=disc,
        subtotal=sub,
        tax_rate=10.0,
        tax_amount=tax,
        total_amount=tot,
        start_date=datetime.utcnow() - timedelta(days=32),
        next_billing_date=datetime.utcnow() + timedelta(days=3),
        auto_renew=True,
        notes="Professional tier recurring license.",
        created_by_id=staff_user.id,
        created_at=datetime.utcnow() - timedelta(days=32)
    )

    # Sub 3: Confirmed Odoo ERP Sync for Acme
    sub, disc, tax, tot = calc_totals(plan_odoo_sync.unit_price, 1, None)
    sub_3 = Subscription(
        subscription_code="SUB-2026-003",
        customer_id=customer_user_1.id,
        plan_id=plan_odoo_sync.id,
        status="confirmed",
        billing_interval="annually",
        quantity=1,
        unit_price=plan_odoo_sync.unit_price,
        discount_rule_id=None,
        discount_amount=0.0,
        subtotal=sub,
        tax_rate=10.0,
        tax_amount=tax,
        total_amount=tot,
        start_date=datetime.utcnow(),
        next_billing_date=datetime.utcnow() + timedelta(days=365),
        auto_renew=True,
        notes="Order confirmed by customer. Ready for billing cycle activation.",
        created_by_id=staff_user.id,
        created_at=datetime.utcnow() - timedelta(days=5)
    )

    # Sub 4: Quotation for Globex
    sub, disc, tax, tot = calc_totals(plan_starter.unit_price, 2, rule_welcome)
    sub_4 = Subscription(
        subscription_code="SUB-2026-004",
        customer_id=customer_user_2.id,
        plan_id=plan_starter.id,
        status="quotation",
        billing_interval="monthly",
        quantity=2,
        unit_price=plan_starter.unit_price,
        discount_rule_id=rule_welcome.id,
        discount_amount=disc,
        subtotal=sub,
        tax_rate=10.0,
        tax_amount=tax,
        total_amount=tot,
        start_date=datetime.utcnow(),
        next_billing_date=None,
        auto_renew=True,
        notes="Formal quotation sent to Globex finance team for approval.",
        created_by_id=staff_user.id,
        created_at=datetime.utcnow() - timedelta(days=3)
    )

    # Sub 5: Draft for Acme
    sub, disc, tax, tot = calc_totals(plan_pro.unit_price, 3, None)
    sub_5 = Subscription(
        subscription_code="SUB-2026-005",
        customer_id=customer_user_1.id,
        plan_id=plan_pro.id,
        status="draft",
        billing_interval="monthly",
        quantity=3,
        unit_price=plan_pro.unit_price,
        discount_rule_id=None,
        discount_amount=0.0,
        subtotal=sub,
        tax_rate=10.0,
        tax_amount=tax,
        total_amount=tot,
        start_date=datetime.utcnow(),
        next_billing_date=None,
        auto_renew=True,
        notes="Internal draft prepared for subsidiary rollout.",
        created_by_id=staff_user_2.id,
        created_at=datetime.utcnow() - timedelta(days=1)
    )

    # Sub 6: Closed previous contract for Globex
    sub, disc, tax, tot = calc_totals(plan_starter.unit_price, 1, None)
    sub_6 = Subscription(
        subscription_code="SUB-2026-006",
        customer_id=customer_user_2.id,
        plan_id=plan_starter.id,
        status="closed",
        billing_interval="monthly",
        quantity=1,
        unit_price=plan_starter.unit_price,
        discount_rule_id=None,
        discount_amount=0.0,
        subtotal=sub,
        tax_rate=10.0,
        tax_amount=tax,
        total_amount=tot,
        start_date=datetime.utcnow() - timedelta(days=120),
        next_billing_date=None,
        end_date=datetime.utcnow() - timedelta(days=35),
        auto_renew=False,
        notes="Closed following scheduled upgrade to Professional Suite.",
        created_by_id=admin_user.id,
        created_at=datetime.utcnow() - timedelta(days=120)
    )

    db.add_all([sub_1, sub_2, sub_3, sub_4, sub_5, sub_6])
    db.flush()

    # 6. Audit Trail for Subscriptions
    audit_entries = [
        SubscriptionAuditLog(subscription_id=sub_1.id, from_status="draft", to_status="quotation", changed_by_name="Marcus Vance", reason="Initial quotation drafted", created_at=datetime.utcnow() - timedelta(days=45)),
        SubscriptionAuditLog(subscription_id=sub_1.id, from_status="quotation", to_status="confirmed", changed_by_name="Alex Mercer", reason="Customer approved quotation online", created_at=datetime.utcnow() - timedelta(days=44)),
        SubscriptionAuditLog(subscription_id=sub_1.id, from_status="confirmed", to_status="active", changed_by_name="Marcus Vance", reason="Initial payment settled & subscription activated", created_at=datetime.utcnow() - timedelta(days=44)),
        
        SubscriptionAuditLog(subscription_id=sub_2.id, from_status="draft", to_status="quotation", changed_by_name="Marcus Vance", reason="Prepared proposal for Globex", created_at=datetime.utcnow() - timedelta(days=33)),
        SubscriptionAuditLog(subscription_id=sub_2.id, from_status="quotation", to_status="confirmed", changed_by_name="Elena Rostova", reason="Accepted proposal via customer portal", created_at=datetime.utcnow() - timedelta(days=32)),
        SubscriptionAuditLog(subscription_id=sub_2.id, from_status="confirmed", to_status="active", changed_by_name="Marcus Vance", reason="Activated after billing setup", created_at=datetime.utcnow() - timedelta(days=32)),

        SubscriptionAuditLog(subscription_id=sub_3.id, from_status="draft", to_status="quotation", changed_by_name="Marcus Vance", reason="Yearly ERP sync add-on drafted", created_at=datetime.utcnow() - timedelta(days=6)),
        SubscriptionAuditLog(subscription_id=sub_3.id, from_status="quotation", to_status="confirmed", changed_by_name="Alex Mercer", reason="Purchase order PO-992 signed", created_at=datetime.utcnow() - timedelta(days=5)),

        SubscriptionAuditLog(subscription_id=sub_4.id, from_status="draft", to_status="quotation", changed_by_name="Marcus Vance", reason="Dispatched quote to customer", created_at=datetime.utcnow() - timedelta(days=3)),

        SubscriptionAuditLog(subscription_id=sub_6.id, from_status="active", to_status="closed", changed_by_name="Sarah Connor", reason="Upgraded to Professional tier", created_at=datetime.utcnow() - timedelta(days=35)),
    ]
    db.add_all(audit_entries)

    # 7. Invoices (Paid, Posted, Overdue, Draft)
    
    # Inv 1: Paid invoice for Acme sub_1
    inv_1 = Invoice(
        invoice_number="INV-2026-1001",
        subscription_id=sub_1.id,
        customer_id=customer_user_1.id,
        issue_date=datetime.utcnow() - timedelta(days=44),
        due_date=datetime.utcnow() - timedelta(days=30),
        status="paid",
        subtotal=sub_1.subtotal,
        discount_amount=sub_1.discount_amount,
        tax_amount=sub_1.tax_amount,
        total_amount=sub_1.total_amount,
        amount_paid=sub_1.total_amount,
        payment_method="credit_card",
        paid_at=datetime.utcnow() - timedelta(days=44),
        notes="Automated cycle invoice #1 settled via corporate Visa card.",
        created_at=datetime.utcnow() - timedelta(days=44)
    )
    
    # Inv 2: Paid invoice for Globex sub_2
    inv_2 = Invoice(
        invoice_number="INV-2026-1002",
        subscription_id=sub_2.id,
        customer_id=customer_user_2.id,
        issue_date=datetime.utcnow() - timedelta(days=32),
        due_date=datetime.utcnow() - timedelta(days=18),
        status="paid",
        subtotal=sub_2.subtotal,
        discount_amount=sub_2.discount_amount,
        tax_amount=sub_2.tax_amount,
        total_amount=sub_2.total_amount,
        amount_paid=sub_2.total_amount,
        payment_method="bank_transfer",
        paid_at=datetime.utcnow() - timedelta(days=31),
        notes="Wire transfer ACH ref #WT-88401 settled.",
        created_at=datetime.utcnow() - timedelta(days=32)
    )

    # Inv 3: Posted (Unpaid, due soon) for Acme sub_1
    inv_3 = Invoice(
        invoice_number="INV-2026-1003",
        subscription_id=sub_1.id,
        customer_id=customer_user_1.id,
        issue_date=datetime.utcnow() - timedelta(days=14),
        due_date=datetime.utcnow() + timedelta(days=16),
        status="posted",
        subtotal=sub_1.subtotal,
        discount_amount=sub_1.discount_amount,
        tax_amount=sub_1.tax_amount,
        total_amount=sub_1.total_amount,
        amount_paid=0.0,
        notes="Current billing cycle statement dispatched.",
        created_at=datetime.utcnow() - timedelta(days=14)
    )

    # Inv 4: Overdue Invoice for Globex (due 10 days ago!)
    inv_4 = Invoice(
        invoice_number="INV-2026-1004",
        subscription_id=sub_2.id,
        customer_id=customer_user_2.id,
        issue_date=datetime.utcnow() - timedelta(days=25),
        due_date=datetime.utcnow() - timedelta(days=10),
        status="overdue",
        subtotal=sub_2.subtotal,
        discount_amount=sub_2.discount_amount,
        tax_amount=sub_2.tax_amount,
        total_amount=sub_2.total_amount,
        amount_paid=0.0,
        notes="Second notice dispatched. Overdue by 10 calendar days.",
        created_at=datetime.utcnow() - timedelta(days=25)
    )

    # Inv 5: Draft Invoice for sub_3 (confirmed order)
    inv_5 = Invoice(
        invoice_number="INV-2026-1005",
        subscription_id=sub_3.id,
        customer_id=customer_user_1.id,
        issue_date=datetime.utcnow() - timedelta(days=2),
        due_date=datetime.utcnow() + timedelta(days=28),
        status="draft",
        subtotal=sub_3.subtotal,
        discount_amount=sub_3.discount_amount,
        tax_amount=sub_3.tax_amount,
        total_amount=sub_3.total_amount,
        amount_paid=0.0,
        notes="Draft invoice pending customer payment authorization.",
        created_at=datetime.utcnow() - timedelta(days=2)
    )

    db.add_all([inv_1, inv_2, inv_3, inv_4, inv_5])
    db.flush()

    # 8. Line items for invoices
    line_items = [
        InvoiceLineItem(invoice_id=inv_1.id, description="Enterprise Cloud License (1 month)", quantity=1, unit_price=499.0, total_price=499.0),
        InvoiceLineItem(invoice_id=inv_2.id, description="Professional Suite License (1 month)", quantity=1, unit_price=149.0, total_price=149.0),
        InvoiceLineItem(invoice_id=inv_3.id, description="Enterprise Cloud License (Monthly Renewal)", quantity=1, unit_price=499.0, total_price=499.0),
        InvoiceLineItem(invoice_id=inv_4.id, description="Professional Suite License (Monthly Service)", quantity=1, unit_price=149.0, total_price=149.0),
        InvoiceLineItem(invoice_id=inv_5.id, description="Custom Odoo ERP Sync (Annual Bridge)", quantity=1, unit_price=1200.0, total_price=1200.0),
    ]
    db.add_all(line_items)

    db.commit()
    print("[+] INTRINSIC Database Seeder: Successfully seeded realistic personas, plans, subscriptions, and invoices.")
