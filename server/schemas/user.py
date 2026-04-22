from pydantic import BaseModel


class UserInfo(BaseModel):
    """
    Schema per esporre le informazioni di un utente verso l'esterno.

    Usato come risposta negli endpoint che restituiscono dati utente.
    NON include hashed_password — le credenziali non devono mai
    uscire dall'API.

    model_config from_attributes=True permette di costruire questo schema
    direttamente da un oggetto SQLAlchemy User senza copiare i campi a mano.
    """
    id: int
    username: str
    role: str

    model_config = {"from_attributes": True}
