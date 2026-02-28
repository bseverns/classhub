# JSON API Reference

## Summary

ClassHub exposes a headless JSON API for mobile and programmatic clients.
All endpoints live under `/api/v1/` and return `application/json` with
`Cache-Control: no-store, private` headers.

## What to do now

1. Use the [Authentication](#authentication) section to understand how to
   obtain and send credentials.
2. Browse the [Student](#student-api) or [Teacher](#teacher-api) endpoint
   tables for the route you need.
3. Check [Rate Limits](#rate-limits) and [Error Codes](#error-codes) for
   operational details.

---

## Authentication

### Student: Bearer Token (recommended for mobile)

Tokens are issued at join time and sent via the `Authorization` header.

```
POST /join
Content-Type: application/json

{"class_code": "ABC123", "display_name": "Ada"}
```

**Response** (200):
```json
{
  "ok": true,
  "return_code": "XYZW",
  "rejoined": false,
  "api_token": "<token>"
}
```

Use the token on all subsequent API requests:

```
GET /api/v1/student/session
Authorization: Bearer <token>
```

**Token properties:**
- Signed with `CLASSHUB_API_TOKEN_SIGNING_KEY` (falls back to `SECRET_KEY`).
- Contains `{sid, cid, epoch}`. Automatically invalidated when a teacher
  resets the class roster (bumps `session_epoch`).
- No hard expiry. Invalidated by roster reset or student deletion.

### Student: Session Cookie (browser fallback)

Browser clients may continue to use session cookies set by `/join`.
The middleware checks bearer tokens first, then falls back to session auth.

### Teacher: Session Cookie + OTP

Teacher endpoints require Django staff authentication with verified OTP.
There is no bearer token flow for teachers (OTP is inherently stateful).

Authenticate via `/admin/login/` → complete 2FA → session cookie is set.

---

## Student API

All student endpoints require authentication (bearer token or session).
Unauthenticated requests return `401`.

### `GET /api/v1/student/session`

Returns the active classroom and student details. Also serves as a
heartbeat (updates `last_seen_at` at most once per minute).

**Response** (200):
```json
{
  "classroom": {
    "id": 1,
    "name": "Intro to Scratch",
    "student_landing_title": "Welcome!",
    "student_landing_message": "Start coding today.",
    "student_landing_hero_url": "/static/hero.jpg"
  },
  "student": {
    "id": 42,
    "display_name": "Ada",
    "return_code": "XYZW"
  },
  "privacy_meta": { ... }
}
```

---

### `GET /api/v1/student/modules`

Returns the accessible curriculum tree for the student's classroom.

**Response** (200):
```json
{
  "ui_density_mode": "standard",
  "modules": [
    {
      "id": 1,
      "title": "Session 1",
      "materials": [
        {
          "id": 10,
          "title": "Upload your project",
          "type": "upload",
          "url": "",
          "body": "",
          "accepted_extensions": ".sb3",
          "max_upload_mb": 50,
          "access": { ... },
          "checklist_items": [],
          "rubric_specs": {}
        }
      ]
    }
  ]
}
```

---

### `GET /api/v1/student/submissions`

Returns the student's historical work and responses, with pagination.

**Query parameters:**

| Param    | Type | Default | Max |
|----------|------|---------|-----|
| `limit`  | int  | 50      | 100 |
| `offset` | int  | 0       | —   |

**Response** (200):
```json
{
  "submissions": [
    {
      "id": 5,
      "material_id": 10,
      "uploaded_at": "2026-02-28T14:30:00Z",
      "original_filename": "project.sb3"
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total": 1
  },
  "submissions_by_material": { ... },
  "material_responses": { ... },
  "gallery_entries_by_material": { ... }
}
```

---

## Teacher API

All teacher endpoints require staff authentication with verified OTP.
Unauthenticated or non-staff requests return `401`. Authorization failures
(e.g., non-manager attempting a write) return `403`.

### Read Endpoints

#### `GET /api/v1/teacher/classes`

Returns all classes accessible to the authenticated teacher.

**Response** (200):
```json
{
  "classes": [
    {
      "id": 1,
      "name": "Intro to Scratch",
      "join_code": "ABC123",
      "is_locked": false,
      "enrollment_mode": "open",
      "student_count": 25,
      "submissions_24h": 12,
      "is_assigned": true
    }
  ]
}
```

---

#### `GET /api/v1/teacher/class/<id>/roster`

Returns the full dashboard context for a class, including students, modules,
materials, submission counts, outcome snapshots, and helper signals.

**Response** (200):
```json
{
  "classroom": {
    "id": 1,
    "name": "Intro to Scratch",
    "join_code": "ABC123",
    "is_locked": false,
    "enrollment_mode": "open"
  },
  "students": [
    {
      "id": 42,
      "display_name": "Ada",
      "last_seen_at": "2026-02-28T14:30:00Z"
    }
  ],
  "student_count": 1,
  "modules": [
    {
      "id": 1,
      "title": "Session 1",
      "materials": [
        { "id": 10, "title": "Upload your project", "type": "upload" }
      ]
    }
  ],
  "submission_counts": { ... },
  "outcome_snapshots": { ... },
  "helper_signals": { ... }
}
```

**Errors:**
- `404` — class not found or not accessible to this teacher.

---

#### `GET /api/v1/teacher/class/<id>/submissions`

Returns paginated submissions for a class, ordered by most recent.

**Query parameters:**

| Param    | Type | Default | Max |
|----------|------|---------|-----|
| `limit`  | int  | 50      | 100 |
| `offset` | int  | 0       | —   |

**Response** (200):
```json
{
  "submissions": [
    {
      "id": 5,
      "student": { "id": 42, "display_name": "Ada" },
      "material": { "id": 10, "title": "Upload your project" },
      "uploaded_at": "2026-02-28T14:30:00Z",
      "original_filename": "project.sb3"
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total": 1
  }
}
```

---

### Write Endpoints

All write endpoints use `POST`, require staff authentication with manager-level
ACL (`staff_can_manage_classroom`), and create an audit log entry.

#### `POST /api/v1/teacher/class/<id>/toggle-lock`

Toggles the `is_locked` status of a class. No request body required.

**Response** (200):
```json
{
  "classroom_id": 1,
  "is_locked": true
}
```

---

#### `POST /api/v1/teacher/class/<id>/rotate-code`

Generates a new unique join code for a class. No request body required.

**Response** (200):
```json
{
  "classroom_id": 1,
  "join_code": "NEW56789"
}
```

---

#### `POST /api/v1/teacher/class/<id>/set-enrollment-mode`

Sets the enrollment mode for a class. Accepts JSON or form-encoded body.

**Request body:**
```json
{
  "enrollment_mode": "open"
}
```

**Valid modes:** `open`, `invite_only`, `closed`

**Response** (200):
```json
{
  "classroom_id": 1,
  "enrollment_mode": "open"
}
```

**Errors:**
- `400` with `{"error": "invalid_enrollment_mode", "valid_modes": ["closed", "invite_only", "open"]}`.

---

## Rate Limits

All API endpoints are rate-limited per client IP.

| Surface          | Limit            | Window  |
|------------------|------------------|---------|
| Student (read)   | 120 requests     | 60 sec  |
| Teacher (read)   | 60 requests      | 60 sec  |
| Teacher (write)  | 30 requests      | 60 sec  |

Exceeding the limit returns `429`:
```json
{ "error": "rate_limited" }
```

---

## Error Codes

All errors follow a consistent shape:

```json
{ "error": "error_code" }
```

| Code                      | HTTP | Meaning |
|---------------------------|------|---------|
| `unauthorized`            | 401  | Missing or invalid credentials |
| `rate_limited`            | 429  | Too many requests |
| `not_found`               | 404  | Class not found or not accessible |
| `forbidden`               | 403  | Insufficient permissions (not a manager) |
| `invalid_enrollment_mode` | 400  | Unknown enrollment mode value |

---

## Cache Headers

All API responses include:
- `Cache-Control: no-store, private`
- `Pragma: no-cache`

This ensures that intermediate proxies and browsers never cache
authenticated API responses.

---

## Testing

The API is covered by 55 automated tests across three test modules:

| Module                  | Tests | Covers |
|-------------------------|-------|--------|
| `test_api_tokens.py`    | 15    | Token utility, middleware bearer resolution, join token issuance |
| `test_api_student.py`   | 13    | Session, modules, submissions endpoints |
| `test_api_teacher.py`   | 27    | All 6 teacher endpoints (read + write) |

Run locally:
```bash
python manage.py test hub.tests.test_api_tokens hub.tests.test_api_student hub.tests.test_api_teacher -v2
```

The smoke check (`scripts/smoke_check.sh`) also probes live API endpoints
using bearer tokens and teacher session cookies.
