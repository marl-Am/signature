# Signature - Email Signature Generator

**Live demo:** https://signature-j0bv.onrender.com/
*(Hosted on Render's free tier — the app spins down after 15 minutes of inactivity, so the first load after idle time may take 30-60 seconds to wake up.)*

## Project Overview

**Type:** Full-Stack SaaS Portfolio Project
**Status:** Live in production, core functionality complete and validated end to end
**Purpose:** Demonstrate SaaS architecture, subscription billing, web tracking, and secure application design in a real, deployed product — not just a design document.

## The Problem

Solopreneurs and small businesses struggle to create professional email signatures with tracking capabilities.

## The Solution

A web-based signature generator that creates customized, trackable signatures with built-in analytics and a retention mechanism (signatures depend on server-hosted assets, so the value compounds the longer a user stays subscribed).

## Key Technical Concepts Demonstrated

1. **SaaS Architecture:** Multi-tier application with clear separation of concerns (routes, services, models)
2. **Subscription Management:** Stripe Checkout and webhook-driven billing, with automatic signature locking on downgrade
3. **Web Tracking:** Pixel-based open tracking and redirect-based click tracking, with bot/scanner filtering to keep analytics accurate
4. **Retention Mechanics:** Technical dependency on hosted assets creates ongoing business value
5. **Security:** OWASP Top 10 practices applied throughout, including a remediated stored XSS finding (see Security section below)
6. **Type-Safe Programming:** Python type hints checked with `ty`, Marshmallow-style validation at the boundary, ownership-based access control enforced consistently across routes

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Flask + Gunicorn (Python 3.13.5) |
| ORM / Migrations | SQLAlchemy + Flask-Migrate |
| Authentication | Flask-Login + Argon2id (`argon2-cffi`) password hashing |
| Frontend | Jinja2 + Tailwind CSS (CDN) + Alpine.js (CDN) |
| Charts | Chart.js |
| Payments | Stripe (Checkout + Webhooks) |
| Transactional email | Brevo (300 emails/day, free tier, permanent) |
| Database (dev/test) | SQLite (in-memory, StaticPool, for tests) |
| Database (prod) | Neon Postgres 18 |
| Hosting | Render.com (Hobby free tier), auto-deploys on push to `main` |
| Testing | pytest — 41 tests, run in CI and locally before every deploy |
| CI | GitHub Actions (`.github/workflows/ci.yml`) |
| Containerization | Docker, scanned with Docker Scout |
| Type checking | `ty` |
| Linting | Ruff |

## Project Structure
```
signature/
├── app/
│   ├── models/          # User, Signature, Analytics
│   ├── routes/          # auth, billing, dashboard, profile, signatures,
│   │                    # subscription, tracking, analytics (Blueprints)
│   ├── services/        # email_service, user_service, signature_service,
│   │                    # analytics_service — business logic layer
│   ├── templates/       # Jinja2 templates, organized by feature area
│   └── static/
├── scripts/              # One-off/maintenance tooling (documented, not auto-run)
├── tests/                # pytest suite (41 tests)
└── migrations/           # Flask-Migrate migration history
```

## Setup Instructions

### Prerequisites
- Python 3.13+
- Git
- Visual Studio Code (or your preferred IDE)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/marl-Am/signature.git
cd signature
```

2. **Create virtual environment:**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. **Configure environment:**
```bash
copy .env.example .env
# Edit .env and set SECRET_KEY
# Leave DATABASE_URL unset for local dev — the app falls back to SQLite
```

5. **Run database migrations:**
```bash
flask db upgrade
```

6. **Run development server:**
```bash
python wsgi.py
```

7. **Open browser:** Navigate to `http://localhost:5000`

### Running tests
```bash
pytest
ruff check .
ty check .
```

## Development Status

- [x] Project initialization and Flask application scaffold
- [x] Database models (User, Signature, TrackingEvent/Analytics)
- [x] Authentication system (Flask-Login + Argon2id)
- [x] Signature builder UI (7 layouts: classic, modern, minimal, ruled, avatar, compact, banner)
- [x] Open/click tracking implementation with bot filtering
- [x] Analytics dashboard
- [x] Stripe integration (Checkout + Webhooks, test mode)
- [x] Deployed to production (Render + Neon Postgres + Brevo)
- [x] End-to-end delivery validated in Gmail (create → copy → paste → send → receive)
- [ ] End-to-end delivery validated in Outlook and Apple Mail
- [ ] Custom domain (currently running on Render's free `*.onrender.com` subdomain by deliberate choice, pending budget)
- [ ] Stripe moved out of test mode (pending business verification, deferred until there's a real onboarding plan)

## Security

Security is treated as a first-class concern rather than an afterthought:

- **Access Control (A01):** Ownership checks enforced consistently on every signature/analytics route — a user can only view or modify their own data.
- **Cryptographic Failures (A02):** Passwords hashed with Argon2id; all traffic served over TLS via Render.
- **Injection (A03):** SQLAlchemy ORM used throughout; no raw string-built queries.
- **Stored XSS (remediated):** A stored XSS vulnerability in the signature HTML generation pipeline was identified, traced to unescaped user input in the server-side HTML builder, and fixed with proper input escaping and URL scheme validation using Python's standard library. Regression coverage for this bug class is being added to the test suite.
- **Dependency & container hygiene:** Docker image scanned with Docker Scout; no fixable critical or high vulnerabilities as of the last scan.
- **CI enforcement:** Every push runs the full pytest suite, Ruff linting, and `ty` type checking before deploy.

## Architecture Documentation

See `docs/architecture.md` for detailed system design, including:
- High-level architecture diagrams
- Component interactions
- Data flow documentation
- Security implementation (OWASP compliance)
- Technology stack rationale

## Why This Project?

This project demonstrates:
- **Systems thinking:** Understanding how technical decisions drive business outcomes
- **Security-first development:** OWASP-aligned practices applied and validated, not just planned
- **Real-world debugging:** Diagnosing and fixing live production incidents post-launch (see `docs/architecture.md` for a written case study of one such incident — a clipboard-serialization bug that only surfaced outside the app itself)
- **Architectural documentation:** Clear communication of complex systems
- **Full-stack capability:** Backend, frontend, database, and infrastructure, all shipped to a real production environment
- **Product thinking:** Technical features aligned with business value (retention mechanism, tiered billing)

## License

This is a portfolio demonstration project. Not intended for commercial use at this time.