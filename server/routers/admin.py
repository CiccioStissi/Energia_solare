import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from auth.dependencies import require_admin
from models.user import User
from models.job import ImportJob
from schemas.job import JobStatusResponse
import rabbitmq

router = APIRouter(prefix="/admin", tags=["admin"])

UPLOADS_DIR = Path(__file__).parent.parent / "uploads"


@router.post("/upload-csv", status_code=202)
async def upload_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Accetta un file CSV e lo mette in coda per l'importazione asincrona.

    Invece di elaborare il CSV direttamente (operazione bloccante), salva
    il file su disco, crea un record ImportJob sul DB e pubblica un messaggio
    sulla coda RabbitMQ 'csv_import'. Risponde subito con 202 Accepted e il
    job_id per il polling dello stato tramite GET /admin/job-status/{job_id}.

    Il worker (workers/csv_worker.py) legge il messaggio dalla coda,
    elabora il CSV e aggiorna lo status del job.

    Args:
      file: file CSV caricato come multipart/form-data.
      db: sessione database.
      current_user: deve avere ruolo 'admin'.

    Returns:
      job_id e status 'queued' (HTTP 202 Accepted).

    Raises:
      HTTPException 400: se il file non ha estensione .csv.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo file .csv accettati")

    job_id = str(uuid.uuid4())
    UPLOADS_DIR.mkdir(exist_ok=True)
    file_path = UPLOADS_DIR / f"{job_id}.csv"

    content = await file.read()
    file_path.write_bytes(content)

    job = ImportJob(id=job_id, filename=file.filename, status="queued")
    db.add(job)
    await db.commit()

    await rabbitmq.publish(
        rabbitmq.CSV_IMPORT_QUEUE,
        {"job_id": job_id, "file_path": str(file_path)},
    )

    return {"job_id": job_id, "status": "queued", "filename": file.filename}


@router.get("/job-status/{job_id}", response_model=JobStatusResponse)
async def job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Restituisce lo stato corrente di un job di importazione CSV.

    Permette all'admin di fare polling dopo aver caricato un CSV con
    POST /admin/upload-csv. Lo status passa da 'queued' → 'processing'
    → 'done' (con rows_imported) oppure → 'failed' (con error).
    """
    result = await db.execute(select(ImportJob).where(ImportJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job non trovato")
    return job
