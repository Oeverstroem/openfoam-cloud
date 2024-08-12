from pydantic import BaseModel
from openfoamcloud.structures.case import Case


class ParameterStudy(BaseModel):
    name: str
    path: str
    cases: list[Case]
