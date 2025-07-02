# TaskFlow Manager Backend API Documentation

This document provides the complete API specification and endpoint summary for the TaskFlow Manager FastAPI backend, including authentication and task management endpoints.

## Overview

- **Base URL:** `/`
- **API Version:** 1.0.0
- **Framework:** FastAPI
- **Authentication:** JWT via OAuth2 Password Bearer; required for all `/tasks` endpoints

---

## Authentication

All endpoints under `/tasks` require a valid JWT token provided as a Bearer token in the `Authorization` header.

### Register

- **Endpoint:** `POST /auth/register`
- **Summary:** Register a new user.
- **Request Body:**
    ```json
    {
      "email": "user@example.com",
      "password": "string (min 6 chars)"
    }
    ```
- **Response:**
    ```json
    {
      "email": "user@example.com"
    }
    ```
- **Status Codes:**
    - `201 Created`: Success
    - `409 Conflict`: User already exists

---

### Login

- **Endpoint:** `POST /auth/login`
- **Summary:** Log in and receive a JWT token.
- **Request (Form):**
    - `username`: user email
    - `password`: password
- **Response:**
    ```json
    {
      "access_token": "string (JWT)",
      "token_type": "bearer"
    }
    ```
- **Status Codes:**
    - `200 OK`: Success
    - `401 Unauthorized`: Invalid credentials

---

### JWT Usage Help

- **Endpoint:** `GET /docs/jwt`
- **Summary:** Guidance on Bearer Token usage for authentication.
- **Response:**
    ```json
    {
      "message": "Use 'Bearer <access_token>' in the Authorization header for all /tasks endpoints."
    }
    ```

---

## Tasks

> All `/tasks` endpoints **require** the `Authorization: Bearer <token>` header.

### List All Tasks

- **Endpoint:** `GET /tasks`
- **Summary:** Get a list of all tasks for the authenticated user.
- **Query Parameters:**
    - `status` (optional): Filter by task status (`pending`, `complete`, etc)
    - `sort_by` (optional): Field to sort (`due_date`, `created_at`, `updated_at`)
- **Response:**
    ```json
    [
      {
        "id": "string",
        "title": "Task title",
        "description": "Details",
        "status": "pending",
        "due_date": "YYYY-MM-DDTHH:MM:SS",
        "created_at": "YYYY-MM-DDTHH:MM:SS",
        "updated_at": "YYYY-MM-DDTHH:MM:SS"
      }
    ]
    ```

---

### Create Task

- **Endpoint:** `POST /tasks`
- **Summary:** Create a new task.
- **Request Body:**
    ```json
    {
      "title": "Task title",
      "description": "Task description",
      "status": "pending",
      "due_date": "YYYY-MM-DDTHH:MM:SS"
    }
    ```
- **Response:**
    ```json
    {
      "id": "string",
      "title": "Task title",
      "description": "Task description",
      "status": "pending",
      "due_date": "YYYY-MM-DDTHH:MM:SS",
      "created_at": "YYYY-MM-DDTHH:MM:SS",
      "updated_at": "YYYY-MM-DDTHH:MM:SS"
    }
    ```
- **Status Codes:**
    - `201 Created`: Success

---

### Update Task

- **Endpoint:** `PUT /tasks/{task_id}`
- **Summary:** Update an existing task (only fields provided).
- **Path Parameter:**
    - `task_id`: Task identifier
- **Request Body:**
    ```json
    {
      "title": "Optional new title",
      "description": "Optional new description",
      "status": "Optional new status",
      "due_date": "YYYY-MM-DDTHH:MM:SS"
    }
    ```
- **Response:** (The updated task, same as the create response)
- **Status Codes:**
    - `200 OK`: Success
    - `404 Not Found`: Task not found for user

---

### Delete Task

- **Endpoint:** `DELETE /tasks/{task_id}`
- **Summary:** Delete a task for the authenticated user.
- **Path Parameter:**
    - `task_id`: Task identifier
- **Response:**
    - `204 No Content` on success
    - `404 Not Found`: Task not found

---

## Health Check

- **Endpoint:** `GET /`
- **Summary:** Service health check.
- **Response:**
    ```json
    {
      "message": "Healthy"
    }
    ```

---

## Pydantic Models

- **UserRegister**
    - email: user email address
    - password: password (min 6 characters)
- **UserPublic**
    - email: user email address
- **Token**
    - access_token: JWT string
    - token_type: "bearer"
- **TaskBase**
    - title: task title
    - description: optional task description
    - status: task status (default: "pending")
    - due_date: optional, ISO8601 date string
- **TaskCreate** (inherits TaskBase)
- **TaskUpdate**
    - Each field is optional (partial update)
- **Task** (extends TaskBase)
    - id: string
    - created_at, updated_at: datetime

---

## OpenAPI (Swagger) Schema

The OpenAPI schema is available from the running backend at:

- [Swagger UI /docs](https://vscode-internal-198-beta.beta01.cloud.kavia.ai:3001/docs)
- [OpenAPI JSON /openapi.json](https://vscode-internal-198-beta.beta01.cloud.kavia.ai:3001/openapi.json)

---

### Security

All task endpoints (`/tasks*`) require JWT authentication (OAuth2PasswordBearer).

**Usage Example (with curl):**

```
curl -H "Authorization: Bearer <YOUR_TOKEN_HERE>" https://your-api-url/tasks
```

---

## Mermaid Diagram: Endpoint Structure

```mermaid
graph TD
    subgraph Authentication
        A[POST /auth/register] --> Ap[User Registration]
        B[POST /auth/login] --> Bp[User Login & Token]
    end
    subgraph Task Management (JWT)
        C[GET /tasks] --> Cp[List Tasks]
        D[POST /tasks] --> Dp[Create Task]
        E[PUT /tasks/{task_id}] --> Ep[Update Task]
        F[DELETE /tasks/{task_id}] --> Fp[Delete Task]
    end
    G[GET /] --> Gp[Health Check]
    H[GET /docs/jwt] --> Hp[JWT Usage]
    %% Auth required for all /tasks*
    style Task\ Management\ (JWT) fill:#f9f,stroke:#333,stroke-width:2px
```

---

## Notes

- Use the `/auth/register` and `/auth/login` endpoints to begin using the API.
- The `/tasks` endpoints are fully protected—**never send passwords or tokens in URLs**.
- The documentation above reflects the backend implementation as of version 1.0.0 in `src/api/main.py`.

---


