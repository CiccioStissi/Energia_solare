from pydantic import BaseModel


class LoginRequest(BaseModel):
    """
    Schema per la richiesta di login (POST /auth/login).

    Contiene le credenziali inviate dal client nel body JSON.
    Pydantic valida automaticamente che entrambi i campi siano presenti
    e di tipo stringa prima che il codice dell'endpoint venga eseguito.
    """
    username: str
    password: str


class RegisterRequest(BaseModel):
    """
    Schema per la registrazione di un nuovo utente (POST /auth/register).

    Identico a LoginRequest nella struttura: username e password scelti dall'utente.
    Il router assegnerà automaticamente il ruolo 'user' al nuovo account.
    """
    username: str
    password: str


class TokenResponse(BaseModel):
    """
    Schema per la risposta del login e della registrazione.

    Restituisce il token JWT generato e il tipo di token (sempre 'bearer').
    Il client deve allegare questo token in tutte le richieste successive
    nell'header: Authorization: Bearer <access_token>
    """
    access_token: str
    token_type: str = "bearer"
