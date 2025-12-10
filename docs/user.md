<!-- app/models/user.py -->
# 🐍 Flask User Model: Security and Features

This document explains the functionality and security implementation of the Python code (`app/models/user.py`), which defines a **User model** for a web application using **Flask-SQLAlchemy** and **Flask-Login**.

The model is designed to manage user authentication, authorization, and subscription data, with a strong emphasis on security by adhering to the **OWASP Top 10: 2025** guidelines.

---

## 🛡️ OWASP Top 10 Security Implementations

The code integrates specific measures to mitigate critical security risks:

| OWASP ID | Risk | Implementation in Code |
| :--- | :--- | :--- |
| **A04** | **Cryptographic Failures** | The `set_password` method uses `generate_password_hash` with **scrypt** (or a similar strong hash) to store passwords securely, preventing storage of plaintext passwords. |
| **A07** | **Authentication Failures** | **Account Lockout:** Implemented via `failed_login_attempts` and `locked_until`. The account is locked for **15 minutes after 5 failed attempts** to prevent brute-force attacks. |
| **A07** | **Authentication Failures** | **Secure Token Management:** Uses time-limited and cryptographically random tokens (`secrets.token_urlsafe`) for **email verification** and **password reset**. |
| **A09** | **Logging & Monitoring** | Records key events, specifically tracking the `last_login_at` and `last_login_ip` for auditing and detecting suspicious activity. |
| **A01** | **Access Control** | Enforced at the data level by linking resources (like `signatures`) directly to the user's `id` via **relationships**. This ensures users can only interact with data they own. |

---

## 🏗️ Core Model Structure and Data Fields

The `User` class inherits from `db.Model` (database representation) and `UserMixin` (Flask-Login compatibility).

### Database Fields

The model defines columns grouped by their function:

* **Identity & Credentials:**
    * `id` (Primary Key), `email` (Unique and Indexed), `name`.
    * `password_hash` (stores the securely hashed password).
* **A07 Status & Security:**
    * `is_active`, `email_verified`.
    * `failed_login_attempts`, `locked_until` (for brute-force protection).
    * `email_verification_token`, `password_reset_token`, `password_reset_expires`.
* **A09 Logging & Audit:**
    * `last_login_at`, `last_login_ip` (stores the last known IP address of a login).
    * `created_at`, `updated_at` (timestamps for record tracking).
* **Business Logic (Subscriptions):**
    * `subscription_status`, `subscription_tier`.
    * Fields for Stripe integration: `stripe_customer_id`, `stripe_subscription_id`, `trial_ends_at`.

### Relationships (A01 Access Control)

* The `signatures` field defines a **one-to-many relationship**, linking the user to all their created signature objects. The `cascade="all, delete-orphan"` setting ensures that if a user is deleted, all their related signatures are also deleted.

---

## 🔑 Key Functionality (Methods)

The methods define the actions and security checks the user object can perform:

### Password Management (A04)

* `set_password(password: str)`: Hashes the provided plaintext password and saves it to `password_hash`. Includes a basic check for password length.
* `check_password(password: str)`: Verifies if a plaintext password matches the stored hash.

### Authentication Flow (A07 & A09)

* `is_locked()`: Checks if the current time is past the `locked_until` time, managing the account lockout state.
* `record_failed_login()`: Increments the counter and **locks the account** if the threshold (5 attempts) is reached.
* `record_successful_login(ip_address: Optional[str])`: Resets the failure counter, clears any lockout, and updates the `last_login_at` and `last_login_ip` (A09).

### Email & Password Tokens (A07)

* **Email Verification:** Methods to `generate_verification_token` and `verify_email`.
* **Password Reset:** Methods to `generate_password_reset_token` (expires after 1 hour) and `reset_password`, which verifies the token before securely setting the new password.

### Subscription Checks (Business Logic)

* `has_active_subscription()`: Returns `True` if the user is `active` or their `trial` period has not expired.
* `can_create_signature()`: Implements feature gating: allows unlimited creation for `pro` tiers but limits `free` users to one signature.

### Utility

* `to_dict()`: Generates a JSON-friendly dictionary of user attributes for API responses, **excluding sensitive data** like tokens and the password hash.