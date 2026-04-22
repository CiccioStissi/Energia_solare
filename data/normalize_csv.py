"""
Normalizzazione dataset solar_production.csv.

Esegui dalla cartella data/:
  python normalize_csv.py

Operazioni eseguite:
  1. Parsing e validazione formato timestamp
  2. Rimozione righe con timestamp o energy_kwh nulli
  3. Rimozione duplicati su timestamp (mantiene il primo)
  4. Rimozione valori negativi su energy_kwh e radiation_wm2
  5. Arrotondamento a 4 decimali per energy_kwh, 2 per radiation_wm2 e temperature_c
  6. Ordinamento cronologico
  7. Salvataggio in solar_production_normalized.csv
"""

import pandas as pd
from pathlib import Path

INPUT_FILE  = Path(__file__).parent / "solar_production.csv"
OUTPUT_FILE = Path(__file__).parent / "solar_production_normalized.csv"


def main():
    """
    Esegue la pipeline completa di normalizzazione del dataset CSV.

    Legge il file sorgente, applica una serie di controlli e correzioni
    in sequenza, stampa un report di ogni anomalia trovata e salva
    il risultato in un nuovo file normalizzato.

    Le anomalie vengono segnalate con [WARN] ma non bloccano l'esecuzione:
    le righe problematiche vengono semplicemente rimosse.
    """
    print(f"Lettura: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)

    print(f"\n--- STATO INIZIALE ---")
    print(f"  Righe totali     : {len(df)}")
    print(f"  Colonne          : {list(df.columns)}")

    # 1. Normalizza nomi colonne: lowercase e underscore al posto degli spazi
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # 2. Parsing timestamp — i valori non parsabili diventano NaT
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    ts_invalidi = df["timestamp"].isna().sum()
    if ts_invalidi:
        print(f"\n[WARN] {ts_invalidi} righe con timestamp non valido → rimosse")
    df = df.dropna(subset=["timestamp"])

    # 3. Parsing numerico — i valori non convertibili diventano NaN
    df["energy_kwh"]    = pd.to_numeric(df["energy_kwh"],    errors="coerce")
    df["radiation_wm2"] = pd.to_numeric(df["radiation_wm2"], errors="coerce")
    df["temperature_c"] = pd.to_numeric(df["temperature_c"], errors="coerce")

    # 4. Rimozione righe senza energy_kwh (colonna obbligatoria)
    energy_null = df["energy_kwh"].isna().sum()
    if energy_null:
        print(f"[WARN] {energy_null} righe senza energy_kwh → rimosse")
    df = df.dropna(subset=["energy_kwh"])

    # 5. Rimozione valori negativi fisicamente impossibili
    neg_energy = (df["energy_kwh"] < 0).sum()
    neg_rad    = (df["radiation_wm2"].notna() & (df["radiation_wm2"] < 0)).sum()
    if neg_energy:
        print(f"[WARN] {neg_energy} righe con energy_kwh negativo → rimosse")
    if neg_rad:
        print(f"[WARN] {neg_rad} righe con radiation_wm2 negativo → rimosse")
    df = df[df["energy_kwh"] >= 0]
    df = df[df["radiation_wm2"].isna() | (df["radiation_wm2"] >= 0)]

    # 6. Rimozione timestamp duplicati — mantiene il primo occorrenza
    duplicati = df.duplicated(subset=["timestamp"]).sum()
    if duplicati:
        print(f"[WARN] {duplicati} timestamp duplicati → mantenuto il primo")
    df = df.drop_duplicates(subset=["timestamp"], keep="first")

    # 7. Arrotondamento a decimali consistenti
    df["energy_kwh"]    = df["energy_kwh"].round(4)
    df["radiation_wm2"] = df["radiation_wm2"].round(2)
    df["temperature_c"] = df["temperature_c"].round(2)

    # 8. Ordinamento cronologico per timestamp crescente
    df = df.sort_values("timestamp").reset_index(drop=True)

    # 9. Formato timestamp standard ISO senza timezone
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Report finale
    print(f"\n--- STATO FINALE ---")
    print(f"  Righe totali     : {len(df)}")
    print(f"  Periodo          : {df['timestamp'].iloc[0]}  →  {df['timestamp'].iloc[-1]}")
    print(f"  Null radiation   : {df['radiation_wm2'].isna().sum()}")
    print(f"  Null temperature : {df['temperature_c'].isna().sum()}")
    print(f"\n  Anteprima:")
    print(df.head(3).to_string(index=False))

    # Salvataggio del file normalizzato
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n[OK] File normalizzato salvato in: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
