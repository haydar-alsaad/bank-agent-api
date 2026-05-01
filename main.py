"""
Bank Agent API - v1.1
7 endpoints (5 demo + /health + root):
  GET /                      - root (API info)
  GET /health                - status + data load counts
  GET /customer              - workhorse: full customer package
                               (accounts, wallets, cards, recent txns, bills, active onboarding journey)
  GET /transactions          - filtered transaction history (when more than recent 10 are needed)
  GET /branch                - branch/ATM lookup (by city, type, or service)
  GET /product               - product catalog lookup
  GET /biller                - biller catalog lookup
  GET /kyc-tier              - KYC tier requirements & limits (for upgrade pitch flows)
"""
import json
import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Bank Agent API", version="1.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

customers = []
accounts = []
wallets = []
cards = []
transactions = []
bill_payments = []
billers_catalog = []
products_catalog = []
branches_atms = []
kyc_tiers = []
wallet_onboarding_journeys = []


def load(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_all_data():
    global customers, accounts, wallets, cards, transactions, bill_payments
    global billers_catalog, products_catalog, branches_atms, kyc_tiers, wallet_onboarding_journeys

    customers = load("customers.json")
    accounts = load("accounts.json")
    wallets = load("wallets.json")
    cards = load("cards.json")
    transactions = load("transactions.json")
    bill_payments = load("bill_payments.json")
    billers_catalog = load("billers_catalog.json")
    products_catalog = load("products_catalog.json")
    branches_atms = load("branches_atms.json")
    kyc_tiers = load("kyc_tiers.json")
    wallet_onboarding_journeys = load("wallet_onboarding_journeys.json")


@app.on_event("startup")
def startup():
    load_all_data()


# ============================================================
# Lookup helpers
# ============================================================

def find_customer(cid):
    return next((c for c in customers if c["Customer ID"] == cid), None)

def find_customer_by_phone(phone):
    return next((c for c in customers if c["Phone"] == phone), None)

def find_biller(bid):
    return next((b for b in billers_catalog if b["Biller ID"] == bid), None)

def find_kyc_tier_by_name(tier_name):
    return next((t for t in kyc_tiers if t["Tier Name (EN)"].lower() == tier_name.lower()), None)


# ============================================================
# Endpoints
# ============================================================

@app.get("/")
def root():
    return {
        "name": "Bank Agent API",
        "version": "1.1",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "version": "1.1",
        "data_loaded": {
            "customers": len(customers),
            "accounts": len(accounts),
            "wallets": len(wallets),
            "cards": len(cards),
            "transactions": len(transactions),
            "bill_payments": len(bill_payments),
            "billers_catalog": len(billers_catalog),
            "products_catalog": len(products_catalog),
            "branches_atms": len(branches_atms),
            "kyc_tiers": len(kyc_tiers),
            "wallet_onboarding_journeys": len(wallet_onboarding_journeys),
        }
    }


@app.get("/customer")
def get_customer_data(
    customer_id: Optional[str] = Query(None, description="Customer ID e.g. CUST-001"),
    phone: Optional[str] = Query(None, description="Phone number e.g. +966501234001"),
    transaction_limit: int = Query(10, description="Max recent transactions per account"),
):
    """Workhorse endpoint - everything for one customer in a single call.

    Returns:
      - customer profile
      - all accounts (current/savings/investment)
      - all wallets
      - all cards (with status, including any frozen/disputed)
      - recent transactions (limit per account, most recent first)
      - recent bill payments
      - active wallet onboarding journey (if any)
    """
    if not customer_id and not phone:
        raise HTTPException(400, "Provide either customer_id or phone")

    customer = find_customer(customer_id) if customer_id else find_customer_by_phone(phone)
    if not customer:
        raise HTTPException(404, "Customer not found")

    cid = customer["Customer ID"]

    cust_accounts = [a for a in accounts if a["Customer ID"] == cid]
    cust_wallets = [w for w in wallets if w["Customer ID"] == cid]
    cust_cards = [c for c in cards if c["Customer ID"] == cid]

    # Recent transactions per account (limit per account)
    cust_txns = [t for t in transactions if t["Customer ID"] == cid]
    cust_txns.sort(key=lambda t: (t["Date"], t["Time"]), reverse=True)
    by_account = {}
    for t in cust_txns:
        by_account.setdefault(t["Account ID"], []).append(t)
    recent_transactions = []
    for acc_id, txns in by_account.items():
        recent_transactions.extend(txns[:transaction_limit])
    recent_transactions.sort(key=lambda t: (t["Date"], t["Time"]), reverse=True)

    # Recent bill payments
    cust_bills = [p for p in bill_payments if p["Customer ID"] == cid]
    cust_bills.sort(key=lambda p: (p["Date"], p["Time"]), reverse=True)
    recent_bills = cust_bills[:transaction_limit]

    # Active onboarding journey (folded in — no separate endpoint needed)
    journey = next((j for j in wallet_onboarding_journeys if j["Customer ID"] == cid), None)

    return {
        "customer": customer,
        "accounts": cust_accounts,
        "wallets": cust_wallets,
        "cards": cust_cards,
        "recent_transactions": recent_transactions,
        "recent_bill_payments": recent_bills,
        "active_onboarding_journey": journey,
        "totals": {
            "accounts": len(cust_accounts),
            "wallets": len(cust_wallets),
            "cards": len(cust_cards),
            "transactions_total": len(cust_txns),
            "transactions_returned": len(recent_transactions),
            "bills_total": len(cust_bills),
            "bills_returned": len(recent_bills),
        }
    }


@app.get("/transactions")
def get_transactions(
    customer_id: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None, description="Account or Wallet ID"),
    transaction_type: Optional[str] = Query(None, description="POS Purchase / Salary / Bill Payment / Transfer In / Transfer Out / etc."),
    category: Optional[str] = Query(None, description="Groceries / Dining / Salary / Telecom / etc."),
    direction: Optional[str] = Query(None, description="Debit or Credit"),
    status: Optional[str] = Query(None, description="Completed / Pending / Disputed / etc."),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit: int = Query(20),
):
    """Filtered transaction history. Use when /customer's recent_transactions isn't enough
    (e.g., 'show me all my Saudi Electricity bills', 'find that disputed transaction')."""
    txns = list(transactions)

    if customer_id:
        txns = [t for t in txns if t["Customer ID"] == customer_id]
    if account_id:
        txns = [t for t in txns if t["Account ID"] == account_id]
    if transaction_type:
        txns = [t for t in txns if t["Transaction Type"].lower() == transaction_type.lower()]
    if category:
        txns = [t for t in txns if t["Category"].lower() == category.lower()]
    if direction:
        txns = [t for t in txns if t["Direction"].lower() == direction.lower()]
    if status:
        txns = [t for t in txns if t["Status"].lower() == status.lower()]
    if date_from:
        txns = [t for t in txns if t["Date"] >= date_from]
    if date_to:
        txns = [t for t in txns if t["Date"] <= date_to]

    txns.sort(key=lambda t: (t["Date"], t["Time"]), reverse=True)
    return {
        "transactions": txns[:limit],
        "total_matching": len(txns),
        "returned": min(limit, len(txns)),
    }


@app.get("/branch")
def get_branches(
    city: Optional[str] = Query(None, description="City name (English or Arabic)"),
    type: Optional[str] = Query(None, description="Branch / ATM / ITM"),
    service: Optional[str] = Query(None, description="e.g. 'Wealth Advisory'"),
):
    """Branch and ATM lookup with optional filters."""
    results = list(branches_atms)
    if city:
        c = city.lower()
        results = [b for b in results if b["City (EN)"].lower() == c or b["City (AR)"] == city]
    if type:
        results = [b for b in results if b["Type"].lower() == type.lower()]
    if service:
        s = service.lower()
        results = [b for b in results if any(s in svc.lower() for svc in b["Services"])]
    return {"branches": results, "count": len(results)}


@app.get("/product")
def get_products(
    product_id: Optional[str] = Query(None),
    product_type: Optional[str] = Query(None, description="Wallet / Account / Card"),
    tier: Optional[str] = Query(None, description="Basic / Plus / Premium / Business / Standard"),
):
    """Product catalog lookup."""
    if product_id:
        prod = next((p for p in products_catalog if p["Product ID"] == product_id), None)
        if not prod:
            raise HTTPException(404, f"Product {product_id} not found")
        return prod
    results = list(products_catalog)
    if product_type:
        results = [p for p in results if p["Product Type"].lower() == product_type.lower()]
    if tier:
        results = [p for p in results if p["Product Tier"].lower() == tier.lower()]
    return {"products": results, "count": len(results)}


@app.get("/biller")
def get_billers(
    biller_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None, description="Telecom / Utilities / Government / Insurance / Charity"),
):
    """Biller catalog lookup. Use when customer wants to pay a bill."""
    if biller_id:
        b = find_biller(biller_id)
        if not b:
            raise HTTPException(404, f"Biller {biller_id} not found")
        return b
    results = list(billers_catalog)
    if category:
        results = [b for b in results if b["Category"].lower() == category.lower()]
    return {"billers": results, "count": len(results)}


@app.get("/kyc-tier")
def get_kyc_tier(
    tier_id: Optional[str] = Query(None, description="e.g. KYC-PLUS"),
    tier_name: Optional[str] = Query(None, description="e.g. Plus"),
):
    """KYC tier lookup. Use when explaining what's needed to upgrade
    (e.g., Sara hits Basic 5K limit, agent pitches Plus upgrade)."""
    if not tier_id and not tier_name:
        return {"tiers": kyc_tiers, "count": len(kyc_tiers)}
    if tier_id:
        t = next((kt for kt in kyc_tiers if kt["Tier ID"] == tier_id), None)
    else:
        t = find_kyc_tier_by_name(tier_name)
    if not t:
        raise HTTPException(404, "KYC tier not found")
    return t
