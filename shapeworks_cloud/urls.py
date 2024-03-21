from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_extensions.routers import ExtendedSimpleRouter

from shapeworks_cloud.core import rest

router = ExtendedSimpleRouter()
router.register('datasets', rest.DatasetViewSet, basename='dataset')
router.register('subjects', rest.SubjectViewSet, basename='subject')
router.register('segmentations', rest.SegmentationViewSet, basename='segmentation')
router.register('meshes', rest.MeshViewSet, basename='mesh')
router.register('contours', rest.ContourViewSet, basename='contour')
router.register('images', rest.ImageViewSet, basename='image')
router.register('projects', rest.ProjectViewSet, basename='project')
router.register(
    'groomed-segmentations', rest.GroomedSegmentationViewSet, basename='groomed_segmentation'
)
router.register('groomed-meshes', rest.GroomedMeshViewSet, basename='groomed_mesh')
router.register(
    'optimized-particles', rest.OptimizedParticlesViewSet, basename='optimized_particles'
)
router.register('landmarks', rest.LandmarksViewSet, basename='landmarks')
router.register('constraints', rest.ConstraintsViewSet, basename='constraints')
router.register('cached-analysis', rest.CachedAnalysisViewSet, basename='cached_analysis')
router.register(
    'cached-analysis-mode', rest.CachedAnalysisModeViewSet, basename='cached_analysis_mode'
)
router.register(
    'cached-analysis-mode-pca',
    rest.CachedAnalysisModePCAViewSet,
    basename='cached_analysis_mode_pca',
)
router.register(
    'cached-analysis-group',
    rest.CachedAnalysisGroupViewSet,
    basename='cached_analysis_group',
)
router.register(
    'cached-analysis-mean-shape',
    rest.CachedAnalysisMeanShapeViewSet,
    basename='cached_analysis_mean_shape',
)
router.register(
    'reconstructed-samples', rest.ReconstructedSampleViewSet, basename='reconstructed_sample'
)
router.register('task-progress', rest.TaskProgressViewSet, basename='task_progress')

# ----------------
# DeepSSM
# ----------------
router.register(
    'deepssm-testing-data',
    rest.DeepSSMTestingDataViewSet,
    basename='deepssm_testing_data',
)

router.register(
    'deepssm-training-image',
    rest.DeepSSMTrainingImageViewSet,
    basename='deepssm_training_image',
)

router.register(
    'deepssm-aug-pair',
    rest.DeepSSMAugPairViewSet,
    basename='deepssm_aug_pair',
)

router.register(
    'deepssm-result',
    rest.DeepSSMResultViewSet,
    basename='deepssm_result',
)

# OpenAPI generation
schema_view = get_schema_view(
    openapi.Info(title='ShapeWorks Cloud', default_version='v1', description=''),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('accounts/', include('allauth.urls')),
    path('oauth/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('admin/', admin.site.urls),
    path('api/v1/logout/', rest.LogoutView.as_view()),
    path('api/v1/s3-upload/', include('s3_file_field.urls', namespace='s3ff')),
    path('api/v1/', include(router.urls)),
    path('api/docs/redoc/', schema_view.with_ui('redoc'), name='docs-redoc'),
    path('api/docs/swagger/', schema_view.with_ui('swagger'), name='docs-swagger'),
    path('api-token-auth/', obtain_auth_token),
    path('', RedirectView.as_view(url=settings.HOMEPAGE_REDIRECT_URL)),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
