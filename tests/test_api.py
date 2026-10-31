import os
import sys

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.database import engine, Base, SessionLocal
from app.seed_data import seed_database

# Ensure database tables and seed data are created
Base.metadata.create_all(bind=engine)
db = SessionLocal()
seed_database(db)
db.close()

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_admin_login():
    response = client.post("/api/auth/login", json={
        "email": "admin@company.com",
        "password": "admin123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "admin"
    return data["access_token"]

def test_staff_login():
    response = client.post("/api/auth/login", json={
        "email": "staff@company.com",
        "password": "staff123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "staff"
    return data["access_token"]

def test_customer_login():
    response = client.post("/api/auth/login", json={
        "email": "john.doe@enterprise.com",
        "password": "customer123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "customer"
    return data["access_token"]

def test_get_plans():
    response = client.get("/api/plans")
    assert response.status_code == 200
    plans = response.json()
    assert len(plans) >= 4
    assert any(p["frequency"] == "monthly" for p in plans)

def test_dashboard_metrics():
    admin_token = test_admin_login()
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/dashboard/metrics", headers=headers)
    assert response.status_code == 200
    metrics = response.json()
    assert "mrr" in metrics
    assert metrics["mrr"] > 0
    assert "active_subscriptions_count" in metrics
    assert metrics["active_subscriptions_count"] >= 2
    assert "recent_revenue_logs" in metrics

def test_discount_validation():
    customer_token = test_customer_login()
    headers = {"Authorization": f"Bearer {customer_token}"}
    response = client.get("/api/discounts/validate/WELCOME20?amount=200", headers=headers)
    assert response.status_code == 200
    res = response.json()
    assert res["valid"] is True
    assert res["discount_amount"] == 40.0 # 20% of 200

def test_subscription_creation_and_lifecycle():
    customer_token = test_customer_login()
    headers = {"Authorization": f"Bearer {customer_token}"}

    # Get plans
    plans = client.get("/api/plans").json()
    monthly_plan = next(p for p in plans if p["frequency"] == "monthly")

    # Create subscription as Draft
    create_payload = {
        "plan_id": monthly_plan["id"],
        "quantity": 1,
        "discount_code": "WELCOME20",
        "status": "Draft"
    }
    res = client.post("/api/subscriptions", json=create_payload, headers=headers)
    assert res.status_code == 201
    sub = res.json()
    sub_id = sub["id"]
    assert sub["status"] == "Draft"
    assert sub["discount_id"] is not None

    # Customer transitions Draft -> Quotation
    res_quot = client.patch(f"/api/subscriptions/{sub_id}/status", json={"status": "Quotation"}, headers=headers)
    assert res_quot.status_code == 200
    assert res_quot.json()["status"] == "Quotation"

    # Staff transitions Quotation -> Confirmed
    staff_token = test_staff_login()
    staff_headers = {"Authorization": f"Bearer {staff_token}"}
    res_conf = client.patch(f"/api/subscriptions/{sub_id}/status", json={"status": "Confirmed"}, headers=staff_headers)
    assert res_conf.status_code == 200
    assert res_conf.json()["status"] == "Confirmed"

    # Staff transitions Confirmed -> Active (should auto-generate invoice!)
    res_act = client.patch(f"/api/subscriptions/{sub_id}/status", json={"status": "Active"}, headers=staff_headers)
    assert res_act.status_code == 200
    assert res_act.json()["status"] == "Active"

    # Verify invoice was generated
    invoices_res = client.get("/api/invoices", headers=headers)
    assert invoices_res.status_code == 200
    customer_invoices = invoices_res.json()
    sub_invoice = next((inv for inv in customer_invoices if inv["subscription_id"] == sub_id), None)
    assert sub_invoice is not None
    assert sub_invoice["status"] in ["Draft", "Confirmed"]

    # Pay the invoice
    inv_id = sub_invoice["id"]
    pay_payload = {
        "method": "credit_card",
        "amount": sub_invoice["total_amount"],
        "notes": "Automated test payment"
    }
    pay_res = client.post(f"/api/invoices/{inv_id}/pay", json=pay_payload, headers=headers)
    assert pay_res.status_code == 201

    # Verify invoice status is now Paid
    inv_check = client.get(f"/api/invoices/{inv_id}", headers=headers).json()
    assert inv_check["status"] == "Paid"
    assert len(inv_check["payments"]) >= 1

if __name__ == "__main__":
    print("Running backend tests...")
    test_health_check()
    test_admin_login()
    test_staff_login()
    test_customer_login()
    test_get_plans()
    test_dashboard_metrics()
    test_discount_validation()
    test_subscription_creation_and_lifecycle()
    print("All backend tests passed successfully!")
