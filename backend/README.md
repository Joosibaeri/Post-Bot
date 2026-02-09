# PostBot Backend (FastAPI)

The backend is a FastAPI application implementing clean architecture with route modules, repository pattern, Clerk JWT authentication, and multi-provider AI integration.

## Quick Start (Local)

```bash
# 1. Create virtualenv and install dependencies
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment
cp ../.env.example ../.env  # Edit with your API keys

# 3. Run the API
python app.py
# Or with hot-reload:
uvicorn app:app --reload --port 8000
```

The server starts at [http://localhost:8000](http://localhost:8000).

## Architecture

```
backend/
├── app.py              # FastAPI entry point (~200 lines)
├── core/config.py      # Environment, CORS, templates
├── database/schema.py  # SQLAlchemy table definitions
├── migrations/         # Alembic schema versioning
├── repositories/       # Data access layer (BaseRepository pattern)
├── routes/             # API route modules (8 files)
│   ├── auth.py         # Authentication endpoints
│   ├── feedback.py     # User feedback
│   ├── github.py       # GitHub OAuth + activity scanning
│   ├── linkedin.py     # LinkedIn OAuth
│   ├── payments.py     # Stripe subscriptions
│   ├── posts.py        # Post generation, publishing, scheduling
│   ├── settings.py     # User settings, connection status, usage
│   └── webhooks.py     # Webhook receivers
├── schemas/            # Pydantic request/response models
├── middleware/          # Auth (Clerk JWT) + Request ID tracing
├── dependencies.py     # Dependency injection helpers
└── tests/              # pytest test suite (84+ tests)
```

## Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/templates` | GET | Post templates |
| `/api/settings/{user_id}` | GET | User settings (auth required) |
| `/api/post/generate-preview` | POST | AI-powered post generation |
| `/api/post/publish` | POST | Publish to LinkedIn |
| `/api/post/schedule` | POST | Schedule a future post |
| `/api/github/scan` | POST | Scan GitHub activity |
| `/api/publish/full` | POST | Full publish with image (auth required) |
| `/api/post/bot-stats` | GET | Bot mode historical stats |
| `/api/post/generate-batch` | POST | Batch AI generation for bot mode |
| `/api/connection-status/{user_id}` | GET | LinkedIn/GitHub connection status + persona_complete flag |
| `/docs` | GET | Swagger UI documentation |
| `/openapi.json` | GET | OpenAPI 3.0 spec |

All data endpoints require Clerk JWT authentication via `Authorization: Bearer <token>`.

## AI Providers

| Provider | Model | Tier |
|----------|-------|------|
| Groq | llama-3.3-70b-versatile | Free |
| OpenAI | gpt-4o | Pro |
| Anthropic | claude-3-5-sonnet-20241022 | Pro |
| Mistral | mistral-large-latest | Pro |

## Database

- **Production**: PostgreSQL via asyncpg with configurable connection pooling (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`)
- **Development**: SQLite fallback (auto-created as `dev_database.db`); `init_tables()` runs on startup to ensure schema exists
- **Migrations**: Alembic (`alembic upgrade head` / `alembic revision --autogenerate`)
- **Schema**: SQLAlchemy 2.0 declarative models in `database/schema.py`
- **Health Check**: `/health` endpoint validates DB connectivity, not just HTTP 200

## Recent Changes

- **Environment Validation**: `validate_environment()` at startup warns about missing optional keys, fails fast on required ones
- **Auto Table Creation**: `init_tables()` called during app lifespan startup with ALTER TABLE fallbacks for schema evolution
- **Persona Pipeline**: Auto-refresh learned patterns after successful LinkedIn publish; `persona_complete` flag in connection-status
- **DEV_MODE Gating**: Dev bypass routes require explicit `DEV_MODE=true` environment variable
- **Redis Rate Limiter**: Production rate limiting backed by Redis with in-memory fallback for local dev

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=. --cov-report=term-missing
```

Tests use FastAPI dependency overrides to mock Clerk authentication. See `tests/conftest.py` for fixtures.

## Environment Variables

See the root `.env.example` for all required and optional variables. Key backend variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Production | PostgreSQL connection string |
| `GROQ_API_KEY` | Yes | Default AI provider |
| `ENCRYPTION_KEY` | Production | Fernet key for token encryption |
| `CLERK_ISSUER` | Yes | Clerk JWT issuer URL |
| `LINKEDIN_CLIENT_ID` | Yes | LinkedIn OAuth app |
| `LINKEDIN_CLIENT_SECRET` | Yes | LinkedIn OAuth secret |
| `STRIPE_SECRET_KEY` | Optional | Stripe payments |
