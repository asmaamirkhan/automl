import copy
import os
from typing import Any, List, Optional

import numpy as np
import torch
import torch.backends.cudnn as cudnn
import torch.nn as nn
import torch.utils.data as torch_Data
from cleanlab.filter import find_label_issues
from sklearn.model_selection import StratifiedKFold, train_test_split
from torchvision import datasets
from tqdm import tqdm

from kiliautoml.utils.cleanlab.datasets import (
    get_original_image_dataset,
    prepare_image_dataset,
    separe_holdout_datasets,
)
from kiliautoml.utils.constants import HOME, ModelNameT, ModelRepositoryT
from kiliautoml.utils.download_assets import download_project_image_clean_lab
from kiliautoml.utils.path import ModelDirT, Path, PathPytorchVision
from kiliautoml.utils.pytorchvision.image_classification import (
    get_trained_model_image_classif,
    predict_probabilities,
    set_model_name_image_classification,
    set_model_repository_image_classification,
)


def combine_folds(data_dir, model_dir: ModelDirT, verbose=0, num_classes=10, nb_folds=4, seed=42):
    """
    Method that combines the probabilities from all the holdout sets into a single file
    """
    destination = os.path.join(model_dir, "train_model_intel_pyx.npy")
    if verbose >= 2:
        print()
        print("Combining probabilities. This method will overwrite file: {}".format(destination))
    # Prepare labels
    labels = [label for _, label in datasets.ImageFolder(data_dir).imgs]
    # Initialize pyx array (output of trained network)
    pyx = np.empty((len(labels), num_classes))

    # Split train into train and holdout for each cv_fold.
    kf = StratifiedKFold(n_splits=nb_folds, shuffle=True, random_state=seed)
    for k, (_, cv_holdout_idx) in enumerate(kf.split(range(len(labels)), labels)):
        probs_path = os.path.join(model_dir, f"model_fold_{k}__probs.npy")
        probs = np.load(probs_path)
        pyx[cv_holdout_idx] = probs[:, :num_classes]
    if verbose >= 2:
        print("Writing final predicted probabilities.")
    np.save(destination, pyx)

    if verbose >= 2:
        # Compute overall accuracy
        print("Computing Accuracy.", flush=True)
        acc = sum(np.array(labels) == np.argmax(pyx, axis=1)) / float(len(labels))
        print("Accuracy: {:.25}".format(acc))

    return destination


def single_true(iterable):
    i = iter(iterable)
    return any(i) and not any(i)


def train_and_get_error_image_classification(
    cv_n_folds: Optional[int],
    epochs: int,
    assets: List[Any],
    model_repository: ModelRepositoryT,
    model_name: ModelNameT,
    job_name: str,
    project_id: str,
    api_key: str,
    verbose: int = 0,
    cv_seed: int = 42,
    only_train: bool = False,
    only_predict: bool = False,
):
    """
    Main method that trains the model on the assets that are in data_dir, computes the
    incorrect labels using Cleanlab and returns the IDs of the concerned assets.
    """
    assert single_true([only_train, only_predict, bool(cv_n_folds)])
    model_repository = set_model_repository_image_classification(model_repository)
    model_name = set_model_name_image_classification(model_name)
    model_repository_dir = Path.model_repository_dir(HOME, project_id, job_name, model_repository)

    # TODO: move to Path
    model_dir = PathPytorchVision.append_model_dir(model_repository_dir)
    model_path = PathPytorchVision.append_model_path(model_repository_dir, model_name)
    data_dir = os.path.join(model_repository_dir, "data")
    download_project_image_clean_lab(
        assets=assets, api_key=api_key, data_path=data_dir, job_name=job_name, project_id=project_id
    )

    # To set to False if the input size varies a lot and you see that the training takes
    # too much time
    cudnn.benchmark = True

    original_image_datasets = get_original_image_dataset(data_dir)

    class_names = original_image_datasets["train"].classes  # type: ignore
    labels = [label for img, label in datasets.ImageFolder(data_dir).imgs]
    assert len(class_names) > 1, "There should be at least 2 classes in the dataset."

    if only_train:
        image_datasets = copy.deepcopy(original_image_datasets)
        train_idx, val_idx = train_test_split(
            range(len(labels)), test_size=0.2, random_state=cv_seed
        )
        prepare_image_dataset(train_idx, val_idx, image_datasets)
        model, loss = get_trained_model_image_classif(
            epochs, model_name, verbose, class_names, image_datasets, save_model_path=model_path
        )
        return loss
    elif only_predict:
        image_datasets = copy.deepcopy(original_image_datasets)
        model: nn.Module = torch.load(model_path)  # type: ignore
        loader = torch_Data.DataLoader(
            original_image_datasets["test"], batch_size=1, shuffle=False, num_workers=1
        )
        probs = predict_probabilities(loader, model, verbose=verbose)
    else:
        pass
    kf = StratifiedKFold(n_splits=cv_n_folds, shuffle=True, random_state=cv_seed)
    for cv_fold in tqdm(range(cv_n_folds)):  # type: ignore
        # Split train into train and holdout for particular cv_fold.
        cv_train_idx, cv_holdout_idx = list(kf.split(range(len(labels)), labels))[cv_fold]

        # Separate datasets
        image_datasets, holdout_dataset = separe_holdout_datasets(
            cv_n_folds, verbose, original_image_datasets, cv_fold, cv_train_idx, cv_holdout_idx
        )

        model, loss = get_trained_model_image_classif(
            epochs, model_name, verbose, class_names, image_datasets, save_model_path=None
        )

        holdout_loader = torch_Data.DataLoader(
            holdout_dataset,
            batch_size=64,
            shuffle=False,
            pin_memory=True,
        )

        probs = predict_probabilities(holdout_loader, model, verbose=verbose)
        print("probs", probs)
        probs_path = os.path.join(model_dir, "model_fold_{}__probs.npy".format(cv_fold))
        np.save(probs_path, probs)

    psx_path = combine_folds(
        data_dir=data_dir,
        model_dir=model_dir,
        num_classes=len(class_names),
        seed=cv_seed,
        verbose=verbose,
    )

    psx = np.load(psx_path)
    train_imgs = datasets.ImageFolder(data_dir).imgs

    noise_indices = find_label_issues(labels, psx, return_indices_ranked_by="normalized_margin")

    noise_paths = []
    for idx in noise_indices:
        noise_paths.append(os.path.basename(train_imgs[idx][0])[:-4])

    return noise_paths
