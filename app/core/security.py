from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(
auto_error=False,
)

def get_current_user(
credentials: HTTPAuthorizationCredentials | None = Depends(
bearer_scheme
),
db: Session = Depends(get_db),
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials.",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )

    # No Authorization header was supplied.
    if credentials is None:
        raise credentials_exception

    # HTTPBearer already parses:
    # Authorization: Bearer <token>
    if credentials.scheme.lower() != "bearer":
        raise credentials_exception

    token = credentials.credentials.strip()

    if not token:
        raise credentials_exception

    try:

        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

    except JWTError:
        raise credentials_exception

    user_id = payload.get("sub")

    if not user_id:
        raise credentials_exception

    # Only access tokens may authenticate API requests.
    token_type = payload.get("type")

    if token_type != "access":
        raise credentials_exception

    user = db.execute(
        select(User).where(
            User.id == str(user_id)
        )
    ).scalar_one_or_none()

    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address is not verified.",
        )

    return user