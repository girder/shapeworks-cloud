import base64
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Type

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import GenericViewSet

from . import filters, models, serializers
from .tasks import groom, optimize


def save_thumbnail_image(target, encoded_thumbnail):
    if encoded_thumbnail:
        with TemporaryDirectory() as download_dir:
            target_path = Path(download_dir) / 'thumbnail.png'
            with open(target_path, 'wb') as fh:
                fh.write(base64.b64decode((encoded_thumbnail)))
            target.thumbnail.save('thumbnail.png', open(target_path, 'rb'))


class Pagination(PageNumberPagination):
    page_size = 25
    max_page_size = 100
    page_size_query_param = 'page_size'


class BaseViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = Pagination

    serializer_class_dict: Dict[str, Type[BaseSerializer]] = {}
    serializer_class: Type[BaseSerializer]

    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self) -> Type[BaseSerializer]:
        return self.serializer_class_dict.get(self.action, self.serializer_class)


class DatasetViewSet(BaseViewSet):
    serializer_class = serializers.DatasetSerializer
    filterset_class = filters.DatasetFilter

    def get_queryset(self):
        user = self.request.user
        if user.is_anonymous:
            return models.Dataset.objects.none()
        return models.Dataset.objects.filter(Q(private=False) | Q(creator=user)).order_by('name')

    def perform_create(self, serializer):
        user = None
        if self.request and hasattr(self.request, 'user'):
            user = self.request.user
        serializer.save(creator=user)

    @action(
        detail=True,
        url_path='thumbnail',
        url_name='thumbnail',
        methods=['POST'],
    )
    def set_thumbnail(self, request, **kwargs):
        dataset = self.get_object()
        form_data = request.data
        encoded_thumbnail = form_data.get('encoding')
        save_thumbnail_image(dataset, encoded_thumbnail)
        return Response(serializers.DatasetSerializer(dataset).data)

    @action(
        detail=True,
        url_path='subset',
        url_name='subset',
        methods=['POST'],
    )
    def subset(self, request, **kwargs):
        dataset = self.get_object()
        form_data = request.data
        selected = form_data.get('selected')
        name = form_data.get('name') or dataset.name + '_subset'
        if len(selected) < 1:
            return Response(
                'Cannot make dataset from empty subset.', status=status.HTTP_400_BAD_REQUEST
            )
        if models.Dataset.objects.filter(name=name).count() > 0:
            return Response(f'Dataset {name} already exists.', status=status.HTTP_400_BAD_REQUEST)
        new_dataset = models.Dataset.objects.create(
            name=name,
            description=form_data.get('description') or dataset.description,
            keywords=form_data.get('keywords') or dataset.keywords,
            # the following attributes are inherited directly
            license=dataset.license,
            acknowledgement=dataset.acknowledgement,
            contributors=dataset.contributors,
            publications=dataset.publications,
        )
        for datum in selected:
            target_subject = models.Subject.objects.get(id=datum['subject'])
            new_subject = models.Subject.objects.create(
                name=target_subject.name, dataset=new_dataset
            )
            if datum['type'] == 'mesh':
                target_object = models.Mesh.objects.get(id=datum['id'])
            elif datum['type'] == 'segmentation':
                target_object = models.Segmentation.objects.get(id=datum['id'])
            # clone object with new subject
            target_object.id = None
            target_object.subject = new_subject
            target_object.save()
        return Response(serializers.DatasetSerializer(new_dataset).data)


class SubjectViewSet(BaseViewSet):
    queryset = models.Subject.objects.all().order_by('name')
    serializer_class = serializers.SubjectSerializer
    filterset_class = filters.SubjectFilter


class SegmentationViewSet(BaseViewSet):
    queryset = models.Segmentation.objects.all().order_by('subject')
    serializer_class = serializers.SegmentationSerializer
    filterset_class = filters.SegmentationFilter


class MeshViewSet(BaseViewSet):
    queryset = models.Mesh.objects.all().order_by('subject')
    serializer_class = serializers.MeshSerializer
    filterset_class = filters.MeshFilter


class ContourViewSet(BaseViewSet):
    queryset = models.Contour.objects.all().order_by('subject')
    serializer_class = serializers.ContourSerializer
    filterset_class = filters.ContourFilter


class ImageViewSet(BaseViewSet):
    queryset = models.Image.objects.all().order_by('subject')
    serializer_class = serializers.ImageSerializer
    filterset_class = filters.ImageFilter


class LandmarksViewSet(BaseViewSet):
    queryset = models.Landmarks.objects.all().order_by('subject')
    serializer_class = serializers.LandmarksSerializer
    filterset_class = filters.LandmarksFilter


class ConstraintsViewSet(BaseViewSet):
    queryset = models.Constraints.objects.all().order_by('subject')
    serializer_class = serializers.ConstraintsSerializer
    filterset_class = filters.ConstraintsFilter


class ProjectViewSet(BaseViewSet):
    queryset = models.Project.objects.all()
    filterset_class = filters.ProjectFilter

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return serializers.ProjectReadSerializer
        else:
            return serializers.ProjectSerializer

    def create(self, request, **kwargs):
        serializer = serializers.ProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save()
        if not project.file:
            project.create_new_file()
        return Response(
            serializers.ProjectReadSerializer(project).data, status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        url_path='thumbnail',
        url_name='thumbnail',
        methods=['POST'],
    )
    def set_thumbnail(self, request, **kwargs):
        project = self.get_object()
        form_data = request.data
        encoded_thumbnail = form_data.get('encoding')
        save_thumbnail_image(project, encoded_thumbnail)
        return Response(serializers.ProjectReadSerializer(project).data)

    @action(
        detail=True,
        url_path='groom',
        url_name='groom',
        methods=['POST'],
    )
    def groom(self, request, **kwargs):
        project = self.get_object()
        form_data = request.data
        form_data = {k: str(v) for k, v in form_data.items()}

        models.TaskProgress.objects.filter(name='groom', project=project).delete()
        progress = models.TaskProgress.objects.create(name='groom', project=project)
        groom.delay(request.user.id, project.id, form_data, progress.id)
        return Response(
            data={'groom_task': serializers.TaskProgressSerializer(progress).data},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        url_path='optimize',
        url_name='optimize',
        methods=['POST'],
    )
    def optimize(self, request, **kwargs):
        project = self.get_object()
        form_data = request.data
        form_data = {k: str(v) for k, v in form_data.items()}

        models.TaskProgress.objects.filter(name='optimize', project=project).delete()
        models.TaskProgress.objects.filter(name='analyze', project=project).delete()

        progress = models.TaskProgress.objects.create(name='optimize', project=project)
        analysis_progress = models.TaskProgress.objects.create(name='analyze', project=project)
        optimize.delay(
            request.user.id,
            project.id,
            form_data,
            progress.id,
            analysis_progress.id,
        )
        return Response(
            data={
                'optimize_task': serializers.TaskProgressSerializer(progress).data,
                'analyze_task': serializers.TaskProgressSerializer(analysis_progress).data,
            },
            status=status.HTTP_200_OK,
        )


class GroomedSegmentationViewSet(BaseViewSet):
    queryset = models.GroomedSegmentation.objects.all()
    serializer_class = serializers.GroomedSegmentationSerializer
    filterset_class = filters.GroomedSegmentationFilter


class GroomedMeshViewSet(BaseViewSet):
    queryset = models.GroomedMesh.objects.all()
    serializer_class = serializers.GroomedMeshSerializer
    filterset_class = filters.GroomedMeshFilter


class OptimizedParticlesViewSet(BaseViewSet):
    queryset = models.OptimizedParticles.objects.all()
    serializer_class = serializers.OptimizedParticlesSerializer
    filterset_class = filters.OptimizedParticlesFilter


class CachedAnalysisViewSet(BaseViewSet):
    queryset = models.CachedAnalysis.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return serializers.CachedAnalysisReadSerializer
        else:
            return serializers.CachedAnalysisSerializer


class CachedAnalysisModeViewSet(BaseViewSet):
    queryset = models.CachedAnalysisMode.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return serializers.CachedAnalysisModeReadSerializer
        else:
            return serializers.CachedAnalysisModeSerializer


class CachedAnalysisModePCAViewSet(BaseViewSet):
    queryset = models.CachedAnalysisModePCA.objects.all()
    serializer_class = serializers.CachedAnalysisModePCASerializer


class ReconstructedSampleViewSet(
    GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
):
    queryset = models.ReconstructedSample.objects.all()
    serializer_class = serializers.ReconstructedSampleSerializer
    filterset_class = filters.ReconstructedSampleFilter


class TaskProgressViewSet(
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = models.TaskProgress.objects.all()
    serializer_class = serializers.TaskProgressSerializer

    @action(
        detail=True,
        url_path='abort',
        url_name='abort',
        methods=['POST'],
    )
    def abort(self, request, **kwargs):
        progress = self.get_object()
        for task in models.TaskProgress.objects.filter(project=progress.project):
            task.abort = True
            task.save(update_fields=['abort'])
        return Response(
            status=status.HTTP_200_OK,
        )
