from pydantic import BaseModel


class UserInfo(BaseModel):
    """
    Schema per esporre le informazioni di un utente verso l'esterno.

    Usato come risposta negli endpoint che restituiscono dati utente.
    NON include hashed_password
    """
    id: int
    username: str
    role: str

    model_config = {"from_attributes": True}
