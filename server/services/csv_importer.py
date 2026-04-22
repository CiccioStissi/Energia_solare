import io
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.production import SolarProduction


class CsvImporter:
    """
    Service per l'importazione di file CSV nella tabella solar_production.

    Il CSV deve avere le colonne: timestamp, energy_kwh, radiation_wm2, temperature_c.
    """

    @classmethod
    async def import_csv(cls, db: AsyncSession, content: bytes) -> int:
        """
        Analizza un file CSV e inserisce i record nel database.

        Flusso completo:
          1. Legge il CSV da bytes con pandas
          2. Normalizza i nomi colonna (lowercase, underscore)
          3. Verifica la presenza delle colonne obbligatorie (timestamp, energy_kwh)
          4. Converte i tipi: timestamp → datetime, numerici → float
          5. Elimina le righe con timestamp o energy_kwh nulli
          6. Inserisce con ON CONFLICT DO NOTHING: i timestamp già presenti
             vengono ignorati silenziosamente (import idempotente)

        Args:
          db: sessione database asincrona.
          content: contenuto grezzo del file CSV in bytes.

        Returns:
          Numero di righe processate (incluse quelle già presenti che vengono skippate).

        Raises:
          ValueError: se mancano le colonne obbligatorie 'timestamp' o 'energy_kwh'.
        """
        df = pd.read_csv(io.BytesIO(content))

        # Normalizza nomi colonne: rimuove spazi, converte in lowercase con underscore
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        # Verifica colonne obbligatorie
        if "timestamp" not in df.columns:
            raise ValueError("CSV manca colonna 'timestamp'")
        if "energy_kwh" not in df.columns:
            raise ValueError("CSV manca colonna 'energy_kwh'")

        # Conversione tipi
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["energy_kwh"] = pd.to_numeric(df["energy_kwh"], errors="coerce")

        # Colonne opzionali: se non presenti nel CSV vengono impostate a None
        for col in ("radiation_wm2", "temperature_c"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            else:
                df[col] = None

        # Rimuove righe con valori obbligatori nulli
        df = df.dropna(subset=["timestamp", "energy_kwh"])

        if df.empty:
            return 0

        records = df[["timestamp", "energy_kwh", "radiation_wm2", "temperature_c"]].to_dict(orient="records")

        # INSERT bulk con ON CONFLICT DO NOTHING sul vincolo unique di timestamp.
        # Se un record con lo stesso timestamp esiste già, viene ignorato silenziosamente
        # senza sollevare errori — rende l'operazione idempotente.
        stmt = pg_insert(SolarProduction).values(records).on_conflict_do_nothing(index_elements=["timestamp"])
        await db.execute(stmt)
        await db.commit()

        return len(records)
