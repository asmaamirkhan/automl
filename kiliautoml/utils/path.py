import os
from datetime import datetime

from kiliautoml.utils.constants import (
    HOME,
    ModelFrameworkT,
    ModelNameT,
    ModelRepositoryT,
)


def makedirs_exist_ok(path_building_function):
    def wrapper(*args, **kwargs):
        res = path_building_function(*args, **kwargs)
        os.makedirs(res, exist_ok=True)
        return res

    return wrapper


JobDirT = str
ModelRepositoryDirT = str
ModelDirT = str
ModelPathT = str


class Path:
    """
    Paths manager class.

    A project is composed of the following nested directories:


    ├── cl0wihlop3rwc0mtj9np28ti2 # project_id
    │   └── DETECTION # job_name
    │       └── ultralytics # model_repository
    │           ├── inference
    │           └── model
    │               └── pytorch
    └── joblib
        ├── kiliautoml
        │   └── utils
        │       └── helpers
        │           └── download_image


    """

    @staticmethod
    @makedirs_exist_ok
    def cache_memoization_dir(project_id, sub_dir):
        cache_path = os.path.join(HOME, project_id, sub_dir)
        return cache_path

    @staticmethod
    @makedirs_exist_ok
    def job_dir(root_dir, project_id, job_name) -> JobDirT:
        return os.path.join(root_dir, project_id, job_name)

    @staticmethod
    @makedirs_exist_ok
    def model_repository_dir(
        root_dir, project_id: str, job_name, model_repository: ModelRepositoryT
    ) -> ModelRepositoryDirT:
        return os.path.join(Path.job_dir(root_dir, project_id, job_name), model_repository)


"""
Once we have the model repository dir, we can create the following nested directories:
"""


class PathUltralytics:
    @staticmethod
    @makedirs_exist_ok
    def inference_dir(root_dir, project_id, job_name, model_repository: ModelRepositoryT):
        return os.path.join(
            Path.model_repository_dir(root_dir, project_id, job_name, model_repository), "inference"
        )


class PathHF:
    @staticmethod
    @makedirs_exist_ok
    def append_model_folder(
        model_repository_dir: ModelRepositoryDirT, model_framework: ModelFrameworkT
    ) -> ModelDirT:
        return os.path.join(
            model_repository_dir,
            "model",
            model_framework,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    @staticmethod
    @makedirs_exist_ok
    def append_training_args_dir(model_dir: ModelDirT):
        return os.path.join(model_dir, "training_args")

    @staticmethod
    @makedirs_exist_ok
    def dataset_dir(model_repository_dir: ModelRepositoryDirT):
        return os.path.join(model_repository_dir, "dataset")


class PathPytorchVision:
    @staticmethod
    @makedirs_exist_ok
    def append_model_dir(
        model_repository_dir: ModelRepositoryDirT,
    ) -> ModelDirT:
        return os.path.join(model_repository_dir, "pytorch", "model")

    @staticmethod
    def append_model_path(model_dir: ModelDirT, model_name: ModelNameT) -> ModelPathT:
        return os.path.join(model_dir, model_name)

    @staticmethod
    @makedirs_exist_ok
    def append_training_args_folder(model_dir: ModelDirT):
        return os.path.join(model_dir, "training_args")
