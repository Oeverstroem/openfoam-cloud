from abc import ABC, abstractmethod
from ..structures.case import Case, InpurtParameter
from ..structures.project import Project
from uuid import UUID


class Provider(ABC):
    @abstractmethod
    def create_project(self, project_name: str, files_path: str) -> None:
        "Create Project and return project id"
        pass

    @abstractmethod
    def get_project_ids(self) -> list[str]:
        "Return list of all project ids"
        pass

    @abstractmethod
    def run_case(
        self, project_id: str, parameter_study_name: str, case_name: str
    ) -> None:
        pass

    @abstractmethod
    def create_parameter_stduy(
        self, project_id: UUID, name: str, input_parameters: list[InpurtParameter]
    ) -> None:
        pass

    @abstractmethod
    def get_project_by_id(self, id: UUID) -> Project:
        pass

    @abstractmethod
    def get_parameter_studies_ids(self, project_id: str) -> list[str]:
        pass

    @abstractmethod
    def get_case_names(self, project_id: str, parameter_study_id: str) -> list[str]:
        pass
