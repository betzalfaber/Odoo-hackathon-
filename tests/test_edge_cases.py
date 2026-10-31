import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_performance_and_latency():
    """Verify endpoint latency is well under 2 seconds (< 200ms)."""
    start_time = time.time()
    res = client.get("/api/plans")
    elapsed = time.time() - start_time
    assert res.status_code == 200
    assert elapsed < 2.0, f"Plans API took {elapsed:.2f}s, expected < 2s"

    start_time = time.time()
    res = client.get("/")
    elapsed = time.time() - start_time
    assert res.status_code == 200
    assert elapsed < 2.0, f"HTML index page load took {elapsed:.2f}s, expected < 2s"

def test_rbac_enforcement():
    """Verify customer cannot call admin endpoints."""
    # Customer login
    res_login = client.post("/api/auth/login", json={
        "email": "john.doe@enterprise.com",
        "password": "customer123"
    })
    customer_token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {customer_token}"}

    # Attempt to create plan as customer
    plan_payload = {
        "name": "Hacker Plan",
        "frequency": "monthly",
        "min_quantity": 1,
        "price": 0.01
    }
    res = client.post("/api/plans", json=plan_payload, headers=headers)
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"

    # Attempt to create discount as customer
    disc_payload = {
        "code": "FREE100",
        "type": "percentage",
        "value": 100.0,
        "min_purchase": 0,
        "usage_limit": 10
    }
    res = client.post("/api/discounts", json=disc_payload, headers=headers)
    assert res.status_code == 403

def test_discount_edge_cases():
    """Test min_purchase thresholds and expired discount validations."""
    admin_login = client.post("/api/auth/login", json={"email": "admin@company.com", "password": "admin123"})
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create discount with high min_purchase
    disc_payload = {
        "code": "VIP1000",
        "type": "fixed",
        "value": 100.0,
        "min_purchase": 1000.0,
        "usage_limit": 5
    }
    res = client.post("/api/discounts", json=disc_payload, headers=admin_headers)
    assert res.status_code in [201, 400] # 400 if already created

    # Validate with insufficient amount (e.g. 500)
    customer_login = client.post("/api/auth/login", json={"email": "john.doe@enterprise.com", "password": "customer123"})
    cust_token = customer_login.json()["access_token"]
    cust_headers = {"Authorization": f"Bearer {cust_token}"}

    val_res = client.get("/api/discounts/validate/VIP1000?amount=500", headers=cust_headers).json()
    assert val_res["valid"] is False
    assert "minimum purchase" in val_res["reason"].lower()

    # Validate with sufficient amount (e.g. 1500)
    val_res_ok = client.get("/api/discounts/validate/VIP1000?amount=1500", headers=cust_headers).json()
    assert val_res_ok["valid"] is True
    assert val_res_ok["discount_amount"] == 100.0

def test_plan_minimum_quantity_enforcement():
    """Test that ordering less than min_quantity is rejected."""
    cust_login = client.post("/api/auth/login", json={"email": "sarah.connor@cyberdyne.io", "password": "customer123"})
    cust_token = cust_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {cust_token}"}

    plans = client.get("/api/plans").json()
    growth_plan = next(p for p in plans if p["frequency"] == "weekly")
    assert growth_plan["min_quantity"] >= 2

    # Attempt to subscribe with quantity 1
    sub_payload = {
        "plan_id": growth_plan["id"],
        "quantity": 1,
        "status": "Draft"
    }
    res = client.post("/api/subscriptions", json=sub_payload, headers=headers)
    assert res.status_code == 400
    assert "Minimum quantity" in res.json()["detail"]

def test_prevent_double_payment_on_paid_invoice():
    """Verify that paying an already Paid invoice is rejected."""
    admin_login = client.post("/api/auth/login", json={"email": "admin@company.com", "password": "admin123"})
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    invoices = client.get("/api/invoices", headers=headers).json()
    paid_inv = next((i for i in invoices if i["status"] == "Paid"), None)
    assert paid_inv is not None

    pay_payload = {
        "method": "credit_card",
        "amount": 50.0,
        "notes": "Attempt duplicate payment"
    }
    res = client.post(f"/api/invoices/{paid_inv['id']}/pay", json=pay_payload, headers=headers)
    assert res.status_code == 400
    assert "already been fully paid" in res.json()["detail"]

def test_user_friendly_validation_errors():
    """Verify that 422 RequestValidationErrors are formatted cleanly instead of raw JSON trees."""
    # Attempt registration with empty fields and short password
    invalid_reg = {
        "name": "",
        "email": "not-an-email",
        "password": "123"
    }
    res = client.post("/api/auth/register", json=invalid_reg)
    assert res.status_code == 422
    data = res.json()
    assert data.get("user_friendly") is True
    assert isinstance(data.get("detail"), str)
    assert "Name" in data["detail"] or "Email" in data["detail"] or "Password" in data["detail"]

if __name__ == "__main__":
    print("Executing edge-case test suite...")
    test_api_performance_and_latency()
    test_rbac_enforcement()
    test_discount_edge_cases()
    test_plan_minimum_quantity_enforcement()
    test_prevent_double_payment_on_paid_invoice()
    test_user_friendly_validation_errors()
    print("All edge-case, latency, and error-formatting tests passed successfully!")
