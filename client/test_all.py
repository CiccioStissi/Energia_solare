"""
Test interattivo per Energia Solare API.
"""

import json
import sys
from pathlib import Path
import requests

BASE_URL = "http://localhost:8000"

# Il token viene salvato nella stessa cartella dello script
TOKEN_FILE = Path(__file__).parent / ".energia_token"


TIMEOUT = 10  # secondi — tutte le chiamate HTTP usano questo timeout


def _post(path: str, **kwargs) -> requests.Response:
    """Wrapper POST con timeout di default."""
    return requests.post(f"{BASE_URL}{path}", timeout=TIMEOUT, **kwargs)


def _get(path: str, **kwargs) -> requests.Response:
    """Wrapper GET con timeout di default."""
    return requests.get(f"{BASE_URL}{path}", timeout=TIMEOUT, **kwargs)


def sep(title: str) -> None:
    """
    Stampa un separatore visivo con il titolo dell'operazione.

    Args:
      title: testo da mostrare come intestazione della sezione.
    """
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)


def print_json(data) -> None:
    """
    Stampa un oggetto Python come JSON formattato e leggibile.
    """
    print(json.dumps(data, indent=2, ensure_ascii=False))


def load_token() -> str | None:
    """
    Carica il token JWT salvato su file.
    """
    if not TOKEN_FILE.exists():
        print("[ERRORE] Nessun token trovato. Esegui prima il login (opzione 1).")
        return None
    return TOKEN_FILE.read_text().strip()


def auth_headers() -> dict | None:
    """
    Costruisce l'header Authorization con il token Bearer. (Autenticazioni API)

    Carica il token dal file e lo formatta per le richieste HTTP autenticate.
    Restituisce None se il token non è disponibile.
    """
    token = load_token()
    if not token:
        return None
    return {"Authorization": f"Bearer {token}"}


# ── OPERAZIONI ────────────────────────────────────────────

def op_login():
    """
    Chiede username e password, esegue il login, salva il token e lo verifica automaticamente.

    Invia le credenziali a POST /auth/login. Se il login va a buon fine,
    salva il JWT in .energia_token e chiama immediatamente un endpoint protetto
    per confermare che il token sia valido e l'utente sia autenticato correttamente.
    In caso di errore stampa il codice HTTP e il messaggio del server.
    """
    sep("LOGIN")
    username = input("  Username: ").strip()
    password = input("  Password: ").strip()
    try:
        resp = _post("/auth/login", json={"username": username, "password": password})
    except requests.exceptions.Timeout:
        print("\n[FAIL] Timeout — server non risponde")
        return
    if resp.status_code == 200:
        token = resp.json()["access_token"]
        TOKEN_FILE.write_text(token)
        print(f"\n[OK] Login riuscito. Token salvato in {TOKEN_FILE}")
        print(f"     Token: {token[:40]}...")
    else:
        print(f"\n[FAIL] {resp.status_code}: {resp.text}")


def op_top_hours():
    """
    Chiede il numero di risultati e mostra le ore con più produzione media.

    Chiama GET /production/top-hours?limit=N con il token salvato.
    Mostra le N ore del giorno ordinate per produzione media decrescente.
    """
    sep("TOP HOURS")
    limit = input("  Limit [default 10]: ").strip()
    limit = int(limit) if limit.isdigit() else 10
    headers = auth_headers()
    if not headers:
        return
    resp = _get(f"/production/top-hours?limit={limit}", headers=headers)
    if resp.status_code == 200:
        print(f"\n[OK] Top {limit} ore per produzione:")
        print_json(resp.json())
    else:
        print(f"\n[FAIL] {resp.status_code}: {resp.text}")


def op_top_radiation():
    """
    Chiede il numero di risultati e mostra le ore con più irradiazione media.

    Chiama GET /production/top-radiation?limit=N con il token salvato.
    Mostra le N ore del giorno ordinate per irradiazione solare media decrescente.
    """
    sep("TOP RADIATION")
    limit = input("  Limit [default 10]: ").strip()
    limit = int(limit) if limit.isdigit() else 10
    headers = auth_headers()
    if not headers:
        return
    resp = _get(f"/production/top-radiation?limit={limit}", headers=headers)
    if resp.status_code == 200:
        print(f"\n[OK] Top {limit} ore per irradiazione:")
        print_json(resp.json())
    else:
        print(f"\n[FAIL] {resp.status_code}: {resp.text}")


def op_monthly_aggregate():
    """
    Mostra la produzione totale e l'irradiazione media per ogni mese.

    Chiama GET /production/monthly-aggregate con il token salvato.
    """
    sep("MONTHLY AGGREGATE")
    headers = auth_headers()
    if not headers:
        return
    resp = _get("/production/monthly-aggregate", headers=headers)
    if resp.status_code == 200:
        print("\n[OK] Produzione aggregata per mese:")
        print_json(resp.json())
    else:
        print(f"\n[FAIL] {resp.status_code}: {resp.text}")


def op_averages():
    """
    Mostra le medie di produzione per ora del giorno e per mese.

    Chiama GET /production/averages con il token salvato.
    """
    sep("AVERAGES")
    headers = auth_headers()
    if not headers:
        return
    resp = _get("/production/averages", headers=headers)
    if resp.status_code == 200:
        print("\n[OK] Medie orarie e mensili:")
        print_json(resp.json())
    else:
        print(f"\n[FAIL] {resp.status_code}: {resp.text}")


def op_suggestions():
    """
    Mostra il report completo con tutte le analisi in un'unica chiamata (unico oggetto JSON).
    Chiama GET /production/suggestions con il token salvato.
    """
    sep("Batch")
    headers = auth_headers()
    if not headers:
        return
    resp = _get("/production/suggestions", headers=headers)
    if resp.status_code == 200:
        print("\n[OK] Report completo:")
        print_json(resp.json())
    else:
        print(f"\n[FAIL] {resp.status_code}: {resp.text}")


def op_upload_csv():
    """
    Chiede il percorso del CSV e lo invia al server (solo admin).

    Chiama POST /admin/upload-csv con il token salvato come multipart form.
    Il server risponde subito con 202 Accepted e un job_id: l'elaborazione
    avviene in modo asincrono tramite RabbitMQ e il worker csv_worker.py.
    Dopo l'upload chiede se fare polling automatico sullo stato del job.
    Se l'utente non è admin, il server risponderà con 403 Forbidden.
    """
    sep("UPLOAD CSV (solo admin)")
    path = input("  Percorso file CSV [default ../data/solar_production.csv]: ").strip()
    if not path:
        path = "../data/solar_production.csv"
    csv_path = Path(path)
    if not csv_path.exists():
        print(f"\n[ERRORE] File non trovato: {csv_path}")
        return
    headers = auth_headers()
    if not headers:
        return
    with open(csv_path, "rb") as f:
        resp = _post(
            "/admin/upload-csv",
            headers=headers,
            files={"file": (csv_path.name, f, "text/csv")},
        )
    if resp.status_code == 202:
        data = resp.json()
        job_id = data["job_id"]
        print(f"\n[OK] CSV in coda. job_id: {job_id}")
        print(f"     Usa l'opzione 10 per controllare lo stato del job.")

        poll = input("\n  Fare polling automatico ogni 2s? [s/N]: ").strip().lower()
        if poll == "s":
            import time
            print("  Polling in corso (Ctrl+C per interrompere)...")
            try:
                while True:
                    time.sleep(2)
                    r = _get(f"/admin/job-status/{job_id}", headers=headers)
                    if r.status_code == 200:
                        status_data = r.json()
                        status = status_data["status"]
                        print(f"  Status: {status}", end="")
                        if status == "done":
                            print(f" — {status_data['rows_imported']} righe importate")
                            break
                        elif status == "failed":
                            print(f" — ERRORE: {status_data['error']}")
                            break
                        else:
                            print()
                    else:
                        print(f"  [FAIL] {r.status_code}: {r.text}")
                        break
            except KeyboardInterrupt:
                print("\n  Polling interrotto.")
    else:
        print(f"\n[FAIL] {resp.status_code}: {resp.text}")


def op_job_status():
    """
    Controlla lo stato di un job di importazione CSV tramite job_id.

    Chiama GET /admin/job-status/{job_id} con il token salvato.
    Mostra status, righe importate o messaggio di errore.
    """
    sep("JOB STATUS (solo admin)")
    job_id = input("  job_id: ").strip()
    if not job_id:
        print("\n[ERRORE] job_id obbligatorio.")
        return
    headers = auth_headers()
    if not headers:
        return
    resp = _get(f"/admin/job-status/{job_id}", headers=headers)
    if resp.status_code == 200:
        print("\n[OK] Stato job:")
        print_json(resp.json())
    else:
        print(f"\n[FAIL] {resp.status_code}: {resp.text}")


# ── REGISTRAZIONE ─────────────────────────────────────────

def op_register():
    """
    Registra un nuovo utente con ruolo 'user'.

    Invia username e password a POST /auth/register. La registrazione
    salva solo le credenziali nel database — NON autentica l'utente.
    Per accedere agli endpoint è necessario fare il login (opzione 1)
    dopo la registrazione.
    """
    sep("REGISTRA NUOVO UTENTE")
    username = input("  Username: ").strip()
    password = input("  Password: ").strip()
    resp = _post("/auth/register", json={"username": username, "password": password})
    if resp.status_code == 201:
        print(f"\n[OK] {resp.json()['message']}")
        print("  Utente creato. Usa l'opzione 1 (Login) per autenticarti.")
        # Rimuove il token di eventuali sessioni precedenti: l'utente appena
        # registrato non è ancora autenticato e non deve poter eseguire operazioni.
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
            print("  [INFO] Token precedente rimosso — effettua il login.")
    elif resp.status_code == 403:
        print(f"\n[FAIL] Username riservato — non puoi registrarti come admin")
    elif resp.status_code == 409:
        print(f"\n[WARN] Username già in uso")
    else:
        print(f"\n[FAIL] {resp.status_code}: {resp.text}")


# ── MENU ──────────────────────────────────────────────────

def op_verify_token():
    """
    Verifica manualmente se il token JWT corrente è ancora valido.

    Carica il token salvato e fa una chiamata a GET /production/top-hours?limit=1.
    Risposta 200 → token valido. Risposta 401 → token scaduto o invalido.
    """
    sep("VERIFICA TOKEN")
    token = load_token()
    if not token:
        return
    print(f"\n  Token: {token[:40]}...")
    try:
        resp = _get("/production/top-hours?limit=1", headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 200:
            print("[OK] Token valido — utente autenticato correttamente")
        elif resp.status_code == 401:
            print("[FAIL] Token non valido o scaduto (401)")
        elif resp.status_code == 403:
            print("[FAIL] Token rifiutato (403)")
        else:
            print(f"[FAIL] {resp.status_code}: {resp.text}")
    except requests.exceptions.Timeout:
        print("[FAIL] Timeout — server non risponde")


def main():
    print("\n  Energia Solare API — Test Interattivo")
    print(f"  Server: {BASE_URL}")

    while True:
        print("\n--- MENU ---")
        print("  1. Login")
        print("  2. Registrati")
        print("  3. Verifica token")
        print("  4. Top Hours")
        print("  5. Top Radiation")
        print("  6. Monthly Aggregate")
        print("  7. Averages")
        print("  8. Suggestions (batch)")
        print("  9. Upload CSV (admin)")
        print(" 10. Job Status (admin)")
        print("  0. Esci")

        scelta = input("\nScelta: ").strip()

        if scelta == "0":
            print("Uscita.")
            sys.exit(0)
        elif scelta == "1":
            op_login()
        elif scelta == "2":
            op_register()
        elif scelta == "3":
            op_verify_token()
        elif scelta == "4":
            op_top_hours()
        elif scelta == "5":
            op_top_radiation()
        elif scelta == "6":
            op_monthly_aggregate()
        elif scelta == "7":
            op_averages()
        elif scelta == "8":
            op_suggestions()
        elif scelta == "9":
            op_upload_csv()
        elif scelta == "10":
            op_job_status()
        else:
            print("[ERRORE] Scelta non valida.")


if __name__ == "__main__":
    main()
