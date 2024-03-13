# This test requires that https://www.shapeworks-cloud.org/#/ is running
# This will fetch all datasets populated on the public server and attempt to
# upload them all to the local server
import filecmp
import os
import random
from tempfile import TemporaryDirectory

from swcc import models
from swcc.api import swcc_session

SAMPLE_SIZE = 3


def project_as_dict_repr(project):
    project_repr = dict(project)
    project_repr['dataset'] = dict(project_repr['dataset'])

    # remove keys that are expected to differ between servers
    del project_repr['id']
    if 'file' in project_repr:
        del project_repr['file']
    if 'file_source' in project_repr:
        del project_repr['file_source']
    del project_repr['creator']
    del project_repr['dataset']['id']
    del project_repr['dataset']['creator']
    del project_repr['last_cached_analysis']
    del project_repr['last_cached_deep_ssm']
    del project_repr['landmarks_info']
    return project_repr


class DirCmp(filecmp.dircmp):
    def phase3(self):
        fcomp = filecmp.cmpfiles(self.left, self.right, self.common_files, shallow=False)
        self.same_files, self.diff_files, self.funny_files = fcomp


def is_same(dir1, dir2):
    compared = DirCmp(dir1, dir2)
    different = (
        compared.left_only or compared.right_only or compared.diff_files or compared.funny_files
    )
    if different:
        return False
    for subdir in compared.common_dirs:
        if not is_same(os.path.join(dir1, subdir), os.path.join(dir2, subdir)):
            return False
    return True


def public_server_download(download_dir):
    with swcc_session() as public_server_session:
        public_server_session.login('testuser@noemail.nil', 'cicdtest')
        all_datasets = list(models.Dataset.list())
        tiny_tests = [d for d in all_datasets if 'tiny_test' in d.name]
        dataset_subset = (
            random.sample(tiny_tests, SAMPLE_SIZE) if len(tiny_tests) >= SAMPLE_SIZE else tiny_tests
        )
        project_subset = [next(d.projects, None) for d in dataset_subset]
        for project in project_subset:
            if project is not None:
                project.download(download_dir)
        return project_subset


def test_download_upload_cycle(session):
    with TemporaryDirectory() as temp_dir:
        # Download from public server
        download_dir = f'{temp_dir}/download'
        os.mkdir(download_dir)
        all_projects = public_server_download(download_dir)

        new_projects = []
        # Upload to local server
        for project in all_projects:
            d = models.Dataset(
                name=project.dataset.name,
                description=project.dataset.description,
                license=project.dataset.license,
                acknowledgement=project.dataset.acknowledgement,
                keywords=project.dataset.keywords,
                contributors=project.dataset.contributors,
                publications=project.dataset.publications,
                private=project.dataset.private,
            ).force_create()
            new_projects.append(
                models.Project(
                    dataset=d,
                    name=project.name,
                    file_source=project.file.path,
                    private=project.private,
                    readonly=project.readonly,
                    description=project.description,
                    keywords=project.keywords,
                ).create()
            )

        # Redownload from local server
        redownload_dir = f'{temp_dir}/redownload'
        os.mkdir(redownload_dir)
        for project in new_projects:
            project.download(redownload_dir)

        # Test for file structure congruence
        assert is_same(download_dir, redownload_dir)

    for local_project, remote_project in zip(models.Project.list(), all_projects):
        local_repr = project_as_dict_repr(local_project)
        remote_repr = project_as_dict_repr(remote_project)
        assert local_repr == remote_repr
    assert len(list(models.Project.list())) == len(all_projects)
