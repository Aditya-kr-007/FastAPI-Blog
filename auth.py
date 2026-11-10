import hashlib
import secrets
from jose import jwt,JWTError
from datetime import datetime,timedelta,timezone
from fastapi import HTTPException,Depends
from fastapi.security import OAuth2PasswordBearer

from config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, ADMIN_USERNAME
ALGORITH = "HS256"

oauth2_schema = OAuth2PasswordBearer(tokenUrl="login")

#token create
def create_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc)+ timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITH)


def verify_token(token: str = Depends(oauth2_schema)):
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITH])
        if not payload.get("sub") or payload.get("kind") not in ("admin", "user") or "exp" not in payload:
            raise JWTError("Invalid subject or expiration")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Your session expired. Please sign in again.", headers={"WWW-Authenticate": "Bearer"})


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000)
    return f"pbkdf2_sha256$600000${salt}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt, expected = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
        return secrets.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError):
        return False

