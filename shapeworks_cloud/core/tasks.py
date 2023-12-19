import json
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

from shapeworks_cloud.core import models
from shapeworks_cloud.core.deepssm_util import DeepSSMFileType, DeepSSMSplitType, get_list
from swcc.api import swcc_session
from swcc.models import Project as SWCCProject
from swcc.models.constants import expected_key_prefixes
from swcc.models.project import ProjectFileIO


def parse_progress(xml_string):
    match = re.search('(?<=<progress>)(.*)(?=</progress>)', xml_string)
    if match:
        # running of exec represents ~80% of task progress
        return int(int(match.group().split('.')[0]) * 0.8)
    return 0


def edit_swproj_section(filename, section_name, new_contents):
    with open(filename, 'r') as f:
        data = json.load(f)
    if section_name == 'groom':
        data[section_name] = {}
        data[section_name]['shape'] = new_contents
    else:
        data[section_name] = new_contents
    data['data'] = [
        {
            k: v.replace('../', '').replace('./', '') if isinstance(v, str) else v
            for k, v in row.items()
        }
        for row in data['data']
    ]
    with open(filename, 'w') as f:
        json.dump(data, f)


def interpret_form_data(data, command, swcc_project):
    anisotropic_values = []
    del_keys = []
    for key, value in data.items():
        if 'anisotropic' in key:
            anisotropic_values.append(value)
            del_keys.append(key)

    for del_key in del_keys:
        del data[del_key]

    if command == 'groom' and len(anisotropic_values) > 0:
        data['spacing'] = ' '.join(anisotropic_values)
    elif command == 'optimize':
        num_particles = data.get('number_of_particles')
        if num_particles:
            max_num_domains = max(s.num_domains for s in swcc_project.subjects)
            data['number_of_particles'] = ' '.join(
                str(num_particles) for i in range(max_num_domains)
            )
    elif command == 'augment':
        # split data should only be overwritten when running augmentation
        data['validation_split'] = data['validationSplit']
        data['testing_split'] = data['testingSplit']

        data['aug_num_dims'] = data['numDimensions']
        data['aug_num_samples'] = data['numSamples']
        data['aug_percent_variability'] = data['percentVariability']
        data['aug_sampler_type'] = data['samplerType']
    elif command == 'train':
        data['train_epochs'] = data['epochs']
        data['train_learning_rate'] = data['learningRate']
        data['train_decay_learning_rate'] = data['decayLearningRate']
        data['train_batch_size'] = data['batchSize']
        data['train_fine_tuning'] = data['fineTuning']
        data['train_fine_tuning_epochs'] = data['ftEpochs']
        data['train_fine_tuning_learning_rate'] = data['ftLearningRate']

    return data


def run_shapeworks_command(
    user_id,
    project_id,
    form_data,
    command,
    pre_command_function,
    post_command_function,
    progress_id,
    args: List[str],
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
            project_filename = project.file.name.split('/')[-1]
            swcc_project = SWCCProject.from_id(project.id)
            swcc_project.download(download_dir)

            pre_command_function()
            progress.update_percentage(10)

            if form_data:
                # write the form data to the project file
                form_data = interpret_form_data(form_data, command, swcc_project)
                edit_swproj_section(
                    Path(download_dir, project_filename),
                    command,
                    form_data,
                )

            # perform command
            full_command = [
                '/opt/shapeworks/bin/shapeworks',
                command,
                f'--name={project_filename}',
            ]

            if command == 'analyze':
                full_command.append('--output=analysis.json')
            else:
                full_command.append('--xmlconsole')

            if len(args) > 0:
                full_command.extend(args)

            with Popen(full_command, cwd=download_dir, stdout=PIPE, stderr=PIPE) as process:
                if process.stderr and process.stdout:
                    for line in iter(process.stdout.readline, b''):
                        progress.refresh_from_db()
                        if progress.abort:
                            progress.delete()
                            process.kill()
                            return
                        else:
                            if command == 'analyze':
                                print(line.decode())  # analyze task has no xmloutput
                            else:
                                progress.update_percentage(parse_progress(line.decode()) + 10)
                    for line in iter(process.stderr.readline, b''):
                        progress.update_error(line.decode())
                        return
                process.wait()

            result_filename = 'analysis.json' if command == 'analyze' else project_filename
            with open(Path(download_dir, result_filename), 'r') as f:
                result_data = json.load(f)
            post_command_function(project, download_dir, result_data, project_filename)
            progress.update_percentage(100)


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
            project_filename = project.file.name.split('/')[-1]
            swcc_project = SWCCProject.from_id(project.id)
            swcc_project.download(download_dir)

            pre_command_function()
            progress.update_percentage(10)

            if form_data:
                # write the form data to the project file
                form_data = interpret_form_data(form_data, command, swcc_project)
                edit_swproj_section(
                    Path(download_dir, project_filename),
                    'deepssm',
                    form_data,
                )

            result_data = {}

            testing_split = float(form_data.get('testing_split'))

            # perform deepssm tasks
            if command == 'augment':
                # TODO: Does this need to be custom or deepssmutils integration?
                # get training image list
                train_image_list = get_list(
                    swcc_project, DeepSSMFileType.IMAGE, DeepSSMSplitType.TRAIN, testing_split
                )

                # get training particle list
                train_particle_list = get_list(
                    swcc_project, DeepSSMFileType.PARTICLE, DeepSSMSplitType.TRAIN, testing_split
                )

                # get augmentation parameters as object
                (
                    aug_num_samples,
                    aug_num_dimensions,
                    aug_percent_variability,
                    aug_sampler_type,
                ) = form_data.values()

                # set augmentation directory (where the augmentaton output will be stored)
                aug_dir = download_dir + '/Augmentation/'
                total_data = aug_dir + 'TotalData.csv'
                # run augmentation via (runDataAugmentation)
                result_data['aug_dims'] = DataAugmentationUtils.runDataAugmentation(
                    aug_dir,
                    train_image_list,
                    train_particle_list,
                    aug_num_samples,
                    aug_num_dimensions,
                    aug_percent_variability,
                    aug_sampler_type,
                    0,
                    1,
                )

                result_data['aug_dir'] = aug_dir
                result_data['total_data'] = total_data

                # visualize the augmentation results
                result_data['visualization'] = DataAugmentationUtils.visualizeAugmentation(
                    aug_dir + "TotalData.csv", "violin", False
                )
            elif command == 'train':
                # get lists of training images, training particles, and testing images
                train_image_list = get_list(
                    swcc_project, DeepSSMFileType.IMAGE, DeepSSMSplitType.TRAIN, testing_split
                )
                train_particle_list = get_list(
                    swcc_project, DeepSSMFileType.PARTICLE, DeepSSMSplitType.TRAIN, testing_split
                )
                test_image_list = get_list(
                    swcc_project, DeepSSMFileType.IMAGE, DeepSSMSplitType.TEST, testing_split
                )

                # set directories
                out_dir = download_dir + '/deepssm/'
                down_dir = out_dir + 'DownsampledImages/'
                loader_dir = out_dir + 'TorchDataLoaders/'

                total_data = ''  # TODO: pull totaldata.csv file from s3 or project? ensure this is a directory with Path() or similar

                # get parameters
                (
                    epochs,
                    learning_rate,
                    batch_size,
                    decay_lr,
                    fine_tune,
                    fine_tune_epochs,
                    fine_tune_learning_rate,
                    num_dims,
                ) = form_data.values()
                train_split = form_data['train_split']

                # downsample to 75% of original resolution
                downsample_factor = 0.75

                # get train/validation loaders
                result_data['train_loaders'] = DeepSSMUtils.getTrainValLoaders(
                    loader_dir,
                    total_data,
                    batch_size,
                    downsample_factor,
                    down_dir,
                    train_split,
                )

                # get test loader
                result_data['test_loaders'] = DeepSSMUtils.getTestLoader(loader_dir, test_image_list, downsample_factor, down_dir)

                # prepare config file
                result_data['config_dir'] = config_dir = out_dir + 'configuration.json'
                result_data['config_file'] = DeepSSMUtils.prepareConfigFile(
                    config_dir,
                    "model",
                    num_dims,
                    out_dir,
                    loader_dir,
                    aug_dir,
                    epochs,
                    learning_rate,
                    decay_lr,
                    fine_tune,
                    fine_tune_epochs,
                    fine_tune_learning_rate,
                )

                # run training with config file
                result_data['model'] = DeepSSMUtils.trainDeepSSM(config_dir)

            elif command == 'test':
                # get configuration file
                # TODO: get config file from the model object (provide path)
                config_dir = download_dir + '/deepssm/configuration.json'

                # run testing with config file
                result_data['testing'] = DeepSSMUtils.testDeepSSM(config_dir)

            post_command_function(project, download_dir, result_data, project_filename)
            progress.update_percentage(100)


@shared_task
def groom(user_id, project_id, form_data, progress_id):
    def pre_command_function():
        # delete any previous results
        models.GroomedSegmentation.objects.filter(project=project_id).delete()
        models.GroomedMesh.objects.filter(project=project_id).delete()

    def post_command_function(project, download_dir, result_data, project_filename):
        # save project file changes to database
        project.file.save(
            project_filename,
            open(Path(download_dir, project_filename), 'rb'),
        )

        # make new objects in database
        project_segmentations = models.Segmentation.objects.filter(
            subject__dataset__id=project.dataset.id
        )
        project_meshes = models.Mesh.objects.filter(subject__dataset__id=project.dataset.id)
        for entry in result_data['data']:
            row: Dict[str, Dict] = {}
            for key in entry.keys():
                prefixes = [p for p in expected_key_prefixes if key.startswith(p)]
                if len(prefixes) > 0:
                    prefix = prefixes[0]
                    anatomy_id = 'anatomy' + key.replace(prefix, '')
                    if anatomy_id not in row:
                        row[anatomy_id] = {}
                    row[anatomy_id][prefix] = entry[key].replace('../', '').replace('./', '')

            for anatomy_data in row.values():
                if 'groomed' not in anatomy_data:
                    continue
                source_filename = anatomy_data['shape'].split('/')[-1]
                result_file = Path(download_dir, anatomy_data['groomed'])
                try:
                    target_object = project_segmentations.get(
                        file__endswith=source_filename,
                    )
                    result_object = models.GroomedSegmentation.objects.create(
                        project=project,
                        segmentation=target_object,
                    )
                except models.Segmentation.DoesNotExist:
                    target_object = project_meshes.get(
                        file__endswith=source_filename,
                    )
                    result_object = models.GroomedMesh.objects.create(
                        project=project,
                        mesh=target_object,
                    )
                result_object.file.save(
                    anatomy_data['groomed'],
                    open(result_file, 'rb'),
                )

    run_shapeworks_command(
        user_id,
        project_id,
        form_data,
        'groom',
        pre_command_function,
        post_command_function,
        progress_id,
        [],
    )


@shared_task
def optimize(user_id, project_id, form_data, progress_id, analysis_progress_id):
    def pre_command_function():
        # delete any previous results
        models.OptimizedParticles.objects.filter(project=project_id).delete()

    def post_command_function(project, download_dir, result_data, project_filename):
        # save project file changes to database
        project.file.save(
            project_filename,
            open(Path(download_dir, project_filename), 'rb'),
        )

        # make new objects in database
        project_groomed_segmentations = models.GroomedSegmentation.objects.filter(project=project)
        project_groomed_meshes = models.GroomedMesh.objects.filter(project=project)

        for entry in result_data['data']:
            row: Dict[str, Dict] = {}
            for key in entry.keys():
                prefixes = [p for p in expected_key_prefixes if key.startswith(p)]
                if len(prefixes) > 0 and prefixes[0] != 'name':
                    prefix = prefixes[0]
                    anatomy_id = 'anatomy' + key.replace(prefix, '').replace('_particles', '')
                    if prefix in ['mesh', 'segmentation', 'image', 'contour']:
                        prefix = 'shape'
                    if anatomy_id not in row:
                        row[anatomy_id] = {}
                    row[anatomy_id][prefix] = entry[key].replace('../', '').replace('./', '')

            for anatomy_id, anatomy_data in row.items():
                if 'groomed' not in anatomy_data:
                    continue
                groomed_filename = anatomy_data['groomed'].split('/')[-1]
                target_segmentation = project_groomed_segmentations.filter(
                    file__endswith=groomed_filename,
                ).first()
                target_mesh = project_groomed_meshes.filter(
                    file__endswith=groomed_filename,
                ).first()
                if target_mesh and target_mesh.mesh:
                    subject = target_mesh.mesh.subject
                elif target_segmentation and target_segmentation.segmentation:
                    subject = target_segmentation.segmentation.subject
                result_particles_object = models.OptimizedParticles.objects.create(
                    groomed_segmentation=target_segmentation,
                    groomed_mesh=target_mesh,
                    project=project,
                    subject=subject,
                    anatomy_type=anatomy_id,
                )
                if 'world' in anatomy_data:
                    result_particles_object.world.save(
                        anatomy_data['world'].split('/')[-1],
                        open(Path(download_dir, anatomy_data['world']), 'rb'),
                    )
                if 'local' in anatomy_data:
                    result_particles_object.local.save(
                        anatomy_data['local'].split('/')[-1],
                        open(Path(download_dir, anatomy_data['local']), 'rb'),
                    )
                if 'alignment' in anatomy_data:
                    result_particles_object.transform.save(
                        '.'.join(anatomy_data['shape'].split('/')[-1].split('.')[:-1])
                        + '.transform',
                        ContentFile(str(anatomy_data['alignment']).encode()),
                    )

    run_shapeworks_command(
        user_id,
        project_id,
        form_data,
        'optimize',
        pre_command_function,
        post_command_function,
        progress_id,
        [],
    )

    analyze.delay(user_id, project_id, analysis_progress_id, ['--range=2.0', '--steps=11'])


@shared_task
def analyze(user_id, project_id, progress_id, args: List[str]):
    def pre_command_function():
        # delete any previous results
        project = models.Project.objects.get(id=project_id)
        models.ReconstructedSample.objects.filter(project=project).delete()
        models.CachedAnalysisModePCA.objects.filter(
            cachedanalysismode__cachedanalysis__project=project
        ).delete()
        models.CachedAnalysisMode.objects.filter(cachedanalysis__project=project).delete()
        models.CachedAnalysisGroup.objects.filter(cachedanalysis__project=project).delete()
        models.CachedAnalysisMeanShape.objects.filter(cachedanalysis__project=project).delete()
        models.CachedAnalysis.objects.filter(project=project).delete()

    def post_command_function(project, download_dir, result_data, project_filename):
        project_fileio = ProjectFileIO(project=SWCCProject.from_id(project.id))
        swcc_cached_analysis = project_fileio.load_analysis_from_json(
            Path(download_dir, 'analysis.json')
        )
        project.last_cached_analysis = models.CachedAnalysis.objects.get(id=swcc_cached_analysis.id)
        project.save()

        with open(Path(download_dir, project_filename)) as pf:
            project_data = json.load(pf)['data']
            for i, sample in enumerate(project_data):
                reconstructed_filenames = result_data['reconstructed_samples'][i]
                subject_particles = list(
                    models.OptimizedParticles.objects.filter(project=project).filter(
                        Q(groomed_mesh__mesh__subject__name=sample['name'])
                        | Q(groomed_segmentation__segmentation__subject__name=sample['name'])
                    )
                )
                for j, reconstructed_filename in enumerate(reconstructed_filenames):
                    reconstructed = models.ReconstructedSample(
                        project=project, particles=subject_particles[j]
                    )
                    reconstructed.file.save(
                        reconstructed_filename,
                        open(Path(download_dir, reconstructed_filename), 'rb'),
                    )
                    reconstructed.save()

    run_shapeworks_command(
        user_id,
        project_id,
        None,
        'analyze',
        pre_command_function,
        post_command_function,
        progress_id,
        args,
    )


# DeepSSM tasks, Augmentation, Training, Testing
# TODO: Implement these tasks
@shared_task
def deepssm_augment(user_id, project_id, progress_id, form_data):
    def pre_command_function():
        project = models.Project.objects.get(id=project_id)

        # delete any previous results.
        # Augmentation is the first step so should remove all cached deepssm data
        models.CachedPrediction.objects.filter(
            ft_predictions__cacheddeepssm__project=project
        ).delete()
        models.CachedPrediction.objects.filter(
            pca_predictions__cacheddeepssm__project=project
        ).delete()
        models.CachedExample.objects.filter(
            best__cachedmodel__cacheddeepssm__project=project
        ).delete()
        models.CachedExample.objects.filter(
            median__cachedmodel__cacheddeepssm__project=project
        ).delete()
        models.CachedExample.objects.filter(
            worst__cachedmodel__cacheddeepssm__project=project
        ).delete()
        models.CachedModelExamples.objects.filter(
            cachedmodel__cacheddeepssm__project=project
        ).delete()
        models.CachedModel.objects.filter(cacheddeepssm__project=project).delete()
        models.CachedTensors.objects.filter(tensors__cacheddeepssm__project=project).delete()
        models.CachedDataLoaders.objects.filter(cacheddeepssm__project=project).delete()
        models.CachedAugmentationPair.objects.filter(
            cachedaugmentation__cacheddeepssm__project=project
        ).delete()
        models.CachedAugmentation.objects.filter(cacheddeepssm__project=project).delete()
        models.CachedDeepSSM.objects.filter(project=project).delete()

    def post_command_function(project, download_dir, result_data, project_filename):
        print(result_data)
        # TODO: save relevant result data to db (models)
        # save project file changes to database
        project.file.save(
            project_filename,
            open(Path(download_dir, project_filename), 'rb'),
        )

        for entry in result_data:
            if 'aug_dir' in entry.keys():
                pair = models.CachedAugmentationPair.objects.create()
                pair.file.save(
                    result_data[entry].split('/') + 'Generated-Images',
                    open(Path(download_dir, result_data[entry]), 'rb'),
                )
                pair.save()

    run_deepssm_command(
        user_id,
        project_id,
        form_data,
        'augment',
        pre_command_function,
        post_command_function,
        progress_id,
    )


@shared_task
def deepssm_train(user_id, project_id, progress_id, form_data):
    def pre_command_function():
        project = models.Project.objects.get(id=project_id)

        # delete any previous results
        models.CachedPrediction.objects.filter(
            ft_predictions__cacheddeepssm__project=project
        ).delete()
        models.CachedPrediction.objects.filter(
            pca_predictions__cacheddeepssm__project=project
        ).delete()
        models.CachedExample.objects.filter(
            best__cachedmodel__cacheddeepssm__project=project
        ).delete()
        models.CachedExample.objects.filter(
            median__cachedmodel__cacheddeepssm__project=project
        ).delete()
        models.CachedExample.objects.filter(
            worst__cachedmodel__cacheddeepssm__project=project
        ).delete()
        models.CachedModelExamples.objects.filter(
            cachedmodel__cacheddeepssm__project=project
        ).delete()
        models.CachedModel.objects.filter(cacheddeepssm__project=project).delete()
        models.CachedTensors.objects.filter(tensors__cacheddeepssm__project=project).delete()
        models.CachedDataLoaders.objects.filter(cacheddeepssm__project=project).delete()

    def post_command_function(project, download_dir, result_data, project_filename):
        print(result_data)
        # save project file changes to database
        project.file.save(
            project_filename,
            open(Path(download_dir, project_filename), 'rb'),
        )

    run_deepssm_command(
        user_id,
        project_id,
        form_data,
        'train',
        pre_command_function,
        post_command_function,
        progress_id,
    )


@shared_task
def deepssm_test(user_id, project_id, progress_id, form_data):
    def pre_command_function():
        project = models.Project.objects.get(id=project_id)

        # delete any previous results
        models.CachedPrediction.objects.filter(
            ft_predictions__cacheddeepssm__project=project
        ).delete()
        models.CachedPrediction.objects.filter(
            pca_predictions__cacheddeepssm__project=project
        ).delete()

    def post_command_function(project, download_dir, result_data, project_filename):
        print(result_data)
        # save project file changes to database
        project.file.save(
            project_filename,
            open(Path(download_dir, project_filename), 'rb'),
        )

    run_deepssm_command(
        user_id,
        project_id,
        form_data,
        'test',
        pre_command_function,
        post_command_function,
        progress_id,
    )
