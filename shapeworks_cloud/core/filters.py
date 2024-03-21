from django.db.models import Q
from django_filters import CharFilter, FilterSet, ModelChoiceFilter

from . import models


class DatasetFilter(FilterSet):
    search = CharFilter(method='multifield_search')

    def multifield_search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
            | Q(keywords__icontains=value)
        )

    class Meta:
        model = models.Dataset
        fields = ['name', 'search']


class SubjectFilter(FilterSet):
    dataset = ModelChoiceFilter(queryset=models.Dataset.objects.all())

    class Meta:
        model = models.Subject
        fields = ['dataset']


class ProjectFilter(FilterSet):
    dataset = ModelChoiceFilter(queryset=models.Dataset.objects.all())
    search = CharFilter(method='multifield_search')

    def multifield_search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
            | Q(keywords__icontains=value)
        )

    class Meta:
        model = models.Project
        fields = ['search', 'dataset']


class SegmentationFilter(FilterSet):
    subject = ModelChoiceFilter(queryset=models.Subject.objects.all())

    class Meta:
        models = models.Segmentation
        fields = ['subject']


class MeshFilter(FilterSet):
    subject = ModelChoiceFilter(queryset=models.Subject.objects.all())

    class Meta:
        models = models.Mesh
        fields = ['subject']


class ContourFilter(FilterSet):
    subject = ModelChoiceFilter(queryset=models.Subject.objects.all())

    class Meta:
        models = models.Contour
        fields = ['subject']


class ImageFilter(FilterSet):
    subject = ModelChoiceFilter(queryset=models.Subject.objects.all())

    class Meta:
        models = models.Image
        fields = ['subject']


class LandmarksFilter(FilterSet):
    subject = ModelChoiceFilter(queryset=models.Subject.objects.all())

    class Meta:
        models = models.Landmarks
        fields = ['subject']


class ConstraintsFilter(FilterSet):
    subject = ModelChoiceFilter(queryset=models.Subject.objects.all())

    class Meta:
        models = models.Constraints
        fields = ['subject']


class GroomedSegmentationFilter(FilterSet):
    project = ModelChoiceFilter(queryset=models.Project.objects.all())
    segmentation = ModelChoiceFilter(queryset=models.Segmentation.objects.all())

    class Meta:
        models = models.GroomedSegmentation
        fields = ['project', 'segmentation']


class GroomedMeshFilter(FilterSet):
    project = ModelChoiceFilter(queryset=models.Project.objects.all())
    mesh = ModelChoiceFilter(queryset=models.Mesh.objects.all())

    class Meta:
        models = models.GroomedMesh
        fields = ['project', 'mesh']


class OptimizedParticlesFilter(FilterSet):
    project = ModelChoiceFilter(queryset=models.Project.objects.all())
    original_segmentation = ModelChoiceFilter(
        field_name='groomed_segmentation__segmentation',
        queryset=models.Segmentation.objects.all(),
    )
    original_mesh = ModelChoiceFilter(
        field_name='groomed_mesh__mesh',
        queryset=models.Mesh.objects.all(),
    )
    groomed_segmentation = ModelChoiceFilter(queryset=models.GroomedSegmentation.objects.all())
    groomed_mesh = ModelChoiceFilter(queryset=models.GroomedMesh.objects.all())

    class Meta:
        models = models.OptimizedParticles
        fields = [
            'project',
            'shape_model',
            'groomed_segmentation',
            'groomed_mesh',
            'original_segmentation',
            'original_mesh',
        ]


class ReconstructedSampleFilter(FilterSet):
    project = ModelChoiceFilter(queryset=models.Project.objects.all())

    class Meta:
        models = models.ReconstructedSample
        fields = ['project']


class DeepSSMTestingDataFilter(FilterSet):
    project = ModelChoiceFilter(queryset=models.Project.objects.all())

    class Meta:
        models = models.DeepSSMTestingData
        fields = ['project']


class DeepSSMTrainingImageFilter(FilterSet):
    project = ModelChoiceFilter(queryset=models.Project.objects.all())

    class Meta:
        models = models.DeepSSMTrainingImage
        fields = ['project']


class DeepSSMAugPairFilter(FilterSet):
    project = ModelChoiceFilter(queryset=models.Project.objects.all())

    class Meta:
        models = models.DeepSSMAugPair
        fields = ['project']


class DeepSSMResultFilter(FilterSet):
    project = ModelChoiceFilter(queryset=models.Project.objects.all())

    class Meta:
        models = models.DeepSSMResult
        fields = ['project']
