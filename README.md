# Simplify Money Gold API — Hosted Execution Guide

Your API is live at:
https://simplify-gold-api.onrender.com

---

## 1️⃣ Overview
This project replicates the gold investment assistant workflow inspired by Simplify Money.
It supports:
- Answering questions about gold investment
- Nudging users to invest in digital gold
- Simulating a purchase process and logging transactions

---

## 2️⃣ Solution Details
- Built with **FastAPI** for high performance and easy API development
- **SQLite** database for simplicity and quick testing
- Two key APIs:
  1. `/advisor` — interacts with the user, identifies gold-related queries, and nudges for digital gold investment
  2. `/purchase` — completes the purchase workflow and stores the transaction in the database
- Fully deployed on **Render** (free tier)

---

## 3️⃣ Deployment Notes
- **Hosting Platform:** Render (https://render.com)
- **Runtime:** Python 3.11
- **Database:** SQLite, stored in persistent storage on the server
- **Health Check:** `/health` endpoint ensures uptime monitoring
- **Cold Start Delay:** First API call after inactivity may take ~15 seconds due to free-tier sleep

---

## 4️⃣ Execution — Hosted API

### **Check API Health**
```bash
curl https://simplify-gold-api.onrender.com/health

Expected Response:

{"status":"ok","timestamp":"<current-utc-timestamp>"}

Ask About Gold

curl -X POST https://simplify-gold-api.onrender.com/advisor ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"Should I invest in gold now?\",\"name\":\"Aarav\",\"email\":\"aarav@example.com\"}"

Example Response:

{
  "reply": "Yes, gold is considered a safe asset. You can invest via Simplify Money digital gold.",
  "suggestion": "Would you like to buy digital gold now?"
}

Make a Purchase

curl -X POST https://simplify-gold-api.onrender.com/purchase ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\":1,\"amount_in_inr\":5000}"

Example Response:

{
  "message": "Purchase successful!",
  "user": "Aarav",
  "amount_in_inr": 5000,
  "transaction_id": "TXN123456789",
  "price_per_gram": 5800
}

View Purchase History

curl https://simplify-gold-api.onrender.com/purchases/1

Example Response:

[
  {
    "id": 1,
    "user_id": 1,
    "amount_in_inr": 5000,
    "price_per_gram": 5800,
    "timestamp": "2025-08-26T05:00:00"
  }
]

5️⃣ Approach

    Designed endpoints based on REST API principles.

    Built a lightweight classification layer to detect gold-related queries.

    Used SQLite for quick transaction logging.

    Deployed to Render with gunicorn + uvicorn for production-ready performance.

6️⃣ Challenges and Notes

    Cold Starts: Free-tier Render apps sleep after inactivity; first request may be slow.

    Scalability: SQLite is fine for POC but not for production. Upgrade to Postgres or MySQL for scaling.

    Gold Price Data: Currently hardcoded; can integrate a real-time price API like metals-api for live rates.

    Security: Basic validation implemented. Production should have authentication & HTTPS-only requests.

    Logging: Minimal logging; can integrate structured logs for better debugging in future iterations.

7️⃣ Tips

    Use Postman or Insomnia if you prefer a GUI over curl.

    Always ping /health first to wake up the server.

    Extend the /advisor LLM logic for more complex conversations.
