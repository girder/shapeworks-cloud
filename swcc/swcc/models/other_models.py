from __future__ import annotations

try:
    from typing import List, Literal, Optional
except ImportError:
    from typing import (
        List,
        Optional,
    )
    from typing_extensions import (  # type: ignore
        Literal,
    )

from .api_model import ApiModel
from .file_type import FileType
from .utils import NonEmptyString


class Segmentation(ApiModel):
    _endpoint = 'segmentations'

    file: FileType[Literal['core.Segmentation.file']]
    anatomy_type: NonEmptyString
    subject: Subject


class Mesh(ApiModel):
    _endpoint = 'meshes'

    file: FileType[Literal['core.Mesh.file']]
    anatomy_type: NonEmptyString
    subject: Subject


class Contour(ApiModel):
    _endpoint = 'contours'

    file: FileType[Literal['core.Contour.file']]
    anatomy_type: NonEmptyString
    subject: Subject


class Image(ApiModel):
    _endpoint = 'images'

    file: FileType[Literal['core.Image.file']]
    modality: str
    subject: Subject


class GroomedSegmentation(ApiModel):
    _endpoint = 'groomed-segmentations'

    file: Optional[FileType[Literal['core.GroomedSegmentation.file']]]
    pre_cropping: Optional[FileType[Literal['core.GroomedSegmentation.pre_cropping']]] = None
    pre_alignment: Optional[FileType[Literal['core.GroomedSegmentation.pre_alignment']]] = None

    segmentation: Segmentation
    project: Project


class GroomedMesh(ApiModel):
    _endpoint = 'groomed-meshes'

    file: Optional[FileType[Literal['core.GroomedMesh.file']]]
    pre_cropping: Optional[FileType[Literal['core.GroomedMesh.pre_cropping']]] = None
    pre_alignment: Optional[FileType[Literal['core.GroomedMesh.pre_alignment']]] = None

    mesh: Mesh
    project: Project


class OptimizedParticles(ApiModel):
    _endpoint = 'optimized-particles'

    world: Optional[FileType[Literal['core.OptimizedParticles.world']]]
    local: Optional[FileType[Literal['core.OptimizedParticles.local']]]
    transform: Optional[FileType[Literal['core.OptimizedParticles.transform']]]
    project: Project
    subject: Subject
    anatomy_type: NonEmptyString
    groomed_segmentation: Optional[GroomedSegmentation]
    groomed_mesh: Optional[GroomedMesh]


class Landmarks(ApiModel):
    _endpoint = 'landmarks'

    file: Optional[FileType[Literal['core.Landmarks.file']]]
    subject: Subject
    anatomy_type: NonEmptyString
    project: Project


class Constraints(ApiModel):
    _endpoint = 'constraints'

    file: Optional[FileType[Literal['core.Constraints.file']]]
    subject: Subject
    anatomy_type: NonEmptyString
    optimized_particles: Optional[OptimizedParticles]


class CachedAnalysisGroup(ApiModel):
    _endpoint = 'cached-analysis-group'

    file: FileType[Literal['core.CachedAnalysisGroup.file']]
    particles: Optional[FileType[Literal['core.CachedAnalysisGroup.particles']]]
    name: NonEmptyString
    group1: NonEmptyString
    group2: NonEmptyString
    ratio: float


class CachedAnalysisModePCA(ApiModel):
    _endpoint = 'cached-analysis-mode-pca'

    pca_value: float
    lambda_value: float
    file: FileType[Literal['core.CachedAnalysisModePCA.file']]
    particles: FileType[Literal['core.CachedAnalysisModePCA.particles']]


class CachedAnalysisMode(ApiModel):
    _endpoint = 'cached-analysis-mode'

    mode: int
    eigen_value: float
    explained_variance: float
    cumulative_explained_variance: float
    pca_values: List[CachedAnalysisModePCA]


class CachedAnalysisMeanShape(ApiModel):
    _endpoint = 'cached-analysis-mean-shape'

    file: FileType[Literal['core.CachedAnalysisMeanShape.file']]
    particles: FileType[Literal['core.CachedAnalysisMeanShape.particles']]


class CachedAnalysis(ApiModel):
    _endpoint = 'cached-analysis'

    mean_shapes: List[CachedAnalysisMeanShape]
    modes: List[CachedAnalysisMode]
    charts: List[dict]
    groups: Optional[List[CachedAnalysisGroup]]
    good_bad_angles: List[list]


class CachedPrediction(ApiModel):
    _endpoint = 'cached-prediction'

    particles: Literal['core.CachedPrediction.particles']


class CachedExample(ApiModel):
    _endpoint = 'cached-example'

    train_particles: Literal['core.CachedExample.train_particles']
    train_scalars: Literal['core.CachedExample.train_scalars']
    validation_particles: Literal['core.CachedExample.validation_particles']
    validation_scalars: Literal['core.CachedExample.validation_scalars']


class CachedModelExamples(ApiModel):
    _endpoint = 'cached-model-examples'

    best: CachedExample
    median: CachedExample
    worst: CachedExample


class CachedModel(ApiModel):
    _endpoint = 'cached-model'

    configuration: Literal['core.CachedModel.configuration']
    best_model: Literal['core.CachedModel.best_model']
    final_model: Literal['core.CachedModel.final_model']
    examples: CachedModelExamples
    pca_predictions: List[CachedPrediction]
    ft_predictions: List[CachedPrediction]
    train_log_ft: Optional[Literal['core.CachedModel.train_log_ft']]
    best_model_ft: Optional[Literal['core.CachedModel.best_model_ft']]
    final_model_ft: Optional[Literal['core.CachedModel.final_model_ft']]


class CachedTensors(ApiModel):
    _endpoint = 'cached-tensors'

    train: Literal['core.CachedTensors.train']
    validation: Literal['core.CachedTensors.validation']
    test: Literal['core.CachedTensors.test']


class CachedDataLoaders(ApiModel):
    _endpoint = 'cached-data-loaders'

    mean_pca: Literal['core.CachedDataLoaders.mean_pca']
    std_pca: Literal['core.CachedDataLoaders.std_pca']
    test_names: Literal['core.CachedDataLoaders.test_names']
    tensors: CachedTensors


class CachedAugmentationPair(ApiModel):
    _endpoint = 'cached-augmentation-pair'

    file: Literal['core.CachedAugmentationPair.file']
    particles: Literal['core.CachedAugmentationPair.particles']


class CachedAugmentation(ApiModel):
    _endpoint = 'cached-augmentation'

    pairs: List[CachedAugmentationPair]
    total_data_csv: Literal['core.CachedAugmentation.total_data_csv']
    violin_plot: Literal['core.CachedAugmentation.violin_plot']


class CachedDeepSSM(ApiModel):
    _endpoint = 'cached-deep-ssm'

    augmentation: CachedAugmentation
    data_loaders: CachedDataLoaders
    model: CachedModel


from .project import Project  # noqa: E402
from .subject import Subject  # noqa: E402

Segmentation.update_forward_refs()
Mesh.update_forward_refs()
Contour.update_forward_refs()
Image.update_forward_refs()
GroomedSegmentation.update_forward_refs()
GroomedMesh.update_forward_refs()
OptimizedParticles.update_forward_refs()
Landmarks.update_forward_refs()
Constraints.update_forward_refs()
