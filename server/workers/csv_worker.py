"""
Worker RabbitMQ per l'importazione asincrona di file CSV.

Processo standalone che gira separato da FastAPI.
Avvio:  cd server && python -m workers.csv_worker

Flusso per ogni messaggio ricevuto:
  1. Legge il messaggio JSON dalla coda 'csv_import'
  2. Aggiorna il job su DB a status='processing'
  3. Legge il file CSV dalla cartella uploads/
  4. Chiama CsvImporter.import_csv()
  5. Aggiorna il job a status='done' con il numero di righe importate
     oppure a status='failed' con il messaggio di errore
  6. Invia l'ack a RabbitMQ — il messaggio viene rimosso dalla coda

Se il worker crasha prima dell'ack (step 6), RabbitMQ riconsegna
il messaggio automaticamente a un altro consumer (o allo stesso al riavvio).
L'operazione è idempotente grazie a ON CONFLICT DO NOTHING nel CsvImporter.
"""

import asyncio
import json
import sys
from pathlib import Path

import aio_pika
from sqlalchemy import select

# Aggiunge la cartella server/ al path per poter importare i moduli locali
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from database import SessionLocal
from models.job import ImportJob
from services.csv_importer import CsvImporter
from rabbitmq import CSV_IMPORT_QUEUE

UPLOADS_DIR = Path(__file__).parent.parent / "uploads"


async def process_message(message: aio_pika.IncomingMessage) -> None:
    """
    Callback eseguita per ogni messaggio ricevuto dalla coda.

    Riceve il messaggio, aggiorna il job su DB, elabora il CSV e
    invia l'ack solo a elaborazione completata (at-least-once delivery).

    Args:
      message: messaggio aio-pika con body JSON contenente job_id e file_path.
    """
    async with message.process(requeue=True):
        body = json.loads(message.body.decode())
        job_id: str = body["job_id"]
        file_path = Path(body["file_path"])

        print(f"[WORKER] Job ricevuto: {job_id} — file: {file_path.name}")

        async with SessionLocal() as db:
            # Recupera il job dal DB
            result = await db.execute(select(ImportJob).where(ImportJob.id == job_id))
            job = result.scalar_one_or_none()

            if job is None:
                print(f"[WORKER] Job {job_id} non trovato nel DB — scarto il messaggio")
                return

            # Aggiorna status a 'processing'
            job.status = "processing"
            await db.commit()

            try:
                csv_bytes = file_path.read_bytes()
                rows = await CsvImporter.import_csv(db, csv_bytes)

                job.status = "done"
                job.rows_imported = rows
                print(f"[WORKER] Job {job_id} completato — {rows} righe importate")

            except Exception as exc:
                job.status = "failed"
                job.error = str(exc)
                print(f"[WORKER] Job {job_id} fallito — {exc}")

            finally:
                await db.commit()
                # Pulizia: rimuove il file temporaneo dopo l'elaborazione
                if file_path.exists():
                    file_path.unlink()


async def main() -> None:
    """
    Entry point del worker: connette a RabbitMQ e avvia il consume loop.

    Il worker rimane in ascolto indefinitamente sulla coda CSV_IMPORT_QUEUE.
    Ogni messaggio viene processato da process_message() in modo asincrono.
    """
    print(f"[WORKER] Connessione a RabbitMQ: {settings.RABBITMQ_URL}")
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)  # un CSV alla volta per worker

        queue = await channel.declare_queue(CSV_IMPORT_QUEUE, durable=True)
        print(f"[WORKER] In ascolto sulla coda '{CSV_IMPORT_QUEUE}' — Ctrl+C per uscire")

        await queue.consume(process_message)
        await asyncio.Future()  # blocca indefinitamente


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[WORKER] Arresto.")
