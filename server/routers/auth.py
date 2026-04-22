from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext

from database import get_db
from models.user import User
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from auth.jwt import create_access_token


router = APIRouter(prefix="/auth", tags=["auth"])

# Contesto bcrypt per hashing e verifica password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Autentica un utente esistente e restituisce un token JWT.

    Cerca l'utente per username nel database e verifica la password
    con bcrypt. In caso di credenziali errate risponde sempre con
    lo stesso messaggio generico (401) per non rivelare se è lo
    username o la password ad essere sbagliata.

    Args:
      request: corpo JSON con username e password (schema LoginRequest).
      db: sessione database iniettata da FastAPI.

    Returns:
      TokenResponse con il JWT da usare nelle richieste successive.

    Raises:
      HTTPException 401: se username non esiste o password errata.
    """
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username o password non corretti",
        )

    # Payload JWT: username (sub) e ruolo per il controllo permessi
    token = create_access_token({"sub": user.username, "role": user.role})
    return TokenResponse(access_token=token)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Registra un nuovo utente con ruolo 'user'.

    Verifica che lo username non sia già in uso prima di creare l'account.
    La password viene hashata con bcrypt prima del salvataggio — mai in chiaro.
    Il ruolo assegnato è sempre 'user': la creazione di admin avviene
    solo tramite il lifespan in main.py.

    Args:
      request: corpo JSON con username e password desiderati (schema RegisterRequest).
      db: sessione database iniettata da FastAPI.

    Returns:
      Messaggio di conferma con lo username creato (HTTP 201 Created).

    Raises:
      HTTPException 409: se lo username è già presente nel database.
    """
    # "admin" è un utente riservato creato automaticamente all'avvio — non registrabile
    if request.username.lower() == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Username riservato: non puoi registrarti come admin",
        )

    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username già in uso",
        )

    hashed = pwd_context.hash(request.password)
    db.add(User(username=request.username, hashed_password=hashed, role="user"))
    await db.commit()
    return {"message": f"Utente '{request.username}' creato con ruolo 'user'"}
