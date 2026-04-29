from datetime import datetime
from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    """
    DTO per la risposta di GET /admin/job-status/{job_id}.

    Espone lo stato corrente di un job di importazione CSV senza
    rivelare dettagli interni come il percorso del file sul server.
    """

    id: str
    filename: str
    status: str          
    rows_imported: int | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
