# ADR-0007: Customer sessions use short-lived signed tokens (JWT)

- **Status:** Accepted
- **Date:** 2026-11-17
- **Decided by:** Platform engineer (repository owner)

## Context
After a customer logs in, the payments API must recognise them on every request (balance, history, send money).
The API runs as several identical pods, so any pod must be able to recognise any customer.

## Decision
- On login, the API issues a **JSON Web Token (JWT)** signed with **HS256** and a server-side secret key.
- The token carries only the customer ID (`sub`), issuer, issue time and expiry. **No balances or personal data.**
- Lifetime: **15 minutes** (`JWT_TTL_MINUTES`). The customer logs in again afterwards (no refresh tokens in this proof of concept).
- The browser sends it as `Authorization: Bearer <token>`. Every protected endpoint verifies the signature, issuer and expiry.
- The signing key is a secret:
  - **Locally:** `JWT_SIGNING_KEY` in the git-ignored `.env`.
  - **Azure:** stored in **Key Vault** and read by the payments workload identity, never in code, images or Git.
- Passwords are stored as salted **scrypt** hashes. Login failures return one generic message, so an attacker can't learn which emails exist.

## Alternatives considered
- **Server-side sessions** (session ID in a cookie, session row in the database): can be revoked instantly, but adds a database read on every request.
- **External identity provider** (Entra External ID / Azure AD B2C): the production choice for real customers, but out of scope and budget for this proof of concept.

## Consequences
- ✅ Stateless: any pod can verify a token without a database lookup; scaling out needs no shared session store.
- ✅ Gives Key Vault and workload identity a concrete job in the platform.
- ⚠️ A stolen token is valid until it expires, which is why the lifetime is short. Rotating the signing key logs everyone out.
- ⚠️ All pods must share the same key. A mismatch shows up as `401 Unauthorized` on some requests only.
- 🔁 In production: use an external identity provider, asymmetric signing (RS256/ES256) with key rotation, and HttpOnly cookies or refresh tokens.

## References
- RFC 7519, JSON Web Token: https://datatracker.ietf.org/doc/html/rfc7519
- PyJWT documentation: https://pyjwt.readthedocs.io/
- OWASP Password Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
