from ..provider_interface import Provider
from google.cloud import storage, batch_v1  # type: ignore
from ...structures.project import Project
from ...structures.parameter_study import ParameterStudy
from ...structures.case import InpurtParameter
from openfoamcloud.scripts import fill_file
from openfoamcloud.structures.case import Case, ParameterSet
from datetime import datetime
from uuid import uuid4, UUID
import logging
import os
import glob
import json
import itertools
import string
import random
from typing import Optional


class GoogleCloud(Provider):
    projects_folder = "projects/"
    scripts_folder = "scripts/"
    base_files_folder = "base_files/"
    parameter_studies_folder = "studies/"
    runs_folder = "runs/"
    cases_folder = "cases/"
    fill_file_name = "fill_file.py"
    region = "europe-west6"
    project = "icp-gcp-405410"

    def __init__(self) -> None:
        self.storage_client = storage.Client()
        self.bucket_name = "openfoam-default-bucket"
        self.bucket = self.storage_client.get_bucket(self.bucket_name)

        return

    def initialize(self) -> None:
        blobs = self.storage_client.list_blobs(self.bucket_name)
        blob_names = [blob.name for blob in blobs]

        folders_to_create = [self.projects_folder, self.scripts_folder]

        for folder in folders_to_create:
            if folder in blob_names:
                continue
            print(f"Generating {folder}")
            folder_blob = self.bucket.blob(folder)
            folder_blob.upload_from_string(
                "", content_type="application/x-www-form-urlencoded;charset=UTF-8"
            )

        fill_script_blob = self.bucket.blob(
            os.path.join(self.scripts_folder, self.fill_file_name)
        )

        with open(fill_file.__file__) as f:
            fill_script_blob.upload_from_file(f)

    def get_remote_project_path(self, project_id: UUID) -> str:
        project_path = os.path.join(self.projects_folder, str(project_id))
        return project_path

    def get_remote_parameter_study_path(self, project_id: UUID, study_name: str) -> str:
        parameter_path = os.path.join(
            self.get_remote_project_path(project_id), "studies", study_name
        )
        return parameter_path

    def get_remote_case_path(
        self, project_id: UUID, study_name: str, case_name: str
    ) -> str:
        case_path = os.path.join(
            self.get_remote_parameter_study_path(project_id, study_name),
            self.cases_folder,
            case_name,
        )
        return case_path

    def path_exists(self, path: str) -> bool:
        return self.bucket.blob(path).exists()

    def create_project(self, project_name: str, source_path: str) -> None:
        project_id = uuid4()
        project_path = self.get_remote_project_path(project_name)
        config_path = os.path.join(project_path, "config.json")

        if self.path_exists(config_path):
            raise FileExistsError("Project with this name already exists.")

        source_folder_name = source_path.split("/")[-1]
        target_files_path = os.path.join(
            project_path, self.base_files_folder, source_folder_name
        )

        project_create = Project(
            name=project_name,
            id=project_id,
            created_at=datetime.now(),
            path=project_path,
            files_path=target_files_path,
        )

        print(f"Uploading config to {config_path}")

        project_blob = self.bucket.blob(config_path)
        project_blob.upload_from_string(project_create.model_dump_json(indent=2))

        print(f"Uploading files from {source_path} to {target_files_path}")
        self.upload_recursive(source_path, target_files_path)

    def get_project_by_id(self, id: UUID) -> Project:
        project_path = self.get_remote_project_path(id)
        project_config_blob = self.bucket.blob(
            os.path.join(project_path, "config.json")
        )
        jsons_string = project_config_blob.download_as_string()
        json_dict = json.loads(jsons_string)
        return Project(**json_dict)

    def upload_recursive(self, source_path: str, target_path: str) -> None:
        rel_paths = glob.glob(source_path + "/**", recursive=True)
        for local_file in rel_paths:
            remote_path = os.path.join(
                target_path, os.path.relpath(local_file, source_path)
            )

            if os.path.isfile(local_file):
                logging.info(f"Uploading {local_file}")
                blob = self.bucket.blob(remote_path)
                blob.upload_from_filename(local_file)

    def get_one_level_up_blob(self, prefix: str) -> list[str]:
        blobs = self.bucket.list_blobs(prefix=prefix)
        blob_list = [str(i.name) for i in blobs]
        removed_prefix = [i.replace(prefix, "") for i in blob_list]

        curated_list = []
        for i in removed_prefix:
            if i.startswith("/"):
                curated_list.append(i[1:])
            else:
                curated_list.append(i)

        level_1 = set(i.split("/")[0] for i in curated_list if len(i.split("/")) > 0)
        return [i for i in level_1 if len(i) > 0]

    def get_project_ids(self) -> list[str]:
        return self.get_one_level_up_blob(self.projects_folder)

    def get_parameter_studies_ids(self, project_id: str) -> list[str]:
        path = os.path.join(
            self.projects_folder, project_id, self.parameter_studies_folder
        )
        return self.get_one_level_up_blob(path)

    def get_case_names(self, project_id: str, parameter_study_id: str) -> list[str]:
        path = os.path.join(
            self.projects_folder,
            project_id,
            self.parameter_studies_folder,
            parameter_study_id,
            self.cases_folder,
        )
        one_levels = self.get_one_level_up_blob(path)
        return [i for i in one_levels if i != "config.json"]

    def get_case_run_config(
        self, project_id: str, parameter_study_id: str, case_name: str
    ) -> Case:
        config_path = self.get_remote_case_path(
            project_id, parameter_study_id, case_name
        )
        project_config_blob = self.bucket.blob(os.path.join(config_path, "config.json"))
        jsons_string = project_config_blob.download_as_string()
        json_dict = json.loads(jsons_string)
        return Case(**json_dict)

    def create_parameter_stduy(
        self,
        project_id: UUID,
        name: str,
        run_script: str,
        input_parameters: list[InpurtParameter],
    ) -> None:
        if project_id not in self.get_project_ids():
            raise FileNotFoundError(f"Project {project_id} does not exist.")

        project_path = self.get_remote_project_path(project_id)

        parameter_study_folder = os.path.join(
            project_path, self.parameter_studies_folder, name
        )

        config_path = os.path.join(parameter_study_folder, "config.json")

        if self.path_exists(config_path):
            raise FileExistsError("Parameter study with this name already exists.")

        parameter_names = [i.variable_name for i in input_parameters]
        parameter_values = [i.values for i in input_parameters]
        parameter_paths = [i.path for i in input_parameters]

        cases = []
        for parameter_combination in itertools.product(*parameter_values):
            case_name = "c" + "".join(
                random.choices(string.ascii_lowercase + string.digits, k=12)
            )
            case_path = self.get_remote_case_path(project_id, name, case_name)
            parameter_list = [
                ParameterSet(
                    path=parameter_paths[i],
                    variable_name=parameter_names[i],
                    value=parameter_combination[i],
                )
                for i in range(len(input_parameters))
            ]

            case_create = Case(
                id=case_name,
                path=case_path,
                last_run=None,
                parameter_settings=parameter_list,
                run_script=run_script,
            )

            cases.append(case_create)

            case_blob = self.bucket.blob(os.path.join(case_create.path, "config.json"))
            case_blob.upload_from_string(case_create.model_dump_json(indent=2))

        parameter_study = ParameterStudy(
            name=name, path=parameter_study_folder, cases=cases
        )
        config_blob = self.bucket.blob(config_path)
        config_blob.upload_from_string(parameter_study.model_dump_json(indent=2))

    def delete_case_files(
        self,
        project_id: str,
        parameter_study_name: str,
        case_name: str,
    ):
        parameter_study_path = self.get_remote_parameter_study_path(
            project_id, parameter_study_name
        )
        case_path = self.get_remote_case_path(
            project_id, parameter_study_name, case_name
        )
        content_blobs = self.bucket.list_blobs(prefix=case_path)
        config_path = os.path.join(case_path, "config.json")
        for i in content_blobs:
            if i.name == config_path:
                continue
            i.delete()

    def run_case(
        self,
        project_id: str,
        parameter_study_name: str,
        case_name: str,
        run_script: Optional[str] = None,
        file_logging=True,
    ) -> None:
        client = batch_v1.BatchServiceClient()
        mountpoint = "/mnt/disks/share"
        work_folder = "/home/openfoam/case_files"

        base_path = os.path.join(
            mountpoint, self.get_remote_project_path(project_id), "base_files"
        )

        case_path = os.path.join(
            mountpoint,
            self.get_remote_case_path(project_id, parameter_study_name, case_name),
        )

        run_name = case_name + str(uuid4()).replace("-", "")[:20]
        run_path = os.path.join(case_path, self.runs_folder, run_name)
        log_path = os.path.join(run_path, "log.txt")

        fill_script_path = os.path.join(
            mountpoint, self.scripts_folder, self.fill_file_name
        )

        case_config_path = os.path.join(case_path, "config.json")

        if run_script is None:
            case_config = self.get_case_run_config(
                project_id, parameter_study_name, case_name
            )
            run_script = case_config.run_script

        custom_tasks = [
            # "source /opt/openfoam5/etc/bashrc",
            "source /opt/openfoam11/etc/bashrc",
            "echo 'Run script:'",
            f"echo '{run_script}'",
            "echo $DISPLAY",
            f"mkdir -p {run_path}",
            f"cd {base_path}",
            f"cp -r `ls | head -n 1` {work_folder}",
            f"cd {work_folder}",
            f"echo 'Running python {fill_script_path} {case_config_path} {work_folder}'",
            f"python3 {fill_script_path} {case_config_path} {work_folder}",  #TODO check python version available in container
            run_script,
            f"echo 'copy from {work_folder} to {run_path}'",
            f"echo 'content of {work_folder}'",
            f"ls {work_folder}",
            f"cp -r {work_folder} {run_path}",
        ]

        print(custom_tasks)
        command = " && ".join(custom_tasks)

        # Define what will be done as part of the job.
        runnable = batch_v1.Runnable()
        runnable.container = batch_v1.Runnable.Container()
        # runnable.container.image_uri = "openfoam/openfoam5-paraview54"
        runnable.container.image_uri = "openfoam/openfoam11-paraview510"
        runnable.container.entrypoint = "/bin/bash"
        runnable.container.commands = ["-c", command]

        # Jobs can be divided into tasks. In this case, we have only one task.
        task = batch_v1.TaskSpec()
        task.runnables = [runnable]

        # Specify bucket
        gcs_bucket = batch_v1.GCS()
        gcs_bucket.remote_path = self.bucket_name
        gcs_volume = batch_v1.Volume()
        gcs_volume.gcs = gcs_bucket
        gcs_volume.mount_path = mountpoint
        task.volumes = [gcs_volume]

        # We can specify what resources are requested by each task.
        resources = batch_v1.ComputeResource()
        resources.cpu_milli = 4000  # in milliseconds per cpu-second. This means the task requires 2 whole CPUs.
        resources.memory_mib = 14000  # in MiB
        task.compute_resource = resources

        task.max_retry_count = 0
        task.max_run_duration = "600s"

        # Tasks are grouped inside a job using TaskGroups.
        # Currently, it's possible to have only one task group.
        group = batch_v1.TaskGroup()
        group.task_count = 1
        group.task_spec = task

        # Policies are used to define on what kind of virtual machines the tasks will run on.
        # In this case, we tell the system to use "e2-standard-4" machine type.
        # Read more about machine types here: https://cloud.google.com/compute/docs/machine-types
        policy = batch_v1.AllocationPolicy.InstancePolicy()
        policy.machine_type = "e2-standard-4"
        instances = batch_v1.AllocationPolicy.InstancePolicyOrTemplate()
        instances.policy = policy
        allocation_policy = batch_v1.AllocationPolicy()
        allocation_policy.instances = [instances]

        job = batch_v1.Job()
        job.task_groups = [group]
        job.allocation_policy = allocation_policy
        job.labels = {
            "project": project_id,
            "parameter_study": parameter_study_name,
            "case_name": case_name,
        }

        # We use Cloud Logging as it's an out of the box available option
        job.logs_policy = batch_v1.LogsPolicy()

        if file_logging:
            job.logs_policy.destination = batch_v1.LogsPolicy.Destination.PATH
            job.logs_policy.logs_path = log_path
        else:
            job.logs_policy.destination = batch_v1.LogsPolicy.Destination.CLOUD_LOGGING

        create_request = batch_v1.CreateJobRequest()
        create_request.job = job
        create_request.job_id = run_name
        # The job's parent is the region in which the job will run
        create_request.parent = f"projects/{self.project}/locations/{self.region}"

        return client.create_job(create_request)

    def get_active_runs(self):
        client = batch_v1.BatchServiceClient()
        jobs = client.list_jobs(
            parent=f"projects/{self.project}/locations/{self.region}"
        )
        return [job for job in jobs if job.status.state == 3]

    def get_active_runs_by_parameter_study(
        self, project_id: str, parameter_study_id: str
    ):
        jobs = self.get_active_runs()
        return [
            job
            for job in jobs
            if job.labels["project"] == project_id
            and job.labels["parameter_study"] == parameter_study_id
        ]

    def download_case_files(self):
        pass
