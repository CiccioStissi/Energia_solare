from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.dependencies import require_admin
from models.user import User
from services.csv_importer import CsvImporter


router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Importa un file CSV con dati di produzione solare nel database.

    Endpoint riservato esclusivamente agli utenti con ruolo 'admin'.
    Accetta il file come multipart/form-data, ne verifica l'estensione,
    legge il contenuto e lo passa al CsvImporter per il parsing e l'inserimento.

    Il CSV deve contenere almeno le colonne 'timestamp' e 'energy_kwh'
    (o i loro alias riconosciuti — vedi CsvImporter._COL_MAP).
    I record già presenti nel database (stesso timestamp) vengono ignorati
    silenziosamente grazie a ON CONFLICT DO NOTHING.

    Args:
      file: file CSV inviato come multipart form upload.
      db: sessione database.
      current_user: utente admin autenticato (verifica JWT + ruolo admin).

    Returns:
      Dizionario con messaggio di conferma e numero di righe inserite.

    Raises:
      HTTPException 400: se il file non ha estensione .csv.
      HTTPException 422: se il CSV è malformato o mancano colonne obbligatorie.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo file .csv accettati")

    content = await file.read()

    try:
        rows_inserted = await CsvImporter.import_csv(db, content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {"message": f"Importati {rows_inserted} record", "rows": rows_inserted}
