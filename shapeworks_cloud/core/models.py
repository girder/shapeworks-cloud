import json

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import models
from django_extensions.db.models import TimeStampedModel
from s3_file_field import S3FileField


class Dataset(TimeStampedModel, models.Model):
    name = models.CharField(max_length=255, unique=True)
    private = models.BooleanField(default=False)
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    thumbnail = S3FileField(null=True, blank=True)
    license = models.TextField()
    description = models.TextField()
    acknowledgement = models.TextField()
    keywords = models.CharField(max_length=255, blank=True, default='')
    contributors = models.TextField(blank=True, default='')
    publications = models.TextField(blank=True, default='')

    def get_contents(self, type='all'):
        ret = []

        def truncate_filename(filename):
            return filename.split('/')[-1]

        if type == 'all':
            group_list = [
                Segmentation.objects.filter(subject__dataset=self),
                Mesh.objects.filter(subject__dataset=self),
                Image.objects.filter(subject__dataset=self),
                Contour.objects.filter(subject__dataset=self),
            ]
        elif type == 'shape':
            group_list = [
                Segmentation.objects.filter(subject__dataset=self),
                Mesh.objects.filter(subject__dataset=self),
            ]
        elif type == 'image':
            group_list = [Image.objects.filter(subject__dataset=self)]
        elif type == 'contour':
            group_list = [Contour.objects.filter(subject__dataset=self)]

        for shape_group in group_list:
            for shape in shape_group:
                ret.append(
                    {
                        'name': shape.subject.name,  # type: ignore
                        'shape_1': truncate_filename(shape.file.name),  # type: ignore
                    }
                )
        return ret


class Subject(TimeStampedModel, models.Model):
    name = models.CharField(max_length=255)
    groups = models.JSONField(null=True, blank=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='subjects')


class Segmentation(TimeStampedModel, models.Model):
    file = S3FileField()
    anatomy_type = models.CharField(max_length=255)  # choices?
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='segmentations')


class Mesh(TimeStampedModel, models.Model):
    file = S3FileField()
    anatomy_type = models.CharField(max_length=255)  # choices?
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='meshes')


class Contour(TimeStampedModel, models.Model):
    file = S3FileField()
    anatomy_type = models.CharField(max_length=255)  # choices?
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='contours')


class Image(TimeStampedModel, models.Model):
    file = S3FileField()
    modality = models.CharField(max_length=255)  # choices?
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='images')


class CachedAnalysisGroup(models.Model):
    name = models.CharField(max_length=255, default='')
    group1 = models.CharField(max_length=255, default='')
    group2 = models.CharField(max_length=255, default='')
    ratio = models.FloatField(default=0.0)
    file = S3FileField()
    particles = S3FileField(null=True)


class CachedAnalysisModePCA(models.Model):
    pca_value = models.FloatField()
    lambda_value = models.FloatField()
    file = S3FileField()
    particles = S3FileField(null=True)


class CachedAnalysisMode(models.Model):
    mode = models.IntegerField()
    eigen_value = models.FloatField()
    explained_variance = models.FloatField()
    cumulative_explained_variance = models.FloatField()
    pca_values = models.ManyToManyField(CachedAnalysisModePCA)


class CachedAnalysisMeanShape(models.Model):
    file = S3FileField()
    particles = S3FileField(null=True)


class CachedAnalysis(TimeStampedModel, models.Model):
    mean_shapes = models.ManyToManyField(CachedAnalysisMeanShape)
    modes = models.ManyToManyField(CachedAnalysisMode)
    charts = models.JSONField()
    groups = models.ManyToManyField(CachedAnalysisGroup, blank=True)
    good_bad_angles = models.JSONField(default=list)


class Project(TimeStampedModel, models.Model):
    file = S3FileField()
    name = models.CharField(max_length=255)
    private = models.BooleanField(default=False)
    readonly = models.BooleanField(default=False)
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    thumbnail = S3FileField(null=True, blank=True)
    keywords = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='projects')
    landmarks_info = models.JSONField(default=list, null=True)
    last_cached_analysis = models.ForeignKey(
        CachedAnalysis,
        on_delete=models.SET_NULL,
        null=True,
    )

    def create_new_file(self):
        file_contents = {
            'data': self.dataset.get_contents(),
            'groom': {},
            'optimize': {},
        }
        self.file.save(
            f'{self.dataset.name}.swproj', ContentFile(json.dumps(file_contents).encode())
        )

    def get_download_paths(self):
        print('get_download_paths')
        ret = {}
        with self.file.open() as f:
            data = json.load(f)['data']

        print(data)
        for subject_info in data:
            subject = Subject.objects.filter(
                dataset=self.dataset, name=subject_info['name']
            ).first()
            if subject:
                particles = OptimizedParticles.objects.filter(project=self, subject=subject)
                related_files = {
                    'mesh': [(m.anatomy_type, m.file) for m in subject.meshes.all()],
                    'segmentation': [(s.anatomy_type, s.file) for s in subject.segmentations.all()],
                    'contour': [(c.anatomy_type, c.file) for c in subject.contours.all()],
                    'image': [(i.modality, i.file) for i in subject.images.all()],
                    'constraints': [(c.anatomy_type, c.file) for c in subject.constraints.all()],
                    'landmarks': [
                        (lm.anatomy_type, lm.file)
                        for lm in Landmarks.objects.filter(project=self, subject=subject)
                    ],
                    'groomed': [
                        (gm.mesh.anatomy_type, gm.file)
                        for gm in GroomedMesh.objects.filter(project=self, mesh__subject=subject)
                        if gm.mesh
                    ]
                    + [
                        (gs.segmentation.anatomy_type, gs.file)
                        for gs in GroomedSegmentation.objects.filter(
                            project=self, segmentation__subject=subject
                        )
                        if gs.segmentation
                    ],
                    'local': [(p.anatomy_type, p.local) for p in particles if p.local],
                    'world': [(p.anatomy_type, p.world) for p in particles if p.world],
                }
                related_files['shape'] = (
                    related_files['mesh']
                    + related_files['segmentation']
                    + related_files['contour']
                    + related_files['image']
                )

                for key, value in subject_info.items():
                    prefix = key.split('_')[0]
                    suffix = key.split('_')[-1]
                    target_file = None
                    if prefix in related_files:
                        for related in related_files[prefix]:
                            if not target_file:
                                # subject and anatomy type must match
                                if suffix == related[0].replace('anatomy_', ''):
                                    target_file = related[1].url
                    if target_file:
                        value = value.replace('../', '')
                        ret[value] = target_file
        return ret


class CachedDeepSSMTestingData(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    mean_distance = models.FloatField()
    mesh = S3FileField()
    particles = S3FileField()


class CachedDeepSSMTesting(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='deepssm_testing'
    )
    testing_data = models.ForeignKey(CachedDeepSSMTestingData, on_delete=models.CASCADE)


class CachedDeepSSMTraining(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='deepssm_training'
    )
    visualization = S3FileField()  # .png
    data_table = S3FileField()  # .csv


class CachedDeepSSMAugPair(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    mesh = S3FileField()
    particles = S3FileField()


class CachedDeepSSMAug(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='deepssm_aug'
    )
    visualization = S3FileField()  # .png
    aug_pair = models.ForeignKey(CachedDeepSSMAugPair, on_delete=models.CASCADE)


class CachedDeepSSMResult(TimeStampedModel, models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='cached_deepssm'
    )
    augmentation = models.ForeignKey(CachedDeepSSMAug, on_delete=models.CASCADE)
    training = models.ForeignKey(CachedDeepSSMTraining, null=True, on_delete=models.CASCADE)
    testing = models.ForeignKey(CachedDeepSSMTestingData, null=True, on_delete=models.CASCADE)


class GroomedSegmentation(TimeStampedModel, models.Model):
    # The contents of the nrrd file
    file = S3FileField()

    # represent these in raw form?
    pre_cropping = S3FileField(null=True)
    pre_alignment = S3FileField(null=True)

    segmentation = models.ForeignKey(
        Segmentation,
        on_delete=models.SET_NULL,
        related_name='groomed',
        null=True,
    )

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='groomed_segmentations'
    )


class GroomedMesh(TimeStampedModel, models.Model):
    # The contents of the nrrd file
    file = S3FileField()

    # represent these in raw form?
    pre_cropping = S3FileField(null=True)
    pre_alignment = S3FileField(null=True)

    mesh = models.ForeignKey(
        Mesh,
        on_delete=models.SET_NULL,
        related_name='groomed',
        null=True,
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='groomed_meshes')


class OptimizedParticles(TimeStampedModel, models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    world = S3FileField(null=True)
    local = S3FileField(null=True)
    transform = S3FileField(null=True)
    anatomy_type = models.CharField(max_length=255)
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name='particles', null=True
    )

    groomed_segmentation = models.ForeignKey(
        GroomedSegmentation,
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True,
    )
    groomed_mesh = models.ForeignKey(
        GroomedMesh,
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True,
    )


class Landmarks(TimeStampedModel, models.Model):
    file = S3FileField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='landmarks')
    anatomy_type = models.CharField(max_length=255)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='landmarks', null=True
    )


class Constraints(TimeStampedModel, models.Model):
    file = S3FileField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='constraints')
    anatomy_type = models.CharField(max_length=255)
    optimized_particles = models.ForeignKey(
        OptimizedParticles,
        on_delete=models.SET_NULL,
        related_name='constraints',
        null=True,
    )


class ReconstructedSample(TimeStampedModel, models.Model):
    file = S3FileField()
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='reconstructed_samples'
    )
    particles = models.ForeignKey(
        OptimizedParticles,
        on_delete=models.SET_NULL,
        related_name='reconstructed_samples',
        null=True,
    )


class TaskProgress(TimeStampedModel, models.Model):
    name = models.CharField(max_length=255)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    error = models.CharField(max_length=255)
    percent_complete = models.IntegerField(default=0)
    abort = models.BooleanField(default=False)

    def update_percentage(self, percentage):
        self.percent_complete = percentage
        self.save()

    def update_error(self, error):
        self.error = error[:255]
        self.save()
