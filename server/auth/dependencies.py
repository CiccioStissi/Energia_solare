from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from auth.jwt import decode_token
from database import get_db
from models.user import User


bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency che verifica il token JWT e restituisce l'utente autenticato.

    Viene iniettata da FastAPI in tutti gli endpoint che richiedono autenticazione,
    sia per utenti normali che per admin.

    Flusso:
      1. Estrae il token Bearer dall'header Authorization
      2. Chiama decode_token per verificare firma e scadenza
      3. Ricava lo username dal campo 'sub' del payload
      4. Cerca l'utente nel database
      5. Restituisce l'oggetto User se tutto è valido
    """
    token = credentials.credentials
    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
        if not username:
            raise ValueError("sub mancante nel token")
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non valido o scaduto",
        )

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utente non trovato",
        )
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """
    Dependency che restringe l'accesso ai soli utenti con ruolo 'admin'.

    Si appoggia su get_current_user: prima verifica che il token sia valido,
    poi controlla che l'utente abbia il ruolo corretto. È usata esclusivamente
    sull'endpoint POST /admin/upload-csv.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permessi insufficienti: richiesto ruolo admin",
        )
    return user
