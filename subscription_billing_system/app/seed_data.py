from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import User, Product, Plan, Discount, Subscription, Invoice, Payment
from app.auth import hash_password

def seed_database(db: Session):
    """Seed initial demo data if database is empty."""
    if db.query(User).first() is not None:
        return # Database already seeded

    now = datetime.now(timezone.utc)

    # 1. Users & Roles
    admin = User(
        name="Alex Morgan",
        email="admin@company.com",
        password_hash=hash_password("admin123"),
        role="admin"
    )
    staff = User(
        name="Taylor Swift",
        email="staff@company.com",
        password_hash=hash_password("staff123"),
        role="staff"
    )
    customer1 = User(
        name="John Doe",
        email="john.doe@enterprise.com",
        password_hash=hash_password("customer123"),
        role="customer"
    )
    customer2 = User(
        name="Sarah Connor",
        email="sarah.connor@cyberdyne.io",
        password_hash=hash_password("customer123"),
        role="customer"
    )

    db.add_all([admin, staff, customer1, customer2])
    db.flush()

    # 2. Products & Variants
    p1 = Product(
        name="Cloud Compute Cluster",
        type="compute",
        sales_price=150.0,
        cost_price=60.0,
        variant_attribute="16 vCPU / 64GB RAM",
        price_modifier=50.0
    )
    p2 = Product(
        name="SaaS Analytics Pro",
        type="software",
        sales_price=99.0,
        cost_price=15.0,
        variant_attribute="Enterprise Tier",
        price_modifier=30.0
    )
    p3 = Product(
        name="Secure Storage Vault",
        type="storage",
        sales_price=49.0,
        cost_price=10.0,
        variant_attribute="5 TB NVMe",
        price_modifier=20.0
    )
    db.add_all([p1, p2, p3])
    db.flush()

    # 3. Plans
    plan_monthly = Plan(
        name="Enterprise Monthly",
        frequency="monthly",
        min_quantity=1,
        status_rules="Auto-renew monthly on 1st. 14-day grace period for invoice payment.",
        price=199.0
    )
    plan_weekly = Plan(
        name="Growth Weekly",
        frequency="weekly",
        min_quantity=2,
        status_rules="Auto-renew weekly on Mondays. Immediate suspension upon payment default.",
        price=59.0
    )
    plan_daily = Plan(
        name="Startup Daily",
        frequency="daily",
        min_quantity=1,
        status_rules="Daily billing cycle. High frequency on-demand provisioning.",
        price=12.0
    )
    plan_yearly = Plan(
        name="Annual Unlimited",
        frequency="yearly",
        min_quantity=1,
        status_rules="Annual prepaid term with inclusive premium SLA.",
        price=1899.0
    )
    db.add_all([plan_monthly, plan_weekly, plan_daily, plan_yearly])
    db.flush()

    # 4. Discounts
    d1 = Discount(
        code="WELCOME20",
        type="percentage",
        value=20.0,
        min_purchase=50.0,
        usage_limit=50,
        times_used=2,
        expiry_date=now + timedelta(days=90),
        is_active=True
    )
    d2 = Discount(
        code="STARTUP50",
        type="fixed",
        value=50.0,
        min_purchase=100.0,
        usage_limit=25,
        times_used=1,
        expiry_date=now + timedelta(days=60),
        is_active=True
    )
    d3 = Discount(
        code="ANNUALDEAL",
        type="percentage",
        value=15.0,
        min_purchase=500.0,
        usage_limit=100,
        times_used=0,
        expiry_date=now + timedelta(days=180),
        is_active=True
    )
    db.add_all([d1, d2, d3])
    db.flush()

    # 5. Subscriptions across various lifecycle stages
    # Sub 1: Active Monthly for John Doe
    sub1 = Subscription(
        sub_number="SUB-2026-0001",
        customer_id=customer1.id,
        plan_id=plan_monthly.id,
        discount_id=d1.id,
        quantity=2,
        start_date=now - timedelta(days=45),
        expiry_date=now + timedelta(days=15),
        status="Active"
    )
    # Sub 2: Active Weekly for Sarah Connor
    sub2 = Subscription(
        sub_number="SUB-2026-0002",
        customer_id=customer2.id,
        plan_id=plan_weekly.id,
        discount_id=None,
        quantity=3,
        start_date=now - timedelta(days=20),
        expiry_date=now + timedelta(days=8),
        status="Active"
    )
    # Sub 3: Confirmed for John Doe
    sub3 = Subscription(
        sub_number="SUB-2026-0003",
        customer_id=customer1.id,
        plan_id=plan_yearly.id,
        discount_id=d2.id,
        quantity=1,
        start_date=now - timedelta(days=5),
        expiry_date=now + timedelta(days=360),
        status="Confirmed"
    )
    # Sub 4: Quotation for Sarah Connor
    sub4 = Subscription(
        sub_number="SUB-2026-0004",
        customer_id=customer2.id,
        plan_id=plan_monthly.id,
        discount_id=None,
        quantity=1,
        start_date=now,
        expiry_date=now + timedelta(days=30),
        status="Quotation"
    )
    # Sub 5: Draft for John Doe
    sub5 = Subscription(
        sub_number="SUB-2026-0005",
        customer_id=customer1.id,
        plan_id=plan_daily.id,
        discount_id=None,
        quantity=1,
        start_date=now,
        expiry_date=now + timedelta(days=1),
        status="Draft"
    )

    db.add_all([sub1, sub2, sub3, sub4, sub5])
    db.flush()

    # 6. Invoices
    # Invoice 1: Paid invoice for Sub 1
    inv1_subtotal = 199.0 * 2 # 398.0
    inv1_disc = 398.0 * 0.20 # 79.60
    inv1_tax = round((398.0 - inv1_disc) * 0.10, 2) # 31.84
    inv1_tot = round(398.0 - inv1_disc + inv1_tax, 2) # 350.24

    inv1 = Invoice(
        invoice_number="INV-2026-0001",
        subscription_id=sub1.id,
        issue_date=now - timedelta(days=45),
        due_date=now - timedelta(days=31),
        status="Paid",
        subtotal=inv1_subtotal,
        taxes=inv1_tax,
        discount_amount=inv1_disc,
        total_amount=inv1_tot
    )

    # Invoice 2: Confirmed (Outstanding) invoice for Sub 1 current month
    inv2 = Invoice(
        invoice_number="INV-2026-0002",
        subscription_id=sub1.id,
        issue_date=now - timedelta(days=15),
        due_date=now - timedelta(days=1),
        status="Confirmed",
        subtotal=inv1_subtotal,
        taxes=inv1_tax,
        discount_amount=inv1_disc,
        total_amount=inv1_tot
    )

    # Invoice 3: Paid invoice for Sub 2
    inv3_subtotal = 59.0 * 3 # 177.0
    inv3_tax = round(177.0 * 0.10, 2) # 17.70
    inv3_tot = round(177.0 + inv3_tax, 2) # 194.70

    inv3 = Invoice(
        invoice_number="INV-2026-0003",
        subscription_id=sub2.id,
        issue_date=now - timedelta(days=14),
        due_date=now,
        status="Paid",
        subtotal=inv3_subtotal,
        taxes=inv3_tax,
        discount_amount=0.0,
        total_amount=inv3_tot
    )

    db.add_all([inv1, inv2, inv3])
    db.flush()

    # 7. Payments
    pay1 = Payment(
        payment_number="PAY-2026-0001",
        invoice_id=inv1.id,
        method="credit_card",
        amount=inv1_tot,
        date=now - timedelta(days=44),
        notes="Credit card payment settled via Stripe"
    )
    pay2 = Payment(
        payment_number="PAY-2026-0002",
        invoice_id=inv3.id,
        method="bank_transfer",
        amount=inv3_tot,
        date=now - timedelta(days=12),
        notes="Wire transfer ACH ref #99281"
    )

    db.add_all([pay1, pay2])
    db.commit()
