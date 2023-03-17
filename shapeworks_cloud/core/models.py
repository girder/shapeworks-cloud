import json

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import models
from django_extensions.db.models import TimeStampedModel
from s3_file_field import S3FileField


class Dataset(TimeStampedModel, models.Model):
    name = models.CharField(max_length=255, unique=True)
    private = models.BooleanField(default=False)
    creator = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    thumbnail = S3FileField(null=True)
    license = models.TextField()
    description = models.TextField()
    acknowledgement = models.TextField()
    keywords = models.CharField(max_length=255, blank=True, default='')
    contributors = models.TextField(blank=True, default='')
    publications = models.TextField(blank=True, default='')

    def get_contents(self):
        ret = []

        def truncate_filename(filename):
            return filename.split('/')[-1]

        for shape_group in [
            Segmentation.objects.filter(subject__dataset=self),
            Mesh.objects.filter(subject__dataset=self),
            Image.objects.filter(subject__dataset=self),
            Contour.objects.filter(subject__dataset=self),
        ]:
            for shape in shape_group:
                ret.append(
                    {
                        'name': shape.subject.name,
                        'shape_1': truncate_filename(shape.file.name),
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


class CachedAnalysis(TimeStampedModel, models.Model):
    mean_shape = S3FileField()
    mean_particles = S3FileField(null=True)
    modes = models.ManyToManyField(CachedAnalysisMode)
    charts = models.JSONField()


class Project(TimeStampedModel, models.Model):
    file = S3FileField()
    thumbnail = S3FileField(null=True)
    keywords = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='projects')
    last_cached_analysis = models.ForeignKey(CachedAnalysis, on_delete=models.SET_NULL, null=True)

    def create_new_file(self):
        file_contents = {
            'data': self.dataset.get_contents(),
            'groom': {},
            'optimize': {},
        }
        self.file.save(
            f'{self.dataset.name}.swproj', ContentFile(json.dumps(file_contents).encode())
        )


class GroomedSegmentation(TimeStampedModel, models.Model):
    # The contents of the nrrd file
    file = S3FileField()

    # represent these in raw form?
    pre_cropping = S3FileField(null=True)
    pre_alignment = S3FileField(null=True)

    segmentation = models.ForeignKey(
        Segmentation,
        on_delete=models.CASCADE,
        related_name='groomed',
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
        on_delete=models.CASCADE,
        related_name='groomed',
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='groomed_meshes')


class OptimizedParticles(TimeStampedModel, models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    world = S3FileField(null=True)
    local = S3FileField(null=True)
    transform = S3FileField(null=True)

    groomed_segmentation = models.ForeignKey(
        GroomedSegmentation,
        on_delete=models.CASCADE,
        related_name='+',
        blank=True,
        null=True,
    )
    groomed_mesh = models.ForeignKey(
        GroomedMesh,
        on_delete=models.CASCADE,
        related_name='+',
        blank=True,
        null=True,
    )


class Landmarks(TimeStampedModel, models.Model):
    file = S3FileField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='landmarks')


class Constraints(TimeStampedModel, models.Model):
    file = S3FileField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='constraints')
    optimized_particles = models.ForeignKey(
        OptimizedParticles, on_delete=models.CASCADE, related_name='constraints', null=True
    )


class ReconstructedSample(TimeStampedModel, models.Model):
    file = S3FileField()
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='reconstructed_samples'
    )
    particles = models.ForeignKey(
        OptimizedParticles, on_delete=models.CASCADE, related_name='reconstructed_samples'
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
