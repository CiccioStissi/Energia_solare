# Energia Solare API
  
Utilizzo: **FastAPI** · **SQLAlchemy (async, utilizzato per manipolare database relazionali)** · **PostgreSQL** · **JWT** · **Pydantic v2 (riscrittura da zero delle librerie)** · **pandas** · **RabbitMQ**

---

## Come Funziona

### Architettura generale

Il progetto è composto da tre processi indipendenti che collaborano:

```
┌─────────────────┐      HTTP       ┌─────────────────┐
│  client/        │ ─────────────▶  │  FastAPI server  │
│  test_all.py    │ ◀─────────────  │  (main.py)       │
└─────────────────┘                 └────────┬─────────┘
                                             │ pubblica messaggio
                                             ▼
                                    ┌─────────────────┐
                                    │    RabbitMQ      │
                                    │    (broker)      │
                                    └────────┬─────────┘
                                             │ consuma messaggio
                                             ▼
                                    ┌─────────────────┐
                                    │  csv_worker.py   │
                                    │  (worker)        │
                                    └─────────────────┘
```

- **Client** (`test_all.py`) —> menu interattivo da terminale.
- **Server** (`main.py`) —> API REST FastAPI, gestisce autenticazione, query sui dati e upload CSV.
- **RabbitMQ** —> message broker che riceve i job di importazione CSV dal server e li consegna al worker.
- **Worker** (`csv_worker.py`) —> processo separato che elabora i file CSV in background, aggiorna il database e aggiorna lo stato del job.

---

### Autenticazione (JWT)

Ogni endpoint protetto richiede un token Bearer, il flusso che segue il progetto è:

```
Client                          Server
  │                               │
  │  POST /auth/login             │
  │  { username, password }  ───▶ │  verifica credenziali nel DB
  │                               │  genera JWT firmato con SECRET_KEY
  │  { access_token }        ◀─── │
  │                               │
  │  GET /production/top-hours    │
  │  Authorization: Bearer <token>│
  │                          ───▶ │  decodifica JWT → estrae user + ruolo
  │                               │  autorizza se ruolo corretto
  │  [ risultati ]           ◀─── │
```

Il token JWT contiene: `user_id`, `username`, `role` (`user` o `admin`). Scade dopo `ACCESS_TOKEN_EXPIRE_MINUTES` minuti (configurabile in `.env`). Il client lo salva nel file `.energia_token` e lo riutilizza per tutte le chiamate successive.

---

### Upload CSV asincrono (Message Queue)

L'upload CSV non blocca il server ma usa RabbitMQ per disaccoppiare ricezione ed elaborazione:

```
1. Client invia il file CSV → POST /admin/upload-csv
2. Server salva il file in uploads/, crea un job nel DB (status: "pending")
   e pubblica un messaggio { job_id, file_path } sulla coda RabbitMQ
3. Server risponde subito → 202 Accepted + job_id   (non aspetta l'elaborazione)
4. Worker riceve il messaggio dalla coda
5. Worker aggiorna job → status: "processing"
6. Worker legge il CSV, importa le righe nel DB
7. Worker aggiorna job → status: "done" (o "failed" in caso di errore)
8. Worker invia ACK a RabbitMQ → messaggio rimosso dalla coda
```

Il client può monitorare l'avanzamento con il **polling automatico**:  
ogni 2 secondi chiama `GET /admin/job-status/{job_id}` finché lo status non è `done` o `failed`.

---

### Prima di iniziare:


```bash
pip install -r server/requirements.txt

./start.sh
```

`start.sh` verifica se RabbitMQ è già attivo (porta 5672), poi avvia `uvicorn` e `csv_worker` in background.

**Client** (terminale separato):
```bash
source venv/bin/activate
python client/test_all.py
```

**Swagger UI** (alternativa grafica al client):
```
http://localhost:8000/docs
```

---

### Endpoints disponibili

| Metodo | Endpoint | Ruolo | Descrizione |
|---|---|---|---|
| `POST` | `/auth/register` | pubblico | Registra nuovo utente |
| `POST` | `/auth/login` | pubblico | Login → JWT |
| `GET` | `/production/top-hours` | user/admin | Ore del giorno con più produzione media |
| `GET` | `/production/top-radiation` | user/admin | Ore con più irradiazione media |
| `GET` | `/production/monthly-aggregate` | user/admin | Produzione totale per mese |
| `GET` | `/production/averages` | user/admin | Medie orarie e mensili |
| `GET` | `/production/suggestions` | user/admin | Tutte le analisi in un'unica risposta (Request Batch) |
| `POST` | `/admin/upload-csv` | admin | Upload CSV → job asincrono via RabbitMQ |
| `GET` | `/admin/job-status/{id}` | admin | Stato elaborazione job CSV |

---

## Struttura del Progetto

```
energia_solare/
├── client/
│   ├── test_all.py                     ← client interattivo da terminale
│   └── .energia_token                  ← token JWT salvato dopo il login
├── data/
│   ├── normalize_csv.py
│   ├── solar_production.csv
│   └── solar_production_normalized.csv
├── server/
│   ├── main.py                         ← [Template Method] lifespan: startup → run → shutdown
│   ├── config.py                       ← [Singleton] settings = Settings()
│   ├── database.py                     ← [Singleton] engine · [Factory] async_sessionmaker
│   ├── rabbitmq.py                     ← [Message Queue] connect / publish / close
│   ├── .env                            ← variabili d'ambiente (SECRET_KEY, DB_URL, RABBITMQ_URL, ...)
│   ├── requirements.txt
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt.py                      ← [Token JWT] create_access_token / decode_token
│   │   └── dependencies.py             ← [Token JWT] guard · [DI] · [Chain of Responsibility]
│   │                                      bearer → decode → DB lookup → role check
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── production.py
│   │   └── job.py                      ← ImportJob: traccia stato dei job di importazione CSV
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py                     ← [DTO] LoginRequest · TokenResponse
│   │   ├── user.py                     ← [DTO] UserInfo (nasconde hashed_password)
│   │   ├── production.py               ← [DTO] ProductionRecord · SuggestionsResponse · ...
│   │   └── job.py                      ← [DTO] JobStatusResponse
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                     ← [Remote Facade] POST /auth/login · /register
│   │   ├── production.py               ← [Remote Facade] GET /production/*
│   │   └── admin.py                    ← [Remote Facade] POST /admin/upload-csv (202) · GET /admin/job-status/{id}
│   ├── services/
│   │   ├── __init__.py
│   │   ├── production.py               ← [Service Layer] · [Request Batch] suggestions()
│   │   └── csv_importer.py             ← [Service Layer]
│   ├── workers/
│   │   ├── __init__.py
│   │   └── csv_worker.py               ← [Message Queue] consumer RabbitMQ — elabora i CSV in modo asincrono
│   └── uploads/                        ← file CSV temporanei in attesa di elaborazione
└── moment.txt
```

---

## Pattern Implementati

Pattern richiesti dalla specifica del Prof. Tramontana ("Suggerimenti di Progettazione"):

| Pattern | Descrizione | File |
|---|---|---|
| **Remote Facade** | I router espongono un'API coarse-grained; tutta la logica interna è nascosta nel Service Layer | `routers/auth.py` · `routers/production.py` · `routers/admin.py` |
| **Client Session State** | Lo stato di sessione (user id, ruolo) è portato lato client nel JWT — il server rimane stateless | `auth/jwt.py` · `auth/dependencies.py` |
| **DTO** | I modelli Pydantic disaccoppiano la rappresentazione interna ORM dalla superficie API | `schemas/auth.py` · `schemas/user.py` · `schemas/production.py` |
| **Request Batch** | `suggestions()` aggrega 4 chiamate in un'unica risposta per ridurre i round-trip client/server | `services/production.py` → `suggestions()` |
| **Token JWT** | Ogni richiesta protetta porta un Bearer token che identifica utente, ruolo e sessione | `auth/jwt.py` · `auth/dependencies.py` · tutti i router protetti |
| **Message Queue (RabbitMQ)** | L'upload CSV pubblica un messaggio sulla coda e risponde 202 immediatamente; il worker consuma la coda ed elabora il file in modo asincrono e disaccoppiato | `rabbitmq.py` · `routers/admin.py` · `workers/csv_worker.py` |

---
