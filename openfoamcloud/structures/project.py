from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class Project(BaseModel):
    id: UUID
    path: str
    created_at: datetime
    files_path: str
    name: str
