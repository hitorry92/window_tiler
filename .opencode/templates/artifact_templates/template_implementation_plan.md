# Goal: Add User Authentication via JWT

*This document details the technical plan for creating a new, secure `/api/v1/login` endpoint using JSON Web Tokens (JWT) to authenticate users.*

## User Review Required
> [!IMPORTANT]
> This plan involves security-critical components. Please review the chosen libraries, token structure, and expiration policy. Approval is required before implementation begins.

## Proposed Changes

### `src/services/auth.service.js` [NEW]
- **Role**: A new service to handle all authentication-related logic, such as password hashing, token generation, and token verification.
- **Key Functions**:
    - `async login(email, password)`
    - `async verifyToken(token)`

### `src/routes/api/v1/auth.router.js` [NEW]
- **Role**: A new router to define authentication-related API endpoints.
- **Endpoints**:
    - `POST /login`: Accepts user credentials and returns a JWT.

### `src/models/user.model.js` [MODIFY]
- **Change**: Add a `comparePassword` method to the user schema for secure password verification using `bcrypt`.

### `src/middleware/auth.middleware.js` [NEW]
- **Role**: Middleware to protect routes by verifying the JWT from the `Authorization` header.

## Verification Plan

### Automated Tests
- **Command**: `npm test -- --testPathPattern=auth.service.test.js`
- **Scope**: Unit tests will be created for `auth.service.js` to cover successful login, failed login (wrong password), and token generation logic.

### Manual Verification
- **Scenario**:
    1.  Use a REST client (like Postman) to send a `POST` request to `/api/v1/login` with correct credentials.
    2.  **Expected Result**: Receive a JSON response containing a `token`.
    3.  Send a `GET` request to a protected route (e.g., `/api/v1/profile`) with the `Authorization: Bearer <token>` header.
    4.  **Expected Result**: Receive a `200 OK` response with profile data.
