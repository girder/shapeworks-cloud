import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict

import DataAugmentationUtils
import DeepSSMUtils
from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
import shapeworks as sw

from shapeworks_cloud.core import models
from swcc.api import swcc_session
from swcc.models import Project as SWCCProject

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
    data['train_loss_function'] = data['lossFunction']
    data['train_epochs'] = data['epochs']
    data['train_learning_rate'] = data['learningRate']
    data['train_batch_size'] = data['batchSize']
    data['train_decay_learning_rate'] = data['decayLearningRate']
    data['train_fine_tuning'] = data['fineTuning']
    data['train_fine_tuning_epochs'] = data['ftEpochs']
    data['train_fine_tuning_learning_rate'] = data['ftLearningRate']

    return data


def run_prep(params, project, project_file, progress):
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
    params = project.get_parameters('groom')
    params.set('alignment_method', 'Iterative Closest Point')
    params.set('alignment_enabled', 'true')
    project.set_parameters('groom', params)

    DeepSSMUtils.groom_training_shapes(project)
    project.save(project_file)

    # /////////////////////////////////////////////////////////////////
    # /// STEP 3: Optimize Training Particles
    # /////////////////////////////////////////////////////////////////

    # set num_particles to 16 and iterations_per_split to 1
    params = project.get_parameters('optimize')
    params.set('number_of_particles', '16')
    params.set('iterations_per_split', '1')
    project.set_parameters('optimize', params)

    DeepSSMUtils.optimize_training_particles(project)
    project.save(project_file)
    progress.update_percentage(12)

    # /////////////////////////////////////////////////////////////////
    # /// STEP 4: Groom Training Images
    # /////////////////////////////////////////////////////////////////
    print('Grooming training images')
    DeepSSMUtils.groom_training_images(project)
    project.save(project_file)

    # /////////////////////////////////////////////////////////////////
    # /// STEP 5: Groom Validation Images
    # /////////////////////////////////////////////////////////////////
    val_indices = DeepSSMUtils.get_split_indices(project, 'val')
    test_indices = DeepSSMUtils.get_split_indices(project, 'test')
    val_test_indices = val_indices + test_indices
    DeepSSMUtils.groom_val_test_images(project, val_test_indices)
    project.save(project_file)
    progress.update_percentage(14)

    # /////////////////////////////////////////////////////////////////
    # /// STEP 6: Optimize Validation Particles with Fixed Domains
    # /////////////////////////////////////////////////////////////////
    DeepSSMUtils.prep_project_for_val_particles(project)

    params = project.get_parameters('optimize')
    params.set('multiscale', '0')
    params.set('procrustes', '0')
    params.set('procrustes_interval', '0')
    params.set('procrustes_scaling', '0')
    params.set('narrow_band', '1e10')

    project.set_parameters('optimize', params)

    DeepSSMUtils.groom_validation_shapes(project)
    project.save(project_file)
    progress.update_percentage(17)

    optimize = sw.Optimize()
    optimize.SetUpOptimize(project)
    optimize.Run()

    project.save(project_file)
    progress.update_percentage(20)


def run_augmentation(params, project, download_dir, progress):
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
    progress.update_percentage(25)

    aug_dir = download_dir + '/deepssm/augmentation/'
    aug_data_csv = aug_dir + 'TotalData.csv'

    DataAugmentationUtils.visualizeAugmentation(aug_data_csv, 'violin')
    progress.update_percentage(30)

    return embedded_dims


def run_training(params, project, download_dir, aug_dims, progress):
    batch_size = int(params['train_batch_size'])

    # /////////////////////////////////////////////////////////////////
    # /// STEP 8: Create PyTorch loaders from data
    # /////////////////////////////////////////////////////////////////
    DeepSSMUtils.prepare_data_loaders(project, batch_size, 'train')
    DeepSSMUtils.prepare_data_loaders(project, batch_size, 'val')
    progress.update_percentage(35)

    # /////////////////////////////////////////////////////////////////
    # /// STEP 9: Train DeepSSM Model
    # /////////////////////////////////////////////////////////////////
    out_dir = download_dir + '/deepssm/'
    aug_dir = out_dir + 'augmentation/'

    loader_dir = out_dir + 'torch_loaders/'

    epochs = int(params['train_epochs'])
    learning_rate = float(params['train_learning_rate'])
    decay_learning_rate = params['train_decay_learning_rate']
    fine_tune = params['train_fine_tuning']
    fine_tune_epochs = int(params['train_fine_tuning_epochs'])
    fine_tune_learning_rate = float(params['train_fine_tuning_learning_rate'])
    loss_function = params['train_loss_function']

    config_file = out_dir + 'configuration.json'

    DeepSSMUtils.prepare_config_file(
        config_file,
        'model',
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
    progress.update_percentage(40)

    DeepSSMUtils.trainDeepSSM(config_file)
    progress.update_percentage(50)


def run_testing(params, project, download_dir, progress):
    test_indices = DeepSSMUtils.get_split_indices(project, 'test')

    # /////////////////////////////////////////////////////////////////
    # /// STEP 10: Groom Testing Images
    # /////////////////////////////////////////////////////////////////
    DeepSSMUtils.groom_val_test_images(project, test_indices)
    progress.update_percentage(55)

    # /////////////////////////////////////////////////////////////////
    # /// STEP 11: Prepare Test Data PyTorch Loaders
    # /////////////////////////////////////////////////////////////////
    batch_size = int(params['train_batch_size'])
    DeepSSMUtils.prepare_data_loaders(project, batch_size, 'test')

    test_names_file = download_dir + '/deepssm/torch_loaders/test_names.txt'

    with open(test_names_file, 'w') as file:
        list_items = ["'" + str(id) + "'" for id in test_indices]
        file.write('[')
        file.write(', '.join(list_items))
        file.write(']')

    config_file = download_dir + '/deepssm/configuration.json'
    progress.update_percentage(60)

    # /////////////////////////////////////////////////////////////////
    # /// STEP 12: Test DeepSSM Model
    # /////////////////////////////////////////////////////////////////
    DeepSSMUtils.testDeepSSM(config_file)

    DeepSSMUtils.process_test_predictions(project, config_file)
    progress.update_percentage(90)


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
            print('setting project filename')
            project_filename = project.file.name.split('/')[-1]
            print('project filename set', project_filename)
            swcc_project = SWCCProject.from_id(project.id)
            swcc_project.download(download_dir)
            print('Downloaded swcc project')

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

            result_data = {}

            # data_dir = download_dir + 'data/'

            # Use shapeworks python project class
            sw_project = sw.Project()

            # sw_project.set_subjects(swcc_project.subjects)

            sw_project_file = str(Path(download_dir, project_filename))

            # Save project spreadsheet
            # spreadsheet_file = data_dir + 'deepssm_project.swproj'
            sw_project.load(sw_project_file)

            os.chdir(sw_project.get_project_path())
            run_prep(form_data, sw_project, sw_project_file, progress)

            aug_dims = run_augmentation(form_data, sw_project, download_dir, progress)

            # result data has paths to files
            result_data['augmentation'] = {
                'total_data_csv': download_dir + '/deepssm/augmentation/TotalData.csv',
                'violin_plot': download_dir + '/deepssm/augmentation/violin.png',
                'generated_images': os.listdir(
                    download_dir + '/deepssm/augmentation/Generated-Images/'
                ),
                'generated_particles': os.listdir(
                    download_dir + '/deepssm/augmentation/Generated-Particles/'
                ),
            }

            run_training(form_data, sw_project, download_dir, aug_dims, progress)

            result_data['training'] = {
                'train_log': download_dir + '/deepssm/model/train_log.csv',
                'training_plot': download_dir + '/deepssm/model/training_plot.png',
                'training_plot_ft': download_dir + '/deepssm/model/training_plot_ft.png',
                'train_images': os.listdir(download_dir + '/deepssm/train_images/'),
                'val_and_test_images': os.listdir(download_dir + '/deepssm/val_and_test_images/'),
            }

            run_testing(form_data, sw_project, download_dir, progress)

            result_data['testing'] = {
                'world_predictions': os.listdir(
                    download_dir + '/deepssm/model/test_predictions/world_predictions/'
                ),
                'local_predictions': os.listdir(
                    download_dir + '/deepssm/model/test_predictions/local_predictions/'
                ),
                'test_distances': download_dir + '/deepssm/test_distances.csv',
            }

            os.chdir('../../')

            post_command_function(project, download_dir, result_data, project_filename)
            progress.update_percentage(100)


@shared_task
def deepssm_run(user_id, project_id, progress_id, form_data):
    def pre_command_function():
        project = models.Project.objects.get(id=project_id)

        # delete any previous results.
        models.DeepSSMResult.objects.filter(project=project).delete()
        models.DeepSSMAugPair.objects.filter(project=project).delete()
        models.DeepSSMTrainingImage.objects.filter(project=project).delete()
        models.DeepSSMTestingData.objects.filter(project=project).delete()

    def post_command_function(project, download_dir, result_data, project_filename):
        # save project file changes to database
        project.file.save(
            project_filename,
            open(Path(download_dir, project_filename), 'rb'),
        )

        deepssm_result = models.DeepSSMResult.objects.create(
            project=project,
        )

        # augmentation
        deepssm_result.aug_visualization.save(
            'violin_plot.png',
            open(result_data['augmentation']['violin_plot'], 'rb'),
        )

        # create aug pairs
        for i in range(0, len(result_data['augmentation']['generated_images'])):
            aug_pair = models.DeepSSMAugPair.objects.create(
                project=project,
                sample_num=int(  # get sample number from filename
                    result_data['augmentation']['generated_images'][i].split('_')[2].split('.')[0],
                ),
            )
            aug_pair.mesh.save(
                result_data['augmentation']['generated_images'][i],
                open(
                    download_dir
                    + '/deepssm/augmentation/Generated-Images/'
                    + result_data['augmentation']['generated_images'][i],
                    'rb',
                ),
            )
            aug_pair.particles.save(
                result_data['augmentation']['generated_particles'][i],
                open(
                    download_dir
                    + '/deepssm/augmentation/Generated-Particles/'
                    + result_data['augmentation']['generated_particles'][i],
                    'rb',
                ),
            )

        # training
        deepssm_result.training_visualization.save(
            'training_plot.png',
            open(result_data['training']['training_plot'], 'rb'),
        )
        deepssm_result.training_visualization_ft.save(
            'training_plot_ft.png',
            open(result_data['training']['training_plot_ft'], 'rb'),
        )
        deepssm_result.training_data_table.save(
            'train_log.csv',
            open(result_data['training']['train_log'], 'rb'),
        )

        # testing
        deepssm_result.testing_distances.save(
            'test_distances.csv',
            open(result_data['testing']['test_distances'], 'rb'),
        )

        world_predictions = result_data['testing']['world_predictions']
        local_predictions = result_data['testing']['local_predictions']

        print(world_predictions, local_predictions)
        # create test pairs
        for predictions in [world_predictions, local_predictions]:
            for _i in range(0, len(predictions)):
                if len(predictions) > 0:
                    # in world_predictions, there's two files with the same name,
                    # but .vtk and .particles file types. Add these to mesh and partciles field
                    file1 = predictions.pop()
                    filename = file1.split('.')[0]

                    test_pair = models.DeepSSMTestingData.objects.create(
                        project=project,
                        image_type='world' if predictions == world_predictions else 'local',
                        image_id=filename,
                    )

                    predictions_path = (
                        download_dir
                        + '/deepssm/model/test_predictions/'
                        + (
                            'world_predictions/'
                            if predictions == world_predictions
                            else 'local_predictions/'
                        )
                    )

                    if file1.split('.')[1] == 'vtk':
                        file2 = predictions.pop(predictions.index(filename + '.particles'))
                        test_pair.mesh.save(
                            file1,
                            open(
                                predictions_path + file1,
                                'rb',
                            ),
                        )
                        test_pair.particles.save(
                            file2,
                            open(
                                predictions_path + file2,
                                'rb',
                            ),
                        )
                    else:
                        file2 = predictions.pop(predictions.index(filename + '.vtk'))
                        test_pair.mesh.save(
                            file2,
                            open(
                                predictions_path + file2,
                                'rb',
                            ),
                        )
                        test_pair.particles.save(
                            file1,
                            open(
                                predictions_path + file1,
                                'rb',
                            ),
                        )

        train_images = result_data['training']['train_images']
        val_and_test_images = result_data['training']['val_and_test_images']
        # create training images
        for images in [train_images, val_and_test_images]:
            for image in images:
                image_type = 'train' if images == train_images else 'val_and_test'
                train_image = models.DeepSSMTrainingImage.objects.create(
                    project=project,
                    validation=True if image_type == 'val_and_test' else False,
                )
                train_image.image.save(
                    image,
                    open(
                        download_dir + '/deepssm/' + image_type + '_images/' + image,
                        'rb',
                    ),
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
