import json
import os
from pathlib import Path
import re
from subprocess import PIPE, Popen
from tempfile import TemporaryDirectory
from typing import Dict, List

import DataAugmentationUtils
import DeepSSMUtils
from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db.models import Q
from rest_framework.authtoken.models import Token
import shapeworks as sw

from shapeworks_cloud.core import models
from swcc.api import swcc_session
from swcc.models import Project as SWCCProject
from swcc.models.constants import expected_key_prefixes
from swcc.models.project import ProjectFileIO

from .tasks import edit_swproj_section


def interpret_deepssm_form_data(data: Dict) -> Dict:
    # Prep
    data['validation_split'] = data['validationSplit']
    data['testing_split'] = data['testingSplit']
    data['image_spacing'] = data['imageSpacing']
    data['percent_variability'] = data['percentVariability']

    # Augmentation
    data['aug_num_samples'] = data['numSamples']
    data['aug_sampler_type'] = data['samplerType']

    # Training
    # TODO: review param names with swproj file from studio
    data['train_loss_function'] = data['lossFunction']
    data['train_epochs'] = data['epochs']
    data['train_learning_rate'] = data['learningRate']
    data['train_batch_size'] = data['batchSize']
    data['train_decay_learning_rate'] = data['decayLearningRate']
    data['train_fine_tuning'] = data['fineTuning']
    data['train_fine_tuning_epochs'] = data['ftEpochs']
    data['train_fine_tuning_learning_rate'] = data['ftLearningRate']

    return data


def run_prep(params, project, project_file):
    # //////////////////////////////////////////////
    # /// STEP 1: Create Split
    # //////////////////////////////////////////////
    val_split = float(params['validation_split'])
    test_split = float(params['testing_split'])
    # val_split = project.get_parameters('validation_split')
    # test_split = project.get_parameters('testing_split')
    train_split = 100.0 - val_split - test_split
    DeepSSMUtils.create_split(project, train_split, val_split, test_split)

    # /////////////////////////////////////////////////////////////////
    # /// STEP 2: Groom Training Shapes
    # /////////////////////////////////////////////////////////////////
    params = project.get_parameters("groom")
    params.set("alignment_method", "Iterative Closest Point")
    params.set("alignment_enabled", "true")
    project.set_parameters("groom", params)

    print("project path", project.get_project_path())

    with Popen(
        ["ls", "-a", "distance_transforms/"],
        stdout=PIPE,
        stderr=PIPE,
        cwd=project.get_project_path(),
    ) as proc:
        print(proc.stdout.read().decode("utf-8"))

    DeepSSMUtils.groom_training_shapes(project)
    project.save(project_file)

    # /////////////////////////////////////////////////////////////////
    # /// STEP 3: Optimize Training Particles
    # /////////////////////////////////////////////////////////////////

    # set num_particles to 16 and iterations_per_split to 1
    params = project.get_parameters("optimize")
    params.set("number_of_particles", "16")
    params.set("iterations_per_split", "1")
    project.set_parameters("optimize", params)

    DeepSSMUtils.optimize_training_particles(project)
    project.save(project_file)

    # /////////////////////////////////////////////////////////////////
    # /// STEP 4: Groom Training Images
    # /////////////////////////////////////////////////////////////////
    print("Grooming training images")
    DeepSSMUtils.groom_training_images(project)
    project.save(project_file)

    # /////////////////////////////////////////////////////////////////
    # /// STEP 5: Groom Validation Images
    # /////////////////////////////////////////////////////////////////
    val_indices = DeepSSMUtils.get_split_indices(project, "val")
    test_indices = DeepSSMUtils.get_split_indices(project, "test")
    val_test_indices = val_indices + test_indices
    DeepSSMUtils.groom_val_test_images(project, val_test_indices)
    project.save(project_file)

    # /////////////////////////////////////////////////////////////////
    # /// STEP 6: Optimize Validation Particles with Fixed Domains
    # /////////////////////////////////////////////////////////////////
    DeepSSMUtils.prep_project_for_val_particles(project)

    params = project.get_parameters("optimize")
    params.set("multiscale", "0")
    params.set("procrustes", "0")
    params.set("procrustes_interval", "0")
    params.set("procrustes_scaling", "0")
    params.set("narrow_band", "1e10")

    project.set_parameters("optimize", params)

    DeepSSMUtils.groom_validation_shapes(project)
    project.save(project_file)

    optimize = sw.Optimize()
    optimize.SetUpOptimize(project)
    optimize.Run()

    project.save(project_file)


def run_augmentation(params, project, download_dir):
    # /////////////////////////////////////////////////////////////////
    # /// STEP 7: Augment Data
    # /////////////////////////////////////////////////////////////////
    num_samples = int(params['aug_num_samples'])
    percent_variability = float(params['percent_variability']) / 100.0
    # aug_sampler_type to lowecase
    aug_sampler_type = params['aug_sampler_type'].lower()

    num_dims = 0  # set to 0 to allow for percent variability to be used

    embedded_dims = DeepSSMUtils.run_data_augmentation(
        project,
        num_samples,
        num_dims,
        percent_variability,
        aug_sampler_type,
        mixture_num=0,
        processes=1,  # Thread count
    )

    # TODO: confirm aug_num_dims is correct key
    # project.set("aug_num_dims", aug_dims)
    print(embedded_dims)

    aug_dir = download_dir + "/deepssm/augmentation/"
    aug_data_csv = aug_dir + "TotalData.csv"

    # print(os.listdir(aug_data_csv))
    print(os.listdir(aug_dir))
    # TODO: return this? How should this be saved?
    vis = DataAugmentationUtils.visualizeAugmentation(aug_data_csv, "violin")
    return embedded_dims


def run_training(params, project, download_dir, aug_dims):
    batch_size = int(params['train_batch_size'])

    # /////////////////////////////////////////////////////////////////
    # /// STEP 8: Create PyTorch loaders from data
    # /////////////////////////////////////////////////////////////////
    DeepSSMUtils.prepare_data_loaders(project, batch_size, "train")
    DeepSSMUtils.prepare_data_loaders(project, batch_size, "val")

    # /////////////////////////////////////////////////////////////////
    # /// STEP 9: Train DeepSSM Model
    # /////////////////////////////////////////////////////////////////
    out_dir = download_dir + "/deepssm/"
    aug_dir = out_dir + "augmentation/"

    loader_dir = out_dir + "torch_loaders/"

    epochs = int(params['train_epochs'])
    learning_rate = float(params['train_learning_rate'])
    decay_learning_rate = params['train_decay_learning_rate']
    fine_tune = params['train_fine_tuning']
    fine_tune_epochs = int(params['train_fine_tuning_epochs'])
    fine_tune_learning_rate = float(params['train_fine_tuning_learning_rate'])
    loss_function = params['train_loss_function']

    config_file = out_dir + "configuration.json"

    DeepSSMUtils.prepare_config_file(
        config_file,
        "model",
        aug_dims,
        out_dir,
        loader_dir,
        aug_dir,
        epochs,
        learning_rate,
        decay_learning_rate,
        fine_tune,
        fine_tune_epochs,
        fine_tune_learning_rate,
        loss_function,
    )

    DeepSSMUtils.trainDeepSSM(config_file)


def run_testing(params, project, download_dir):
    test_indices = DeepSSMUtils.get_split_indices(project, "test")

    # /////////////////////////////////////////////////////////////////
    # /// STEP 10: Groom Testing Images
    # /////////////////////////////////////////////////////////////////
    DeepSSMUtils.groom_val_test_images(project, test_indices)

    # /////////////////////////////////////////////////////////////////
    # /// STEP 11: Prepare Test Data PyTorch Loaders
    # /////////////////////////////////////////////////////////////////
    batch_size = int(params['train_batch_size'])
    DeepSSMUtils.prepare_data_loaders(project, batch_size, "test")

    test_names_file = download_dir + "/deepssm/torch_loaders/test_names.txt"

    with open(test_names_file, 'w') as file:
        list_items = ["'" + str(id) + "'" for id in test_indices]
        file.write("[")
        file.write(", ".join(list_items))
        file.write("]")

    config_file = download_dir + "/deepssm/configuration.json"

    # /////////////////////////////////////////////////////////////////
    # /// STEP 12: Test DeepSSM Model
    # /////////////////////////////////////////////////////////////////
    DeepSSMUtils.testDeepSSM(config_file)

    # print config_file's contents
    with open(config_file, 'r') as json_file:
        json_object = json.load(json_file)

    print(json.dumps(json_object))
    print('=====================')
    print(os.listdir(download_dir + "/groomed/"))
    print('=====================')
    print(os.listdir(download_dir + "/deepssm/"))

    DeepSSMUtils.process_test_predictions(project, config_file)


# TODO: implement all steps
def run_deepssm_command(
    user_id,
    project_id,
    form_data,
    command,
    pre_command_function,
    post_command_function,
    progress_id,
):
    user = User.objects.get(id=user_id)
    progress = models.TaskProgress.objects.get(id=progress_id)
    token, _created = Token.objects.get_or_create(user=user)
    base_url = settings.API_URL

    with TemporaryDirectory() as download_dir:
        with swcc_session(base_url=base_url) as session:
            # fetch everything we need
            session.set_token(token.key)
            project = models.Project.objects.get(id=project_id)
            print("setting project filename")
            project_filename = project.file.name.split('/')[-1]
            print("project filename set", project_filename)
            swcc_project = SWCCProject.from_id(project.id)
            swcc_project.download(download_dir)
            print("Downloaded swcc project")

            pre_command_function()
            progress.update_percentage(10)

            if form_data:
                # write the form data to the project file
                form_data = interpret_deepssm_form_data(form_data)
                edit_swproj_section(
                    Path(download_dir, project_filename),
                    'deepssm',
                    form_data,
                )

            # TODO: how to capture output of functions?
            result_data = {}

            # data_dir = download_dir + 'data/'

            # Use shapeworks python project class
            sw_project = sw.Project()

            # sw_project.set_subjects(swcc_project.subjects)

            sw_project_file = str(Path(download_dir, project_filename))

            # Save project spreadsheet
            # spreadsheet_file = data_dir + "deepssm_project.swproj"
            sw_project.load(sw_project_file)

            os.chdir(sw_project.get_project_path())
            # TODO: pass progress through and update percentage per step?
            run_prep(form_data, sw_project, sw_project_file)
            progress.update_percentage(20)

            aug_dims = run_augmentation(form_data, sw_project, download_dir)
            progress.update_percentage(30)

            run_training(form_data, sw_project, download_dir, aug_dims)
            progress.update_percentage(50)

            run_testing(form_data, sw_project, download_dir)
            progress.update_percentage(90)

            os.chdir('../../')
            # TODO: output relevant results
            post_command_function(project, download_dir, result_data, project_filename)
            progress.update_percentage(100)


@shared_task
def deepssm_run(user_id, project_id, progress_id, form_data):
    def pre_command_function():
        # TODO: add removal of all previous results for new db entries

        # project = models.Project.objects.get(id=project_id)

        # delete any previous results.
        # Augmentation is the first step so should remove all cached deepssm data
        # models.CachedPrediction.objects.filter(
        #     ft_predictions__cacheddeepssm__project=project
        # ).delete()
        # models.CachedPrediction.objects.filter(
        #     pca_predictions__cacheddeepssm__project=project
        # ).delete()
        # models.CachedExample.objects.filter(
        #     best__cachedmodel__cacheddeepssm__project=project
        # ).delete()
        # models.CachedExample.objects.filter(
        #     median__cachedmodel__cacheddeepssm__project=project
        # ).delete()
        # models.CachedExample.objects.filter(
        #     worst__cachedmodel__cacheddeepssm__project=project
        # ).delete()
        # models.CachedModelExamples.objects.filter(
        #     cachedmodel__cacheddeepssm__project=project
        # ).delete()
        # models.CachedModel.objects.filter(cacheddeepssm__project=project).delete()
        # models.CachedTensors.objects.filter(tensors__cacheddeepssm__project=project).delete()
        # models.CachedDataLoaders.objects.filter(cacheddeepssm__project=project).delete()
        # models.CachedAugmentationPair.objects.filter(
        #     cachedaugmentation__cacheddeepssm__project=project
        # ).delete()
        # models.CachedAugmentation.objects.filter(cacheddeepssm__project=project).delete()
        # models.CachedDeepSSM.objects.filter(project=project).delete()
        pass

    def post_command_function(project, download_dir, result_data, project_filename):
        print(result_data)
        # TODO: save relevant result data to db (models)
        # save project file changes to database
        project.file.save(
            project_filename,
            open(Path(download_dir, project_filename), 'rb'),
        )

    run_deepssm_command(
        user_id,
        project_id,
        form_data,
        'deepssm',
        pre_command_function,
        post_command_function,
        progress_id,
    )
