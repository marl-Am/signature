# Signature - System Architecture

This document is living documentation and will be updated as the project progresses.

## Current Implementation Status

**Phase 1: Foundation (In Progress)**
- [x] Project structure established
- [x] Core dependencies installed
- [x] Flask application initialized
- [ ] Database models defined
- [ ] Authentication implemented

**Phase 2: Core Features (Not Started)**
- [ ] Signature generation engine
- [ ] Tracking services (pixel, redirect, assets)
- [ ] Analytics processing

**Phase 3: UI/UX**
- [x] Create Landing Page
- [ ] Finish Landing Page
- [ ] Signature builder interface
- [ ] Dashboard with Chart.js
- [ ] Installation instructions

**Phase 4: Payments (Not Started)**
- [ ] Stripe integration
- [ ] Subscription management
- [ ] Webhook handling



## Project Folder Structure

signature/
│
│
├── app/
│ ├── **init**.py # Flask app factory
│ │
│ ├── config.py  # Configuration classes (Dev, Production, Testing), SQLALCHEMY_DATABASE_URI's, secret key
│ │
│ ├── models/ # Database models (SQLAlchemy), empty
│ │  
│ │
│ ├── routes/ # Blueprint routes (controllers), empty
│ │  
│ │
│ ├── services/ # Business logic layer, empty
│ │  
│ │  
│ │
│ ├── schemas/ # Marshmallow schemas (validation & serialization), empty
│ │  
│ │  
│ │
│ ├── templates/ # Jinja2 HTML templates
│ │ ├── index.html # Landing Page, incomplete just the general set up
│ │ ├── base.html # Base layout (nav, footer, common elements), empty
│ │ ├── auth/  
│ │ │ ├── login.html # empty
│ │ │ ├── register.html # empty
│ │ │ └── forgot_password.html # empty
│ │ ├── dashboard/
│ │ │ ├── index.html # Main dashboard (charts, recent activity), empty
│ │ │ └── analytics.html # Detailed analytics view, empty
│ │ ├── signatures/
│ │ │ ├── create.html # Signature builder form, empty
│ │ │ ├── edit.html # Edit existing signature, empty
│ │ │ ├── preview.html # Live preview component, empty
│ │ │ └── install.html # Installation instructions (Gmail, Outlook, etc.), empty
│ │ ├── subscription/
│ │ │ ├── plans.html # Pricing page, empty
│ │ │ ├── checkout.html # Stripe checkout, empty
│ │ │ └── manage.html # Manage subscription (cancel, update card), empty
│ │ └── email_templates/ # MJML email templates
│ │ ├── welcome.mjml # empty
│ │ ├── trial_ending.mjml # empty
│ │ └── subscription_expired.mjml # empty
│ │
│ ├── static/ # Static assets (CSS, JS, images)
│ │ ├── css/
│ │ │ └── styles.css # Custom CSS, no tailwind yet
│ │ ├── js/ # empty
│ │ │ 
│ │ ├── images/ # empty
│ │ │
│ │ └── favicon.ico
│ │
│ ├── utils/ # Utility functions, empty
│
├── migrations/ # Alembic database migrations, empty
│
├── tests/ # Test suite, empty
│
├── tasks/ # Celery tasks maybe (async operations), empty
│
├── scripts/ # Utility scripts, empty
│
├── docker/ # Docker configuration, empty
│
├── docs/ # Documentation
│ ├── architecture.md # System architecture (THIS DOCUMENT), folder structure
│
├── venv/ # For virtual environment
│
│
├── .env.example # Example environment variables (copy to .env)
├── .env # Environment variables (GITIGNORED - contains secrets)
├── .gitignore # Git ignore rules
├── requirements.txt # Python dependencies (pip freeze)
├── requirements-dev.txt # Development dependencies (pytest, black, etc.)
├── README.md # Project overview, setup instructions
└── wsgi.py # WSGI entry point for production (Gunicorn)
