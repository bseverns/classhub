# Class-code auth (student)

## MVP behavior

- Students do not have email/password.
- A student joins a class by entering:
  - Class code
  - Display name
- We create a `StudentIdentity` and store its id in the session cookie.

## Recovery

If cookies are cleared, the student will appear “new” and must re-join.

**Later improvement:** issue a 2-word return code on first join.

## Security notes

- Class codes should be rotatable.
- Joining can be locked per class.
- `/join` should be rate-limited to discourage brute force.
