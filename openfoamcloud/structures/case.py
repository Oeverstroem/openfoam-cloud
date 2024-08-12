from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional


class ParameterSet(BaseModel):
    path: str
    variable_name: str
    value: str


class Case(BaseModel):
    id: str
    path: str
    last_run: Optional[datetime]
    parameter_settings: list[ParameterSet]
    run_script: str


class InpurtParameter(BaseModel):
    path: str
    variable_name: str
    values: list[Any]
