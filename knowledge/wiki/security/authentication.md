---
title: "Authentication and Authorization: OAuth2, JWT, and Secure Access Control Implementation"
author: david-alba
created_at: "2026-05-15T10:30:00Z"
last_modified: "2026-06-02T15:20:00Z"
tags:
  - security
  - authentication
  - best-practices
  - api-design
source_type: manual
confidence_score: 0.96
---

# Authentication & Authorization

## Core Concepts

### Authentication
Verifying the identity of a user or service.
*Question: Are you who you claim to be?*

### Authorization
Determining what authenticated users can do.
*Question: What are you allowed to access?*

## Authentication Methods

### 1. Session-Based Authentication
```
Login → Create Session → Store in Cookie → Validate on Each Request
```

**Pros**: Simple, browser-native  
**Cons**: Requires server-side session storage

### 2. Token-Based Authentication (JWT)
```
Login → Generate Token → Send in Authorization Header
```

**Pros**: Stateless, scalable  
**Cons**: Token size, revocation challenges

### 3. OAuth 2.0
```
User → Application → Auth Provider → Token → Authorized Access
```

**Pros**: Delegated access, industry standard  
**Cons**: Complexity, multiple flows

## JWT Structure

```
Header.Payload.Signature

eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
eyJzdWIiOiIxMjM0NTY3ODkwIn0.
TJVA95OrM7E2cBab30RMHrHDcEfxjoYZgeFONFh7HgQ
```

### Claims
```json
{
  "sub": "user123",
  "name": "John Doe",
  "exp": 1704067200,
  "iat": 1672531200,
  "scopes": ["read:posts", "write:posts"]
}
```

## Authorization Patterns

### Role-Based Access Control (RBAC)
```python
@require_roles("admin", "moderator")
def delete_post(post_id):
    # Only admin or moderator can delete
    pass
```

### Attribute-Based Access Control (ABAC)
```python
def can_delete_post(user, post):
    return (
        user.role == "admin" or
        user.id == post.author_id or
        user.organization == post.organization
    )
```

### Scope-Based (OAuth 2.0)
```
Scopes: read:posts, write:posts, delete:posts
```

## Implementation Example (FastAPI)

```python
from fastapi import FastAPI, Depends, HTTPException
from jose import JWTError, jwt

app = FastAPI()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401)
    return get_user(user_id)

@app.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    return {"message": f"Hello {user.name}"}
```

## Security Best Practices

✓ Use HTTPS only  
✓ Store tokens securely (HttpOnly cookies, secure storage)  
✓ Set appropriate token expiry (short-lived access tokens)  
✓ Implement refresh token rotation  
✓ Use strong encryption algorithms  
✓ Validate all tokens server-side  
✓ Implement rate limiting on login  
✓ Log authentication events  

## Common Vulnerabilities

❌ Storing passwords in plain text  
❌ Tokens without expiry  
❌ Weak token signing algorithms  
❌ Cross-Site Request Forgery (CSRF)  
❌ Cross-Site Scripting (XSS)  
❌ Token leakage in logs  

## Related Topics

- [[wiki/security/encryption.md|Encryption and Data Protection]]
- [[wiki/backend/rest-api-design.md|API Design Security]]
- [[wiki/patterns/circuit-breaker.md|Resilience Patterns]]

## Tools & Libraries

- **PyJWT** - Python JWT handling
- **python-jose** - JOSE implementation
- **Auth0** - Managed authentication
- **Keycloak** - Identity provider
- **AWS IAM** - Cloud identity management

---

**Importance**: Critical  
**Level**: Intermediate to Advanced
