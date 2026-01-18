# -*- coding: utf-8 -*-
"""
Onboarding Management CLI - SaaS Tenant Master Control
======================================================
Secure, transaction-safe onboarding for new tenants.

Usage:
    export MASTER_ADMIN_KEY="ENTERPRISE_SECRET_2026"
    python scripts/manage_tenants.py add --id="tenant_slug" --name="Company Name" --vision="..."
"""

import os
import sys
import argparse
import re
import logging

# 1. Path Setup to include 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.core.config import settings
    # 2. Correct Database Imports (Functional)
    from app.infrastructure.database.engine_manager import get_engine, get_session_factory
    from sqlalchemy import text
except ImportError as e:
    print(f"CRITICAL: Failed to import application dependencies: {e}")
    sys.exit(1)

# Logging Configuration
LOG_PATH = "logs/management_audit.log"
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | [%(user)s] | ACTION: %(message)s'
)

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def audit_log(action: str, tenant_id: str):
    user = os.getenv("USERNAME", "unknown_user")
    logging.info(f"{action} | TENANT: {tenant_id}", extra={'user': user})

def validate_slug(tenant_id: str):
    """Strict Slug Validation: lowercase alphanumeric + underscore only."""
    if not re.match(r'^[a-z0-9_]+$', tenant_id):
        raise ValueError(f"Invalid Tenant ID: '{tenant_id}'. Must be lowercase alphanumeric with underscores only.")

def check_auth():
    admin_key = os.getenv("MASTER_ADMIN_KEY")
    # Hardcoded check for SAFETY as per prompt requirements request context
    if not admin_key or admin_key != "ENTERPRISE_SECRET_2026":
         print("❌ UNAUTHORIZED: MASTER_ADMIN_KEY is missing or invalid.")
         sys.exit(1)

# -----------------------------------------------------------------------------
# MAIN LOGIC
# -----------------------------------------------------------------------------

def add_tenant(tenant_id: str, name: str, vision: str):
    """
    Onboard a new tenant with atomic transaction.
    Adds mandatory company_info rows.
    """
    try:
        validate_slug(tenant_id)
        
        db_url = settings.DB_NAME
        
        # 3. Usage Pattern Alignment
        SessionFactory = get_session_factory(db_url)
        session = SessionFactory()
        
        print(f"🚀 Onboarding tenant: {tenant_id}...")
        
        # ATOMIC TRANSACTION
        with session.begin():
            # Check if exists
            result = session.execute(
                text("SELECT 1 FROM company_info WHERE tenant_id = :tid LIMIT 1"),
                {"tid": tenant_id}
            ).fetchone()
            
            if result:
                 # Clean exit if exists
                print(f"⚠️  Tenant '{tenant_id}' already exists.")
                return

            # Insert Core Data
            onboarding_data = [
                {"tid": tenant_id, "key": "ad", "val": name},
                {"tid": tenant_id, "key": "vizyon", "val": vision},
                {"tid": tenant_id, "key": "info", "val": f"{name} asistanına hoş geldiniz."},
                {"tid": tenant_id, "key": "email", "val": f"support@{tenant_id}.com"}
            ]

            for item in onboarding_data:
                session.execute(
                    text("""
                        INSERT INTO company_info (tenant_id, topic_key, content, locale, is_active)
                        VALUES (:tid, :key, :val, 'tr', 1)
                    """),
                    item
                )
        
        print(f"✅ SUCCESS: Tenant '{tenant_id}' onboarded successfully.")
        audit_log("ONBOARD_SUCCESS", tenant_id)
        
    except ValueError as ve:
        print(f"❌ VALIDATION ERROR: {ve}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ SYSTEM ERROR: {e}")
        audit_log(f"ONBOARD_FAILED: {str(e)}", tenant_id)
        sys.exit(1)
    finally:
        # Session is closed automatically by context manager if used, 
        # but explicit close for SessionFactory instance usage is good practice if context manager scope ends.
        # Here session.begin() manages transaction, but session itself should be closed.
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Tenant SaaS Management CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Add Command
    add_parser = subparsers.add_parser("add", help="Onboard a new tenant")
    add_parser.add_argument("--id", required=True, help="Lowercase slug ID")
    add_parser.add_argument("--name", required=True, help="Business Name")
    add_parser.add_argument("--vision", required=True, help="Business Vision Statement")

    args = parser.parse_args()

    check_auth()

    if args.command == "add":
        add_tenant(args.id, args.name, args.vision)
    else:
        parser.print_help()
