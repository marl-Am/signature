<!-- app/services/user_service.py -->
# ⚙️ User Service: Authentication and Business Logic

This Python code defines the **`UserService`** class, which acts as the **service layer** (or business logic layer) for all user-related operations, including **registration, authentication, and password management**. It isolates the core logic from the user interface and database access code, primarily interacting with the secure **`User` model** (which contains the database details).

The service is highly focused on **OWASP Top 10** security, ensuring strong enforcement of security policies before interacting with the database.

---

## 🛡️ OWASP Top 10 Security Focus

The service class actively implements and enforces security policies related to authentication, cryptography, and logging:

| OWASP ID | Risk | Implementation in Service Layer |
| :--- | :--- | :--- |
| **A07** | **Authentication Failures** | **Password Strength Enforcement:** `validate_password` rigorously checks for length (min. 8), and the presence of uppercase, lowercase, digit, and special characters. |
| **A07** | **Authentication Failures** | **Account Lockout Management:** The `authenticate_user` method checks the user's lockout status (`user.is_locked()`) and calls the `user.record_failed_login()` method on password mismatch. |
| **A04** | **Cryptographic Failures** | Ensures **passwords are never stored in plaintext** by calling `user.set_password(password)` during registration, delegating the secure hashing (e.g., scrypt/bcrypt) to the `User` model. |
| **A09** | **Logging & Monitoring** | The `authenticate_user` method tracks and records the login state (success or failure) along with the client's **IP address** (`request.remote_addr`). |
| **A07** | **Security Through Obscurity** | In `initiate_password_reset`, the service always returns a generic success message, regardless of whether the email exists. This prevents attackers from enumerating valid usernames (emails). |

---

## 🛠️ Key Functionality (Methods)

The service provides several static methods to handle the main user lifecycle actions:

### 1. Validation and Helper Methods

* `validate_password(password: str)`: Enforces the mandatory password complexity requirements using a regular expression. Returns a tuple indicating success and an error message if validation fails.
* `validate_email(email: str)`: Checks that the provided email string matches a standard email format.

### 2. User Registration

* `register_user(email, password, name)`:
    * Performs **validation checks** (email format, password strength).
    * Checks the database to prevent **duplicate email** registration.
    * Creates a new `User` object, calls `user.set_password(password)` (A04), and sets an initial **14-day trial period**.
    * Commits the new user to the database.

### 3. User Authentication

* `authenticate_user(email, password)`:
    * Retrieves the user by email.
    * **A07 Lockout Check:** Immediately denies login if the account is currently locked.
    * **Password Verification:** Compares the provided password to the hash using `user.check_password(password)`.
    * **Failure Handling:** If authentication fails, it calls `user.record_failed_login()` to increment the counter, potentially leading to a lockout.
    * **Success Handling (A09):** If successful, it calls `user.record_successful_login()` to reset the failure counter and record the login time and **IP address**.

### 4. Password Management

* `initiate_password_reset(email)`: Finds the user and calls `user.generate_password_reset_token()`. It sends the reset instruction email, carefully hiding whether the email exists for security.
* `reset_password(token, new_password)`: Validates the new password, finds the user by the token, and calls the secure `user.reset_password()` method on the model to set the new hash and clear the token.
* `change_password(user, current_password, new_password)`: Allows an authenticated user to change their password by first verifying the `current_password` and validating the `new_password` before setting the new hash.

### 5. Utility

* `verify_email(token)`: Confirms the user's email address using a verification token.
* `get_user_by_id(user_id)` and `get_user_by_email(email)`: Simple helper methods for retrieving user objects from the database.