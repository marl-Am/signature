# Signature - Email Signature Generator

## Project Overview

**Type:** Portfolio Architecture Demonstration  
**Status:** Design & Documentation Phase  
**Purpose:** Demonstrate understanding of SaaS architecture, subscription management, and web tracking systems


## The Problem

Solopreneurs and small businesses struggle to create professional email signatures with tracking capabilities.

## The Solution

A web-based signature generator that creates customized, trackable signatures with built-in analytics and a clever retention mechanism (signatures depend on server-hosted assets).

## Key Technical Concepts Demonstrated

1. **SaaS Architecture:** Multi-tier application with clear separation of concerns
2. **Subscription Management:** Stripe integration with real-time validation
3. **Web Tracking:** Pixel tracking and redirect analytics
4. **Retention Mechanics:** Technical dependency creates business value
5. **Security:** OWASP Top 10 compliance integrated from design phase
6. **Type-Safe Programming:** Validation at all layers (Python type hints, Marshmallow schemas)

## Technology Stack

- **Backend:** Flask (Python 3.11+)
- **Database:** PostgreSQL (SQLite for development)
- **ORM:** SQLAlchemy
- **Authentication:** Flask-Login
- **Frontend:** Jinja2 + Tailwind CSS + Alpine.js
- **Charts:** Chart.js
- **Payment:** Stripe
- **Hosting:** Render.com (planned)

## Project Structure
```
signature/
├── app/                 # Main application code
│   ├── models/         # Database models
│   ├── routes/         # API endpoints (Blueprints)
│   ├── services/       # Business logic
│   ├── templates/      # HTML templates
│   └── static/         # CSS, JS, images
├── tests/              # Test suite
├── docs/               # Architecture documentation
└── migrations/         # Database migrations
```

## Setup Instructions

### Prerequisites
- Python 3.11+
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
```

5. **Run development server:**
```bash
   python wsgi.py
```

6. **Open browser:** Navigate to `http://localhost:5000`

## Development Status

- [x] Project initialization
- [x] Basic Flask application
- [x] Environment configuration
- [ ] Database models (User, Signature, TrackingEvent)
- [ ] Authentication system
- [ ] Signature builder UI
- [ ] Tracking implementation
- [ ] Analytics dashboard
- [ ] Stripe integration

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
- **Security-first development:** OWASP compliance from day one
- **Architectural documentation:** Clear communication of complex systems
- **Full-stack capability:** Backend, frontend, database, and infrastructure
- **Product thinking:** Technical features aligned with business value (retention mechanism)

## Contact

[My Name]  
[My Email]  
[My LinkedIn]  
[My Portfolio Site]

## License

This is a portfolio demonstration project. Not intended for commercial use at this.