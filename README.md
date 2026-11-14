# VyaparVaani AI (વેપારવાણી / व्यापारवाणी)
### Multilingual Voice-Driven Agentic Operations Platform for Indian MSMEs

[![Hackathon](https://img.shields.io/badge/Google%20Cloud-Build%20with%20Gemini-blue)](https://hack2skill.com)
[![Problem Statement](https://img.shields.io/badge/Problem%20Statement-PS02%20Voice--Driven%20Workflow%20Automation-success)](https://hack2skill.com)
[![License](https://img.shields.io/badge/License-Apache--2.0-orange)](LICENSE)

> **"Speak Naturally. Execute Intelligently. Operate Effortlessly."**

---

## 🌟 What is VyaparVaani AI?

**VyaparVaani AI** is an enterprise-grade, voice-first agentic platform built specifically for Indian Kirana shop owners, retail merchants, and wholesale FMCG distributors.

Instead of navigating complex English dropdowns or typing numbers on mobile screens while handling busy counters, shopkeepers speak naturally in **Gujarati, Hindi, English, or Hinglish**. 

VyaparVaani AI:
1. Listens to streaming 16kHz audio in real time using **Google Gemini Live API**.
2. Handles **barge-in interruptions and mid-sentence corrections** effortlessly.
3. Understands complex, multi-intent business instructions.
4. Validates business policies (credit limits, stock availability, discount thresholds) with a **deterministic backend engine**.
5. Employs **Human-in-the-Loop approvals** for high-risk operations.
6. Executes atomic database transactions (orders, stock updates, khata ledger entries, delivery tasks).
7. Confirms transactions through natural, conversational vernacular voice read-backs.

---

## 🏗️ Architecture & Technology Stack

- **AI & Voice Intelligence**: Google Gemini Live API (`gemini-2.0-flash-exp`) & Google GenAI SDK
- **Backend**: Python 3.12, FastAPI (Asynchronous), Pydantic v2, WebSockets
- **Database**: SQLAlchemy 2.0 Async ORM with SQLite (local development) and Google Cloud SQL PostgreSQL (production)
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Web Audio API PCM streaming
- **Cloud & Deployment**: Google Cloud Run (Serverless), Google Secret Manager, Cloud Logging

---

## 🚀 Quickstart

### 1. Backend Setup
```bash
# Clone and navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example .env
# Edit .env and supply your GEMINI_API_KEY if testing real Gemini voice live

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```
API Documentation will be live at: `http://localhost:8000/docs`

### 2. Frontend Setup
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 📂 Project Organization

```text
VyaparVaaniAI/
├── frontend/               # React + TypeScript + Tailwind UI
├── backend/                # FastAPI Asynchronous Application
│   ├── app/
│   │   ├── api/            # REST and WebSocket endpoints
│   │   ├── core/           # Configuration, database connection, events
│   │   ├── models/         # SQLAlchemy 2.0 Async ORM models
│   │   ├── schemas/        # Pydantic v2 validation models
│   │   ├── services/       # Customer, Order, Inventory, Ledger services
│   │   ├── tools/          # Strongly-typed tools for Gemini Live
│   │   ├── business_rules/ # Deterministic credit & policy validations
│   │   ├── workflows/      # Orchestrated agentic multi-step pipelines
│   │   └── main.py         # Application entry point
│   └── tests/              # Pytest test suite
├── infrastructure/         # Dockerfiles and deployment configs
├── docs/                   # (Ignored by Git) Comprehensive specifications & guides
├── docker-compose.yml      # Local containerized orchestration
└── README.md
```

---

## 🏆 Hackathon Winning Features
- **Real-Time Vernacular Voice**: Conversational Gujarati and Hindi with turn-taking and spoken barge-in correction.
- **Agentic Function Calling**: Gemini autonomously searches customers, validates inventory, drafts orders, and posts to ledger.
- **Safety First**: Human-in-the-loop approval center for orders exceeding policy thresholds.
- **Deterministic Reliability**: Zero hallucinations in accounting—models propose, backend validates and executes.
- **Complete Auditability**: Comprehensive audit trail for all voice transactions and supervisor decisions.
