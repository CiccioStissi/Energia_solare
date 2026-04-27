# Energia Solare API

Servizio REST per l'interrogazione di un dataset di produzione di energia solare.  
Stack: **FastAPI (Framework per la creazione di API)** · **SQLAlchemy (Libreria python per interagire con db relazionali)** · **PostgreSQL (db)** · **JWT** · **Pydantic v2 (gestione dipendenzde e compatibilità FastAPI)** · **pandas**

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

## Pattern Mancanti

Pattern opzionali indicati in "Altri Suggerimenti di Progettazione" non implementati:

| Pattern | Descrizione | Motivazione assenza |
|---|---|---|
| **Timeout** | Limite di tempo su operazioni remote per evitare blocchi indefiniti | Servizio interno LAN, nessuna chiamata a sistemi esterni |
| **Circuit Breaker** | Interrompe automaticamente le chiamate a un servizio non disponibile | Architettura monolitica, nessun microservizio da proteggere |
| **Spring Boot Microservizi** | Decomposizione del server in microservizi indipendenti | Server implementato con FastAPI (Python) |
