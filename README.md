# 🚀 DevTrack AI - Unified AI Business Operating System

> **Lebanon's First Multi-Industry AI Platform** — Manage communication, operations, customers, orders, bookings, and analytics in one powerful system.

![Platform](https://img.shields.io/badge/Platform-SaaS-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-teal)
![License](https://img.shields.io/badge/License-MIT-purple)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Docker Setup](#docker-setup)
- [API Documentation](#api-documentation)
- [Frontend Dashboard](#frontend-dashboard)
- [AI System](#ai-system)
- [Industry Modules](#industry-modules)
- [Chat Widget](#chat-widget)
- [Configuration](#configuration)
- [Contributing](#contributing)

---

## 🎯 Overview

DevTrack AI is a **multi-industry, all-in-one AI platform** that helps ALL types of businesses manage:

- 🤖 **AI Communication** — Context-aware, multilingual chat (English, Arabic, Lebanese)
- 📦 **Orders & Bookings** — Create and track via chat or manually
- 👥 **Customer CRM** — Full customer profiles with history
- ⚡ **Automation** — IF/THEN workflow rules
- 📈 **Analytics** — AI-generated business insights
- 📂 **Knowledge Base** — RAG system for document-based AI responses
- 🧩 **Multi-Module** — Restaurant, Hotel, Clinic, Retail, Delivery

---

## ✨ Features

### Core AI System
- **Google Gemini** integration for intelligent conversations
- **Intent Detection** — question, order, booking, complaint
- **Sentiment Analysis** — real-time customer sentiment tracking
- **Decision Layer** — AI decides to respond, create order, escalate
- **RAG System** — Upload documents, AI learns from your content

### Multi-Channel
- 🌐 Web Chat Widget (embeddable)
- 📱 WhatsApp Integration (ready)
- Future: Instagram, Messenger

### Dashboard (11 Pages)
1. 📊 Dashboard — Overview with AI insights
2. 💬 Conversations — Live chat with AI/human toggle
3. 👥 Customers — CRM with profiles
4. 📦 Orders — Full order management
5. 📅 Bookings — Reservations & appointments
6. 🏷️ Products — Catalog management
7. 📂 Documents — Knowledge base
8. ⚡ Automation — Workflow builder
9. 📈 Analytics — Charts & AI reports
10. 🧩 Modules — Enable/disable industry modules
11. ⚙️ Settings — Business config, branding, API keys

---

## 🏗️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python 3.11+) |
| AI Engine | Google Gemini API |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Vector DB | FAISS |
| Background Jobs | Celery |
| Auth | JWT (python-jose) |
| Frontend | Vanilla HTML/CSS/JS |
| Deployment | Docker & Docker Compose |

---

## 📁 Project Structure

```
DevTrack/
├── app/                        # Backend Application
│   ├── api/                    # API Routes
│   │   ├── auth.py             # Authentication endpoints
│   │   ├── business.py         # Business management
│   │   ├── conversations.py    # Chat & messaging
│   │   ├── chat.py             # Public chat (widget API)
│   │   └── routes.py           # Customers, orders, bookings, etc.
│   ├── core/                   # Core Configuration
│   │   ├── config.py           # Settings & env vars
│   │   └── security.py         # JWT auth & password hashing
│   ├── db/                     # Database
│   │   └── session.py          # SQLAlchemy session management
│   ├── models/                 # Database Models
│   │   ├── user.py             # Users & roles
│   │   ├── business.py         # Business & modules
│   │   ├── customer.py         # Customers
│   │   ├── conversation.py     # Conversations & messages
│   │   ├── order.py            # Orders & items
│   │   ├── booking.py          # Bookings
│   │   ├── product.py          # Products & categories
│   │   ├── service.py          # Services
│   │   ├── document.py         # Documents & chunks
│   │   ├── workflow.py         # Automation workflows
│   │   ├── analytics.py        # Analytics events
│   │   ├── module.py           # Module definitions
│   │   └── notification.py     # Notifications
│   ├── schemas/                # Pydantic Schemas
│   │   ├── auth.py             # Auth schemas
│   │   ├── business.py         # Business schemas
│   │   └── schemas.py          # All other schemas
│   ├── services/               # Business Logic
│   │   ├── ai_service.py       # Gemini AI integration
│   │   ├── rag_service.py      # RAG / vector search
│   │   └── automation_service.py # Workflow engine
│   ├── workers/                # Background Workers
│   │   └── celery_app.py       # Celery tasks
│   ├── modules/                # Industry Modules (extensible)
│   ├── utils/                  # Utilities
│   └── main.py                 # FastAPI Application
├── frontend/                   # Frontend Dashboard
│   ├── index.html              # Main HTML
│   └── assets/
│       ├── css/styles.css      # Complete CSS design system
│       └── js/
│           ├── api.js          # API client with demo mode
│           ├── app.js          # App controller
│           └── pages.js        # All page renderers
├── widget/                     # Embeddable Chat Widget
│   └── widget.js               # Self-contained chat widget
├── docker-compose.yml          # Docker services
├── Dockerfile                  # Python container
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
├── .env.example                # Template
└── README.md                   # This file
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- (Optional) Docker & Docker Compose

### Option 1: Docker (Recommended)

```bash
# Clone the project
cd DevTrack

# Start all services
docker-compose up -d

# The app will be available at:
# Dashboard: http://localhost:8000
# API Docs:  http://localhost:8000/api/docs
```

### Option 2: Manual Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env with your database and API keys

# 4. Start PostgreSQL and Redis
# (Make sure they're running locally)

# 5. Run the application
uvicorn app.main:app --reload --port 8000

# 6. Open the dashboard
# http://localhost:8000
```

### First Steps
1. Open `http://localhost:8000`
2. Click "Create Account"
3. Enter your business details
4. You're in! Explore the dashboard

> 💡 **Demo Mode**: The frontend works even without the backend running, showing realistic mock data for development and testing.

---

## 🐳 Docker Setup

```yaml
# docker-compose.yml includes:
- FastAPI (port 8000)
- PostgreSQL (port 5432)
- Redis (port 6379)
- Celery Worker (background tasks)
```

```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop
docker-compose down

# Rebuild
docker-compose up -d --build
```

---

## 📡 API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user & business |
| POST | `/api/v1/auth/login` | Login & get JWT token |
| GET | `/api/v1/business/` | Get business details |
| GET | `/api/v1/conversations/` | List conversations |
| POST | `/api/v1/conversations/{id}/messages` | Send message (triggers AI) |
| GET | `/api/v1/customers/` | List customers |
| POST | `/api/v1/orders/` | Create order |
| POST | `/api/v1/bookings/` | Create booking |
| GET | `/api/v1/products/` | List products |
| POST | `/api/v1/documents/upload` | Upload knowledge base doc |
| GET | `/api/v1/workflows/` | List automation rules |
| GET | `/api/v1/analytics/summary` | Dashboard analytics |
| GET | `/api/v1/analytics/insights` | AI-generated insights |
| POST | `/api/v1/chat/message` | Public chat (widget) |

---

## 🧠 AI System

### Google Gemini Integration
Set your API key in `.env`:
```
GEMINI_API_KEY=your-api-key-here
```

### Decision Layer
For every customer message, the AI:
1. **Detects Intent** — question, order, booking, complaint
2. **Analyzes Sentiment** — score from -100 to +100
3. **Decides Action** — respond, create order/booking, or escalate

### RAG System
1. Upload documents (PDF, TXT)
2. System extracts text and creates chunks
3. Chunks are embedded and stored in FAISS index
4. When customers chat, relevant context is retrieved
5. AI uses context to provide accurate responses

---

## 🧩 Industry Modules

Enable modules based on your business type:

| Module | Features |
|--------|----------|
| 🍔 Restaurant | Menu, orders, table reservations, delivery |
| 🏨 Hotel | Room booking, availability, guest management |
| 🛍️ Retail | Products, inventory, orders, discounts |
| 🏥 Clinic | Appointments, doctor schedules, patient records |
| 🚚 Delivery | Order tracking, driver status, route management |

---

## 🌐 Chat Widget

Embed the chat widget on any website:

```html
<script src="https://yourserver.com/widget/widget.js" data-business="your-business-slug"></script>
```

Features:
- 💬 Floating chat bubble
- 🤖 AI-powered responses
- 🌓 Dark mode design
- 📱 Mobile responsive
- 🔄 Session persistence

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://devtrack:devtrack123@db:5432/devtrack` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `GEMINI_API_KEY` | Google Gemini API key | (empty) |
| `JWT_SECRET_KEY` | JWT signing secret | (change in production!) |
| `JWT_EXPIRATION_MINUTES` | Token lifetime | 1440 (24h) |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:3000,...` |
| `MAX_UPLOAD_SIZE_MB` | Max document upload size | 50 |

---

## 🔐 Security

- ✅ JWT token authentication
- ✅ Password hashing (bcrypt)
- ✅ Multi-tenant data isolation
- ✅ Input validation (Pydantic)
- ✅ CORS protection
- ✅ Environment variable secrets
- ✅ SQL injection protection (SQLAlchemy ORM)

---

## 📈 Scalability

- ✅ Async-first design (FastAPI)
- ✅ Connection pooling (SQLAlchemy)
- ✅ Background task processing (Celery)
- ✅ Cache layer (Redis)
- ✅ Multi-tenant architecture
- ✅ Modular plugin system
- ✅ Docker containerization

---

## 🇱🇧 Built for Lebanon

- 🌍 Multilingual: English, Arabic, Lebanese dialect
- 💱 Multi-currency support
- 📱 WhatsApp integration (primary in Lebanon)
- 🏢 Supports all local business types
- 📶 Works offline (frontend demo mode)

---

## 📄 License

MIT License — Feel free to use, modify, and distribute.

---

**Built with ❤️ for Lebanese businesses**
