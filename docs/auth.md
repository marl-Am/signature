<!-- app/routes/auth.py -->

# 🚦 Flask Authentication Routes Blueprint (`app/routes/auth.py`)

This Python code defines the **authentication routes** for a Flask web application, contained within a **Blueprint** named `auth_bp`. This layer is the **Presentation Layer**—it handles all direct user interaction via HTTP requests, coordinates actions by calling the underlying **`UserService`**, and manages session state. 

[Image of 3-Tier Application Architecture Diagram showing the Presentation, Business Logic, and Data layers]


---

## 🧭 Core Function

The primary role of this file is to map URLs (like `/auth/login`) to specific Python functions (`login()`), handle form submissions, and manage the user session using **Flask-Login**. It enforces the **separation of concerns** by relying on the `UserService` for all sensitive business and security logic.

---

## 🔒 Security Measures (Delegated A07)

The routes are designed to adhere to OWASP A07 (Authentication Failures) by ensuring sensitive logic is delegated and generic error messages are used:

* **Delegation:** All security-critical tasks—like password hashing, brute-force protection (lockout), and logging—are initiated via method calls to `UserService`, ensuring the route file remains clean and focused on routing.
* **A07 Generic Messages:** The `login` and `forgot_password` routes deliberately use **generic error messages** to prevent attackers from using the application's response to determine which user emails are registered (user enumeration).

---

## 💻 Route Handlers

The `auth_bp` blueprint registers the following endpoints, all prefixed with `/auth`:

### 1. `/auth/register` (Registration)

* **Methods:** `GET`, `POST`
* **Action:**
    * **GET:** Renders the sign-up form.
    * **POST:** Collects form data (`email`, `password`, `name`). It calls **`UserService.register_user`** to handle validation and creation.
    * **Result:** If successful, the user is logged in, a success flash message is shown, and the user is redirected. If failed, the error message from the service is displayed.

### 2. `/auth/login` (Login)

* **Methods:** `GET`, `POST`
* **Action:**
    * **GET:** Renders the login form.
    * **POST:** Collects credentials (`email`, `password`, `remember`). It calls **`UserService.authenticate_user`**.
    * **Result:** If successful, **`login_user`** establishes the session and redirects the user. If failed (due to incorrect credentials or lockout), it displays the **generic "Invalid email or password"** flash message.

### 3. `/auth/logout` (Logout)

* **Methods:** `GET`
* **Constraint:** Requires a logged-in user (`@login_required`).
* **Action:** Calls **`logout_user()`** to clear the session cookie and redirects the user to the home page.

### 4. `/auth/forgot-password` (Password Reset Request)

* **Methods:** `GET`, `POST`
* **Action:**
    * **GET:** Renders the forgot password form.
    * **POST:** Collects the `email` and calls **`UserService.initiate_password_reset`**.
    * **Security (A07):** It displays the generic message returned by the service, ensuring consistency and preventing user enumeration.

---

> **Note:** The code includes placeholders (`# TODO`) indicating that the actual implementation for the password reset confirmation (`/reset-password/<token>`) and email verification (`/verify-email/<token>`) routes are still pending and would also rely on methods within the `UserService`.