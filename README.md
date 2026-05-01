# Bank Agent API

Demo API for the Noor Digital Bank WhatsApp agent (T2 Communicate × Nebelus).

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Status + data load counts |
| `GET /customer?customer_id=CUST-001` | Workhorse — full customer package (accounts, wallets, cards, recent txns, bills, onboarding) |
| `GET /transactions?customer_id=CUST-001&limit=20` | Filtered transaction history |
| `GET /card?card_id=CARD-001` | Card details |
| `GET /branch?city=Riyadh` | Branch and ATM lookup |
| `GET /product?product_type=Wallet` | Product catalog |
| `GET /biller?category=Telecom` | Biller catalog |
| `GET /kyc-tier?tier_name=Plus` | KYC tier requirements |
| `GET /onboarding-journey?customer_id=CUST-003` | Wallet onboarding journey lookup |

## Local development

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for the interactive Swagger UI.

## Deployment to Railway

1. Push this repo to GitHub.
2. Connect Railway to the repo.
3. Railway auto-detects the Procfile and builds.
4. No environment variables needed.

## Data

All data is in `/data` as JSON files. Cross-references validated.

| File | Records |
|---|---|
| customers.json | 10 |
| accounts.json | 19 |
| wallets.json | 9 |
| cards.json | 13 |
| transactions.json | 190 |
| bill_payments.json | 30 |
| billers_catalog.json | 12 |
| products_catalog.json | 8 |
| branches_atms.json | 12 |
| kyc_tiers.json | 5 |
| wallet_onboarding_journeys.json | 2 |

## Demo personas

| ID | Name | Use for |
|---|---|---|
| CUST-001 | Mohammed Al-Shammari | English headline — full demo flow |
| CUST-002 | Nora Al-Faisal | Arabic headline — full demo flow |
| CUST-003 | Khalid Al-Mutairi | Resume stalled wallet onboarding |
| CUST-004 | Lama Al-Zahrani | Live wallet onboarding from zero |
| CUST-005 | Abdullah Al-Qahtani | Wealth / investment review |
| CUST-006 | Sara Al-Dossary | KYC upgrade pitch (hit Basic 5K limit) |
| CUST-007 | Faisal Al-Otaibi | Fraud dispute / card replacement |
| CUST-008 | Fatima Al-Zamil | SME / business banking |
| CUST-009 | Yousef Al-Harbi | Standard retail / everyday banking |
| CUST-010 | Dalia Al-Rashid | Young professional / savings goal |

## Security note

This is demo data. Names, IDs, IBANs, and phone numbers are fictional.
The agent's system instructions enforce masking of sensitive fields.
