from sqlalchemy import Column, Integer, String
from database import Base


class User(Base):
    """
    Modello SQLAlchemy per la tabella 'users'.

    Rappresenta un utente dell'applicazione. Ogni utente ha un ruolo che
    determina i permessi sull'API: 'user' può accedere agli endpoint di lettura,
    'admin' può anche importare dati CSV.

    Colonne:
      id              : chiave primaria auto-incrementale
      username        : identificativo univoco dell'utente, indicizzato per query veloci al login
      hashed_password : hash bcrypt della password — la password in chiaro non viene mai salvata
      role            : ruolo dell'utente ('user' o 'admin'), default 'user'
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")  # "user" | "admin"
