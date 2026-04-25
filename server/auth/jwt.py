from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from config import settings


def create_access_token(data: dict) -> str:
    """
    Genera un token JWT firmato con i dati forniti.

    Aggiunge al payload il campo 'exp' con la scadenza calcolata in base
    a settings.ACCESS_TOKEN_EXPIRE_MINUTES. Il token viene firmato con
    SECRET_KEY usando l'algoritmo definito in settings.ALGORITHM (HS256).

    Il payload tipico contiene:
      { "sub": "username", "role": "user"|"admin" }
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Verifica e decodifica un token JWT.

    Controlla la firma con SECRET_KEY e verifica che il token non sia scaduto.
    Se il token è invalido o scaduto, restituisce JWTError (gestito da dependencies.py).
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
