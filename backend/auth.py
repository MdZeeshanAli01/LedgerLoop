from dataclasses import dataclass
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .settings import get_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    subject: str
    organization_id: str
    roles: frozenset[str]


@lru_cache
def _jwks_client():
    from jose import jwk
    import json
    from urllib.request import urlopen

    settings = get_settings()
    if not settings.oidc_jwks_url:
        return {}
    with urlopen(settings.oidc_jwks_url, timeout=5) as response:
        keys = json.load(response).get("keys", [])
    return {key["kid"]: jwk.construct(key) for key in keys if key.get("kid")}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> CurrentUser:
    settings = get_settings()
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    if not settings.oidc_issuer or not settings.oidc_audience or not settings.oidc_jwks_url:
        raise HTTPException(status_code=503, detail="OIDC authentication is not configured")
    try:
        header = jwt.get_unverified_header(credentials.credentials)
        key = _jwks_client().get(header.get("kid"))
        if key is None:
            raise JWTError("unknown signing key")
        claims = jwt.decode(
            credentials.credentials,
            key,
            algorithms=["RS256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
        )
    except JWTError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from error
    organization_id = claims.get("custom:organization_id") or claims.get("organization_id")
    if not organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization claim is required")
    roles = claims.get("cognito:groups") or claims.get("roles") or []
    if isinstance(roles, str):
        roles = [roles]
    return CurrentUser(str(claims["sub"]), str(organization_id), frozenset(roles))


def require_roles(*required: str):
    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.roles.intersection(required):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency
