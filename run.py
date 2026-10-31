"""
INTRINSIC - Production-Ready Subscription & Invoicing Operating System
Odoo Makeathon Submission
"""

import sys
import os
import webbrowser
import uvicorn

# Configure console encoding for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def print_banner():
    banner = """
================================================================================
    INTRINSIC | Automated Subscription & Invoicing Management OS
    Built for Odoo Makeathon (FastAPI + SQLAlchemy + SQLite + Alpine.js + Tailwind)
================================================================================
[*] Server Address : http://localhost:8000
[*] API Docs       : http://localhost:8000/docs
[*] SQLite DB      : intrinsic.db (Auto-seeded with test personas & subscriptions)

[Instant Persona Credentials for Makeathon Judges]:
  1. Administrator  : admin@intrinsic.io    | Intrinsic@2026!
  2. Internal Staff : staff@intrinsic.io    | Intrinsic@2026!
  3. Customer Portal: customer@intrinsic.io | Intrinsic@2026!

[Security & State Machine Rules]:
  - Passwords strictly enforced (>8 chars, 1 uppercase, 1 lowercase, 1 special).
  - Public registration restricted strictly to Customer role.
  - Subscription State Machine: Draft -> Quotation -> Confirmed -> Active -> Closed.
  - Automated Billing Engine: "Run Billing Cycle" advances cycles & flags overdue.
================================================================================
"""
    print(banner)

def main():
    print_banner()
    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass

    # Run FastAPI via Uvicorn
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    main()
