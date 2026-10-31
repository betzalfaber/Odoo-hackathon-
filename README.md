# INTRINSIC — Subscription & Invoicing Operating System
### Built for Odoo Makeathon Submission

**INTRINSIC** is a production-grade, full-stack subscription and invoicing management system built using **Python FastAPI**, **SQLAlchemy ORM**, **SQLite**, **Tailwind CSS**, and **Alpine.js**.

---

## 🌟 Key Features & Architectural Compliance

### 1. 🏷️ Application Branding & Identity
- Rebranded completely to **INTRINSIC** across all headers, page titles, branding badges, documentation, and metadata.
- Minimalist, high-contrast, modern enterprise SaaS aesthetic.

### 2. 🔐 Mandatory Initial Auth & Landing Flow
- **Direct Auth Boot:** On launch, the application boots directly into a full-screen Authentication view (Sign In / Register).
- **Core Shielding:** The dashboard, navigation, tables, and settings remain completely hidden until authentication succeeds.
- **Instant Persona Evaluation:** Quick 1-click evaluation buttons on the sign-in screen allowing Makeathon judges to test each persona immediately:
  - 👑 **Administrator**: `admin@intrinsic.io` / `Intrinsic@2026!`
  - 💼 **Internal Staff**: `staff@intrinsic.io` / `Intrinsic@2026!`
  - 👤 **Customer Portal**: `customer@intrinsic.io` / `Intrinsic@2026!`
- **Sign Out:** Prominent header button that clears the session token and redirects back to the full-screen auth landing view.
- **Button Styling Rule:** Vector/icon SVG symbols are removed from dashboard buttons (e.g., text-only buttons like **Run Billing Cycle**, **Create Subscription**, etc.).

### 3. 🛡️ Strict Password Security & Validation Rules
Enforced both on the **Backend** (Pydantic schema validators) and on the **Frontend** (real-time Alpine.js rule checklist):
- ✅ Must have **more than 8 characters** (at least 9 characters).
- ✅ Must contain at least **one uppercase letter** (`A-Z`).
- ✅ Must contain at least **one lowercase letter** (`a-z`).
- ✅ Must contain at least **one special character** (`!@#$%^&*...`).
- Visual inline feedback and notification banners for validation or auth errors.

### 4. 👥 Customer-Only Public Registration & Admin Staff Management
- **Public Registration:** Exclusively registers users with the `customer` role. No role selector is exposed on public forms.
- **Admin Management Portal:** An administrative management section and modal inside the Admin dashboard allows logged-in Administrators to create, view, assign departments to, and toggle active status for **Internal Staff** and **Admin** accounts.

### 5. 🌗 Seamless Dark & Bright Theme Switcher
- High-contrast Dark and Bright theme toggle available on **both** the initial login screen and the main application header.
- Persistent across page reloads via `localStorage`.

### 6. 📐 Full Screen Utilization & Fluid Layout
- Eliminates restricted container widths. Fluid edge-to-edge layout (`w-full min-h-screen px-4 sm:px-6 lg:px-8`).
- Multi-column flexible grids for KPI metrics and full-width data tables.

### 7. 📱 Mobile & Desktop Cross-Platform Responsiveness
- **Desktop:** Persistent header navigation, wide multi-column KPI cards, full data tables with status pills and actions.
- **Mobile:** Collapsible mobile navigation menu, stacked cards, touch-friendly buttons, and horizontal table scrolling.

### 8. ⚙️ Core Business Logic & State Machine
- **Role-Based Access Control (RBAC):** Admin (full control), Internal Staff (operational billing & quotes), and Customer Portal (self-service billing & payments).
- **Subscription Lifecycle State Machine:**
  $$\text{Draft} \longrightarrow \text{Quotation} \longrightarrow \text{Confirmed} \longrightarrow \text{Active} \longrightarrow \text{Closed}$$
  - Full audit trail logging actors and transition timestamps.
  - Automatic invoice generation upon transitioning to `Active`.
- **Automated Billing Engine ("Run Billing Cycle"):**
  - Scans active subscriptions, generates recurring cycle invoices, advances next billing dates, and automatically flags past-due unpaid invoices as `overdue`.
- **Discount Rule Manager:** Tiered percentage and fixed-amount promotional rules with minimum spend thresholds.
- **Real-Time KPIs:** Live calculation of **MRR** (Monthly Recurring Revenue), **Active Subscriptions**, **Overdue Receivables**, and **Total Settled Revenue**.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+ installed
- Dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `bcrypt`, `python-jose`, `python-multipart`.

### Running the Application
From the project root directory, run:
```bash
python run.py
```
*(Or if using the specific Python installation path:)*
```powershell
& "C:\Users\USER\AppData\Local\Programs\Python\Python311\python.exe" run.py
```

1. The server will start at `http://localhost:8000`.
2. Your default web browser will open automatically.
3. Interactive API documentation is available at `http://localhost:8000/docs`.

---

## 🔑 Demo Personas for Judges

| Persona | Email | Password | Capabilities |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@intrinsic.io` | `Intrinsic@2026!` | Full system access, Staff provisioning, Billing cycles, Global KPIs |
| **Internal Staff** | `staff@intrinsic.io` | `Intrinsic@2026!` | Manage subscriptions, Send quotations, Run billing cycles, Void invoices |
| **Customer Portal** | `customer@intrinsic.io` | `Intrinsic@2026!` | Approve quotations, Pay invoices, View payment receipts |
| **Secondary Customer** | `customer2@intrinsic.io` | `Intrinsic@2026!` | Globex Dynamics account with overdue invoice test case |

---

## 📂 Project Directory Structure

```
Dot E/
├── backend/
│   ├── __init__.py
│   ├── database.py         # SQLAlchemy SQLite configuration & WAL mode
│   ├── models.py           # User, Subscription, Invoice, ProductPlan, DiscountRule models
│   ├── schemas.py          # Pydantic schemas with strict password validation
│   ├── security.py         # JWT auth, bcrypt hashing, password rule validators
│   ├── seed.py             # Automatic startup seeder with realistic demo data
│   └── routes/
│       ├── auth.py         # Sign in, public customer registration, /me
│       ├── admin.py        # Staff & admin account provisioning
│       ├── subscriptions.py# Lifecycle state machine & audit logs
│       ├── invoices.py     # Invoice ledger & settlement
│       ├── billing.py      # Automated "Run Billing Cycle" engine
│       ├── kpis.py         # Real-time MRR, active, overdue, and settled metrics
│       └── plans.py        # Plans and discount rules API
├── static/
│   ├── vendor/
│   │   ├── alpine.min.js   # Local Alpine.js for offline speed
│   │   └── tailwindcss.js  # Local Tailwind CSS engine
│   ├── js/
│   │   └── app.js          # Alpine.js reactive application logic
│   └── index.html          # Full-screen auth & responsive single-page dashboard
├── intrinsic.db            # Local SQLite database
├── run.py                  # 1-click startup runner
└── requirements.txt        # Backend dependencies
```
