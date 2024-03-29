from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from factory import Factory, Faker, Sequence, SubFactory
from faker.providers import BaseProvider, file as file_provider, python as python_provider

from swcc import models


class FileUploadProvider(BaseProvider):
    _directory: Path

    def file(self, category=None, extension=None, null_chance=0):
        if self.generator.boolean(null_chance):
            return
        file_name = self.generator.file_name(extension=extension, category=category)
        file_path = self._directory / file_name
        with file_path.open('wb') as f:
            f.write(b' ')

        return file_path


Faker.add_provider(python_provider)
Faker.add_provider(file_provider)
Faker.add_provider(FileUploadProvider)


@contextmanager
def file_context():
    with TemporaryDirectory() as directory:
        p = Path(directory)
        FileUploadProvider._directory = p
        yield p

    del FileUploadProvider._directory


Faker.add_provider(FileUploadProvider)


class DatasetFactory(Factory):
    class Meta:
        model = models.Dataset

    name = Sequence(lambda n: f'dataset_{n}')
    license = Faker('sentence')
    description = Faker('sentence')
    acknowledgement = Faker('sentence')
    keywords = Faker('word')
    contributors = Faker('name')


class SubjectFactory(Factory):
    class Meta:
        model = models.Subject

    name = Sequence(lambda n: f'subject_{n}')
    dataset = SubFactory(DatasetFactory)


class SegmentationFactory(Factory):
    class Meta:
        model = models.Segmentation

    file_source = Faker('file', extension='nrrd')
    anatomy_type = Faker('word')
    subject = SubFactory(SubjectFactory)


class MeshFactory(Factory):
    class Meta:
        model = models.Mesh

    file_source = Faker('file', extension='ply')
    anatomy_type = Faker('word')
    subject = SubFactory(SubjectFactory)


class ImageFactory(Factory):
    class Meta:
        model = models.Image

    file_source = Faker('file', extension='nrrd')
    modality = Faker('word')
    subject = SubFactory(SubjectFactory)


class ProjectFactory(Factory):
    class Meta:
        model = models.Project

    file_source = './tests/test_data/project_demo.swproj'
    keywords = Faker('word')
    description = Faker('sentence')
    dataset = SubFactory(DatasetFactory)


class GroomedSegmentationFactory(Factory):
    class Meta:
        model = models.GroomedSegmentation

    file_source = Faker('file', extension='nrrd')
    pre_cropping_source = Faker('file', extension='txt', null_chance=50)
    pre_alignment_source = Faker('file', extension='txt', null_chance=50)

    segmentation = SubFactory(SegmentationFactory)
    project = SubFactory(ProjectFactory)


class GroomedMeshFactory(Factory):
    class Meta:
        model = models.GroomedMesh

    file_source = Faker('file', extension='ply')
    pre_cropping_source = Faker('file', extension='txt', null_chance=50)
    pre_alignment_source = Faker('file', extension='txt', null_chance=50)

    mesh = SubFactory(MeshFactory)
    project = SubFactory(ProjectFactory)


class OptimizedParticlesFactory(Factory):
    class Meta:
        model = models.OptimizedParticles

    world_source = Faker('file', extension='txt')
    local_source = Faker('file', extension='txt')
    transform_source = Faker('file', extension='txt')
    project = SubFactory(ProjectFactory)
    subject = SubFactory(SubjectFactory)
    anatomy_type = Faker('word')
    groomed_segmentation = SubFactory(GroomedSegmentationFactory)
    groomed_mesh = SubFactory(GroomedMeshFactory)
