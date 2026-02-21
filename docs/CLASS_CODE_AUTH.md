# Class-code auth (student)

## MVP behavior

- Students do not have email/password.
- A student joins a class by entering:
  - Class code
  - Display name
- On first join, we create a `StudentIdentity`, issue a short `return_code`, and store
  the student id in the session cookie.
- Rejoin from the same browser/device can reclaim identity automatically when class code
  + display name match a valid signed device hint cookie.
- Rejoin from a different browser/device requires class code + display name + `return_code`.

## Recovery

If cookies are cleared, the student can rejoin using the same class code and their
return code.

## Security notes

- Class codes should be rotatable.
- Joining can be locked per class.
- `/join` should be rate-limited to discourage brute force.

## Join flow (Map D1)

```mermaid
sequenceDiagram
  participant B as Browser
  participant MW as Middleware
  participant V as student.join_class
  participant DB as Postgres
  participant R as Redis/cache

  B->>MW: POST /join (class_code, display_name)
  MW->>V: request (site mode + session guardrails)
  V->>R: rate limit check (fail-open on cache issues)
  V->>DB: lookup Class by join code
  V->>DB: create/update StudentIdentity + session binding
  V->>DB: write StudentEvent (details minimized)
  V->>B: JSON (return_code) + Cache-Control: no-store
```
