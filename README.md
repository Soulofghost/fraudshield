# FraudShield

[![CI Pipeline](https://github.com/Soulofghost/fraudshield/actions/workflows/ci.yml/badge.svg)](https://github.com/Soulofghost/fraudshield/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57.svg)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **FraudShield** is a real-time financial transaction anomaly and fraud detection system. It combines geographic velocity calculation (impossible travel detection), rolling short-window burst analysis, statistical amount Z-scoring, and merchant risk categorizations to evaluate payments in sub-5ms latency.

---

## 1. System Architecture

FraudShield intercepts inbound transactions and evaluates them against the cardholder's historical profile and global risk matrices.

```
┌─────────────────────────────────────────────────────────────┐
│                 Threat Operations Cockpit                   │
│   • Multi-scenario simulation (Coffee, Tokyo, Burst, Crypto)│
│   • Real-Time Risk Score Meter (0 to 100)                   │
│   • Interactive Security Alerts Triage & Resolution         │
│   • Live Financial Transaction Stream                       │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼──────────────────────────────┐
│                   FastAPI Application Tier                  │
│   • Transaction Evaluation Endpoint                         │
│   • Historical Baseline Retrieval                           │
│   • Alert Workflow & Lifecycle State-Machine                │
└──────────────────────────────┬──────────────────────────────┘
                               │
       ┌───────────────────────┴───────────────────────┐
       ▼                                               ▼
┌─────────────────────────────┐         ┌─────────────────────────────┐
│  Multi-Factor Anomaly Engine│         │   High-Throughput Storage   │
│  • Haversine Geo-Velocity   │         │   • SQLite 3 WAL Mode       │
│  • Rolling Window Burst     │         │   • Foreign Key Constraints │
│  • Amount Z-Score Outlier   │         │   • Transactions & Alerts   │
│  • High-Risk Category Flag  │         │   • Risk Factor Audit JSON  │
│  • Unrecognized Device & IP │         └─────────────────────────────┘
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│    Decision State Machine   │
│  • Risk < 35   -> APPROVED  │
│  • 35-69 Risk  -> REVIEW    │
│  • Risk >= 70  -> BLOCKED   │
└─────────────────────────────┘
```

---

## 2. Core Anomaly Detection Heuristics

### A. Impossible Travel Geo-Velocity
Computes great-circle distance using the Haversine formula:
$$\Delta\sigma = 2 \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)$$
$$\text{Distance} = R \cdot \Delta\sigma \quad (R = 6,371\text{ km})$$
$$\text{Velocity} = \frac{\text{Distance}}{\Delta t \text{ (hours)}}$$
If required speed exceeds **800 km/h** between transactions across distinct locations within a short time window ($\Delta t < 6\text{h}$), an `IMPOSSIBLE_TRAVEL` critical anomaly (+45 risk points) is triggered.

### B. Short-Window Velocity Spikes
Detects automated card testing and brute-force card enumeration by scanning rolling time windows:
- 3+ transactions in under 10 minutes triggers `VELOCITY_SPIKE` (+35 risk points).

### C. Statistical Amount Outliers (Z-Score)
Evaluates amount deviations against the user's historical spend profile:
$$Z = \frac{x - \mu}{\max(\sigma, 15.0)}$$
If $Z \ge 3.0$ and amount exceeds baseline thresholds, triggers `STATISTICAL_AMOUNT_ANOMALY` (+40 risk points).

### D. High-Risk Merchant & Category Weighting
Transactions directed toward high-chargeback categories (`cryptocurrency_exchange`, `luxury_jewelry`, `wire_transfer`, `gambling_casino`) incur immediate +25 risk points.

---

## 3. Technology Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **API Framework** | FastAPI 0.110+ | Real-time microsecond-level REST endpoint |
| **Data Validation** | Pydantic v2 | Strict JSON schema enforcement |
| **Persistence** | SQLite 3 | WAL mode with sub-millisecond sequential logging |
| **Frontend UI** | Vanilla JS / CSS3 | Cyber-fintech threat operations center |
| **Testing** | Pytest + HTTPX | Integration and statistical math unit tests |
| **DevOps** | Docker / Compose | Multi-stage production container |
| **CI/CD** | GitHub Actions | Automated build and test validation |

---

## 4. API Reference

### Evaluation
- `POST /api/transactions/evaluate` — Evaluates transaction, computes composite risk score, persists record, and raises compliance alert if flagged.
  ```json
  {
    "user_id": "usr_alvin_884",
    "card_last4": "8821",
    "amount": 1450.00,
    "currency": "USD",
    "merchant_name": "Bic Camera Tokyo",
    "merchant_category": "luxury_jewelry",
    "latitude": 35.6762,
    "longitude": 139.6503,
    "device_id": "pos_tokyo_terminal"
  }
  ```

### Auditing & Alerts
- `GET /api/transactions` — Query transactions with filtering (`decision`, `user_id`, `min_score`).
- `GET /api/transactions/{id}` — Retrieve detailed transaction with all triggered risk factors.
- `GET /api/alerts` — Query open security compliance alerts.
- `PATCH /api/alerts/{id}` — Resolve or dismiss an alert.

### Analytics
- `GET /api/analytics/risk-summary` — Aggregated fraud metrics (total screened, block rate, prevented volume).
- `GET /health` — Liveness and readiness probe.

---

## 5. Local Setup & Testing

### Installation
```bash
# Clone the repository
git clone https://github.com/Soulofghost/fraudshield.git
cd fraudshield

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

### Running FraudShield
```bash
uvicorn app.main:app --app-dir backend --reload --port 8000
```
Visit `http://localhost:8000` to interact with the threat operations cockpit.

### Running Test Suite
```bash
pytest backend/tests -v
```

---

## 6. Docker Deployment

```bash
docker-compose up --build -d
docker-compose logs -f
```

---

## 7. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
