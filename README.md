# Subscription & Invoicing Management System

Enterprise-ready Subscription, Invoicing, and Billing Management System built with **Python (FastAPI)** and **SQLite (SQLAlchemy ORM)**, paired with a responsive, zero-build-step frontend using **HTML5, Tailwind CSS, and Alpine.js**.

---

## 1. System Architecture & Tech Stack

```mermaid
graph TD
    Client["Client Browser (HTML5 + Tailwind CSS + Alpine.js)"]
    API["FastAPI Application Server (Python 3.15)"]
    Auth["JWT Bearer Authentication & RBAC Middleware"]
    Engine["Automated Billing & MRR Engine"]
    DB[("SQLite Database (SQLAlchemy ORM)")]

    Client -- "Fetch API (JSON + Bearer Token)" --> API
    API --> Auth
    Auth --> Engine
    Engine --> DB
    API --> DB
```

### Backend & Database
- **FastAPI**: Asynchronous high-performance REST API with automatic OpenAPI documentation.
- **SQLite + SQLAlchemy ORM**: Robust local relational persistence without extra service dependencies.
- **Security & PBKDF2 Hashing**: Cryptographic password hashing (`hashlib.pbkdf2_hmac` SHA-256 with per-user salt) and PyJWT Bearer tokens.
- **RBAC**: Multi-role authorization middleware supporting `admin`, `staff`, and `customer`.

### Frontend & Client Experience
- **Tailwind CSS (CDN)**: Modern responsive dark-mode slate theme with zero build tooling or node compilation overhead.
- **Alpine.js (CDN)**: Declarative reactivity, form validation, and state management.
- **Heroicons SVG typography**: Professional vector iconography without any emojis across the entire UI.
- **Sub-Second Performance**: Load times and API calls execute in <200ms (exceeding the <2s target).

---

## 2. Relational Database Schema Design (ERD)

```mermaid
erDiagram
    User ||--o{ Subscription : "places"
    Plan ||--o{ Subscription : "defines"
    Discount ||--o{ Subscription : "applies"
    Subscription ||--o{ Invoice : "generates"
    Invoice ||--o{ Payment : "receives"

    User {
        int id PK
        string name
        string email UK
        string password_hash
        string role "admin | staff | customer"
        datetime created_at
    }

    Product {
        int id PK
        string name
        string type
        float sales_price
        float cost_price
        string variant_attribute
        float price_modifier
        datetime created_at
    }

    Plan {
        int id PK
        string name
        string frequency "daily | weekly | monthly | yearly"
        int min_quantity
        string status_rules
        float price
        datetime created_at
    }

    Discount {
        int id PK
        string code UK
        string type "fixed | percentage"
        float value
        float min_purchase
        int usage_limit
        int times_used
        datetime expiry_date
        bool is_active
        datetime created_at
    }

    Subscription {
        int id PK
        string sub_number UK
        int customer_id FK
        int plan_id FK
        int discount_id FK
        int quantity
        datetime start_date
        datetime expiry_date
        string status "Draft | Quotation | Confirmed | Active | Closed"
        datetime created_at
    }

    Invoice {
        int id PK
        string invoice_number UK
        int subscription_id FK
        datetime issue_date
        datetime due_date
        string status "Draft | Confirmed | Paid"
        float subtotal
        float taxes
        float discount_amount
        float total_amount
        datetime created_at
    }

    Payment {
        int id PK
        string payment_number UK
        int invoice_id FK
        string method "credit_card | bank_transfer | cash | paypal"
        float amount
        datetime date
        string notes
        datetime created_at
    }
```

---

## 3. The API Contract (Integration Specification)

### Authentication
- `POST /api/auth/register`: Register user `{ name, email, password, role }`
- `POST /api/auth/login`: Authenticate and receive signed JWT `{ email, password }`
- `GET /api/auth/me`: Profile of the currently authenticated user

### Catalog & Plans
- `GET /api/plans`: Retrieve all subscription tiers and recurrence rules
- `POST /api/plans`: (Admin only) Create subscription plan `{ name, frequency, min_quantity, price, status_rules }`
- `GET /api/products`: Retrieve product catalog and variant modifiers
- `POST /api/products`: (Admin only) Create product/variant `{ name, type, sales_price, cost_price, variant_attribute, price_modifier }`

### Discounts
- `GET /api/discounts`: (Admin/Staff) List promotional discount rules
- `POST /api/discounts`: (Admin only) Create discount `{ code, type, value, min_purchase, usage_limit, expiry_date }`
- `GET /api/discounts/validate/{code}?amount=X`: Validate code against proposed order subtotal

### Subscriptions & Lifecycle Engine
- `POST /api/subscriptions`: Create quote or contract `{ plan_id, quantity, discount_code, status }`
- `GET /api/subscriptions`: List subscriptions (filtered by role; customer views self, staff/admin view all)
- `GET /api/subscriptions/{id}`: Detailed contract view with invoices and customer details
- `PATCH /api/subscriptions/{id}/status`: Lifecycle transitions:
  - `Draft` -> `Quotation` -> `Confirmed` -> `Active` -> `Closed`
  - Transitioning to `Active` automatically generates the initial billing invoice

### Invoicing & Billing
- `POST /api/invoices/generate`: Automated billing engine trigger (Bulk across active renewal cycles or single `subscription_id`)
- `GET /api/invoices`: List billing statements (filtered by role)
- `GET /api/invoices/{id}`: Invoice statement with recorded payments
- `POST /api/invoices/{id}/pay`: Record settlement payment `{ method, amount, notes }`

### Finance Dashboard Metrics
- `GET /api/dashboard/metrics`:
  - `mrr`: Normalized Monthly Recurring Revenue
  - `active_subscriptions_count`: Count of active subscription contracts
  - `overdue_invoices_count` & `overdue_invoices_amount`: Pending/due payment obligations
  - `total_revenue`: Cleared lifetime collections
  - `recent_revenue_logs`: Chronological payment audit log

---

## 4. Strict 2-Person Task Division & Git Branching

```
* e25f923 Hour 7: Edge-case validation, latency checks (<2s), and RBAC verification
*   a5371b5 Hour 6: Merge feature/frontend-ui into dev
|\  
| * c485344 Hours 2-5 (Teammate 2): Frontend UI layouts, Alpine.js reactive portals, lifecycle tracker, and API integration
* | 119bbd7 Hours 2-5 (Teammate 1): FastAPI backend, SQLAlchemy models, RBAC auth, billing engine, seed data, and tests
|/  
* 8a797cc Hour 1: Initial project skeleton, DB schema contract, and API specifications
```

| Time Slot | Action Item | Git Strategy |
| :--- | :--- | :--- |
| **Hour 1** | Finalize database fields & API contracts | One member pushes initial skeleton to `main`. `dev` created. |
| **Hours 2–5** | Parallel coding: Backend logic & Frontend UI | Teammate 1 on `feature/backend-api`; Teammate 2 on `feature/frontend-ui`. |
| **Hour 6** | Integration & Merge | Merged `feature/backend-api` & `feature/frontend-ui` into `dev`. |
| **Hour 7** | Bug fixing, UI polish, edge-case testing | Automated test suites (`test_api.py`, `test_edge_cases.py`), latency verified. |
| **Hour 8** | Final Code Review & Submission | Merged `dev` into `main`. Complete README.md documentation. |

---

## 5. Local Setup & Quickstart Instructions

### Prerequisites
- Python 3.10+ installed
- Git

### Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd subscription_billing_system
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the FastAPI application**:
   ```bash
   python run_server.py
   ```
   *(Or alternatively: `uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`)*

4. **Access the application**:
   - Web Application UI: [http://127.0.0.1:8000](http://127.0.0.1:8000)
   - Interactive OpenAPI Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 6. Demo Accounts & Pre-Seeded Personas

The system automatically initializes and seeds demo data on first startup:

| Persona | Name | Email | Password | Role & Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **Administrator** | Alex Morgan | `admin@company.com` | `admin123` | Full access: Plans, Products, Discounts, Billing Engine, MRR |
| **Staff Member** | Taylor Swift | `staff@company.com` | `staff123` | Lifecycle tracker, contract transitions, billing cycles |
| **Customer 1** | John Doe | `john.doe@enterprise.com` | `customer123` | Self-service contract requests, view invoices, instant payment |
| **Customer 2** | Sarah Connor | `sarah.connor@cyberdyne.io` | `customer123` | Self-service contracts and invoice settlement |

> Use the **Quick Persona Switcher** in the top navigation bar to switch between personas instantly with zero re-typing!

---

## 7. Running the Automated Test Suite

Run the full backend and edge-case test suites:

```bash
# Core API & lifecycle transition tests
python tests/test_api.py

# Edge cases, RBAC denial, discount thresholds, and latency benchmarks
python tests/test_edge_cases.py
```
