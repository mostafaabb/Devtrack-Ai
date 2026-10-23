# DevTrack AI — AI-Powered Business Operations Platform

**Bringing customer communication, business operations, and AI-assisted workflows into one platform.**

DevTrack AI is a business operations platform designed to help businesses manage customer conversations and everyday activities from a shared dashboard. It combines AI-assisted communication with tools for handling customers, orders, bookings, products, documents, and business analytics.

I built this project around a practical question: how can AI become part of a business's daily workflow instead of being limited to a standalone chat interface?

The project explores how AI services, a backend API, a database, and a web dashboard can work together to support different business operations.

## What It Does

DevTrack AI brings together several workflows that businesses commonly manage across separate tools.

- **AI-assisted customer communication** — process customer messages and generate responses using the configured Gemini integration.
- **Customer management** — maintain customer information and conversation history.
- **Order management** — support order creation and tracking through the available application workflows.
- **Bookings and appointments** — manage booking-related information through the dashboard and API.
- **Product and service management** — organize business offerings.
- **Knowledge-base integration** — retrieve relevant information from uploaded documents to support AI responses.
- **Workflow automation** — define supported rules for automating parts of business operations.
- **Analytics dashboard** — review business activity and available analytics, including AI-generated insights.
- **Embeddable chat widget** — provide a website chat interface connected to the platform.
- **Industry-specific modules** — organize functionality for supported business types, including restaurants, hotels, retail, clinics, and delivery.

The repository also contains WhatsApp-related integration work. Check the current implementation before treating WhatsApp messaging as a fully operational, production-ready integration.

## How the AI Workflow Works

The AI component is designed to do more than generate a reply to a message.

At a high level, the workflow can involve:

1. Receiving a customer message through a supported application endpoint.
2. Identifying the message's intent, such as a question, order, booking, or complaint.
3. Analyzing the message and determining the appropriate response or supported action.
4. Retrieving relevant information from the configured document knowledge base when needed.
5. Using Gemini to assist with the response.
6. Connecting the result to the relevant business workflow, where implemented.

This design explores how AI can be connected to application logic and business data rather than operating independently of the rest of the system.

## Technology Stack

| Area | Technology |
|---|---|
| Backend API | Python, FastAPI |
| AI integration | Google Gemini API |
| Database | PostgreSQL |
| Database access | SQLAlchemy |
| Database migrations | Alembic |
| Authentication | JWT-based authentication |
| Frontend | HTML, CSS, JavaScript |
| Document retrieval | Retrieval-Augmented Generation (RAG), FAISS |
| Background processing | Celery |
| Caching and supporting services | Redis |
| Containerization | Docker, Docker Compose |
| Testing | pytest and API test scripts |

The repository's dependency files and application configuration should be used to confirm exact versions and which services are required for a particular setup.

## Application Architecture

The project separates the main application responsibilities into several areas.

- **API layer:** handles authentication, business operations, conversations, and other application endpoints.
- **Core configuration and security:** manages application settings and authentication-related functionality.
- **Data models and schemas:** define the structures used to represent and validate application data.
- **Service layer:** contains business logic for AI integration, document retrieval, and workflow automation.
- **Background workers:** provide a place for tasks that run outside the main request-response cycle.
- **Frontend dashboard:** provides the interface for interacting with the platform's business features.
- **Chat widget:** offers an embeddable interface for supported website communication workflows.

This separation helps keep API handling, business logic, AI-related operations, and the user interface organized as the application evolves.

## Getting Started

### Prerequisites

For the documented local setup, prepare:

- Python 3.11 or later
- PostgreSQL 15 or a compatible configured database
- Redis 7 or a compatible configured service
- Git
- A Google Gemini API key for AI features

Docker and Docker Compose can be used if you prefer the containerized setup.

### 1. Clone the repository

```bash
git clone https://github.com/mostafaabb/Devtrack-Ai.git
cd Devtrack-Ai
```

### 2. Create a Python virtual environment

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the Python environment's interpreter directly or follow the relevant Python documentation for your local execution policy.

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and configure the required database connection, Redis connection, Gemini API key, authentication secret, and other settings required by the application.

Use strong, unique secrets for local and production environments. Do not commit your populated `.env` file.

### 5. Start the supporting services

Make sure PostgreSQL and Redis are running and that the connection settings in `.env` match your local environment.

### 6. Start the API

From the repository root, run:

```bash
uvicorn app.main:app --reload --port 8000
```

If the configured application starts successfully, the API documentation should be available at:

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

The frontend dashboard and supporting services may require additional configuration. Follow the repository's Docker Compose files and application settings if your local setup differs.

## Configuration

The environment example documents the settings used by the application. Depending on your setup, these include:

- `DATABASE_URL` — PostgreSQL connection
- `REDIS_URL` — Redis connection
- `GEMINI_API_KEY` — Gemini API access
- `JWT_SECRET_KEY` — authentication token signing
- `JWT_EXPIRATION_MINUTES` — token lifetime
- `CORS_ORIGINS` — allowed application origins
- `MAX_UPLOAD_SIZE_MB` — document upload size limit

Use the actual `.env.example` file as the source of truth, and verify required settings before running the application.

## API Documentation

When the backend is running, the generated API documentation allows you to explore available endpoints and inspect request and response schemas.

The documented API areas include:

- Authentication
- Business configuration
- Customer conversations
- Customer management
- Orders and bookings
- Products
- Document uploads
- Workflow rules
- Analytics
- Public chat widget interactions

For exact paths, HTTP methods, request bodies, and authentication requirements, use the running API documentation rather than relying on a static list that may become outdated.

## Security Considerations

The application includes authentication, input validation, and database-related security mechanisms. A deployment should also be reviewed for:

- Secure secret management
- Correct access controls and business-data isolation
- Restricted CORS origins
- HTTPS and secure cookie or token handling where applicable
- Safe document upload and processing
- Proper handling of third-party AI credentials
- Production database and Redis access restrictions

These are important considerations for any platform that handles customer conversations and business information. Their effectiveness depends on the current configuration and implementation.

## What I Learned

Building DevTrack AI has given me a way to work across several areas of full-stack development in one project.

The main challenges include connecting an AI service to real application workflows, organizing business data, designing API boundaries, handling environment configuration, and making different features accessible through a single dashboard.

It has also encouraged me to think about where AI is useful in a business process—and where ordinary application logic is the better choice.

## Project Status

DevTrack AI is an evolving project. The available functionality, integrations, and setup requirements should be verified against the current source code and configuration before deployment.

## Author

**Mostafa Borshalli** — Full-Stack Developer

- Portfolio: https://mostafa-portfolio-black.vercel.app/
- GitHub: https://github.com/mostafaabb
- LinkedIn: https://linkedin.com/in/mostafa-borshalli-7a152a327
