import getpass
from pathlib import Path

from swcc.api import swcc_session
from swcc.models import Dataset, Project

username = input('Enter username: ')
password = getpass.getpass('Enter password: ')


with swcc_session(base_url='http://localhost:8000/api/v1') as session:
    token = session.login(username, password)
    print('Authenticated with running server.')

    print('Uploading left atrium dataset and project (4 meshes).')
    dataset_1 = Dataset(
        name='Left Atria',
        description='Left atria meshes of 4 subjects',
        license='No license',
        acknowledgement='No acknowledgement',
    ).force_create()

    project_file_1 = Path('left_atrium/left_atrium.swproj')
    project_1 = Project(
        file_source=project_file_1,
        description='First project for left atrium data',
        dataset=dataset_1,
        last_cached_analysis='analysis/left_atrium_analysis.json',
    ).create()
    print('Done.')

    print('Uploading ellipsoid dataset and project (3 segmentations).')
    dataset_2 = Dataset(
        name='Ellipsoids',
        description='3 ellipsoid segmentations',
        license='No license',
        acknowledgement='No acknowledgement',
    ).force_create()

    project_file_2 = Path('ellipsoid/ellipsoid.swproj')
    project_2 = Project(
        file_source=project_file_2,
        description='First project for ellipsoid data',
        dataset=dataset_2,
    ).create()
    print('Done.')

    print('Uploading deepsmm la dataset and project (with images).')
    dataset_3 = Dataset(
        name='DeepSSM la with Images',
        description='deepssm dataset with images',
        license='No license',
        acknowledgement='No acknowledgement',
    ).force_create()

    project_file_3 = Path('deepssm_la/deepssm_la.swproj')
    project_3 = Project(
        file=project_file_3,
        description='First project for deepssm la data',
        dataset=dataset_3,
    ).create()
    print('Done.')
