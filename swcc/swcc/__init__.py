from __future__ import annotations

from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
import logging
from pathlib import Path
import platform
import sys
import traceback

import click
from packaging.version import parse as parse_version
from pydantic import BaseModel
import requests
from requests.exceptions import RequestException
from requests_toolbelt.sessions import BaseUrlSession
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from swcc.utils import get_config_value, update_config_value

from .models import Dataset

SWCC_CONFIG_PATH = __name__
SWCC_CONFIG_FILE = 'config'
FORMAT = '%(message)s'
logging.basicConfig(format=FORMAT, datefmt='[%X]', handlers=[RichHandler()])
logger = logging.getLogger(__name__)

try:
    __version__ = version('swcc')
except PackageNotFoundError:
    # package is not installed
    pass


class SwccSession(BaseUrlSession):
    page_size = 50

    def __init__(self, base_url: str):
        base_url = f'{base_url.rstrip("/")}/'  # tolerate input with or without trailing slash
        super().__init__(base_url=base_url)
        self.headers.update(
            {
                'User-agent': f'swcc/{__version__}',
                'Accept': 'application/json',
            }
        )

        token = get_config_value(SWCC_CONFIG_FILE, 'token')
        if token:
            self.headers['Authorization'] = f'Token {token}'

    def request(self, *args, **kwargs):
        response = super().request(*args, **kwargs)

        if response.status_code in [401, 403]:
            click.echo(
                click.style(
                    "You are attempting to perform an authorized operation but you aren't logged in.\n"  # noqa
                    "Run 'swcc login' to continue.",
                    fg='yellow',
                ),
                err=True,
            )
            sys.exit(1)

        return response


class CliContext(BaseModel):
    session: SwccSession
    url: str
    json_output: bool

    class Config:
        arbitrary_types_allowed = True


def newer_version_available():
    if __version__ is None:
        return False

    this_version = parse_version(__version__)
    if this_version.is_devrelease:
        return False

    r = requests.get('https://pypi.org/pypi/swcc/json', timeout=(5, 5))
    r.raise_for_status()
    releases = [parse_version(v) for v in r.json()['releases'].keys()]
    for release in releases:
        if not (release.is_prerelease or release.is_devrelease) and release > this_version:
            return True
    return False


@click.group()
@click.option('--url', default='https://app.shapeworks-cloud.org/api/v1', envvar='SWCC_URL')
@click.option('--json', 'json_output', is_flag=True)
@click.option('-v', '--verbose', count=True)
@click.version_option()
@click.pass_context
def cli(ctx, url, json_output: bool, verbose: int):
    if verbose >= 2:
        logger.setLevel(logging.DEBUG)
    elif verbose >= 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARN)

    try:
        if newer_version_available():
            click.echo(
                click.style(
                    """There is a newer version of swcc available.
You must upgrade to the latest version before continuing.
""",
                    fg='yellow',
                ),
                err=True,
            )
            click.echo(click.style('pip install --upgrade swcc', fg='green'), err=True)
            sys.exit(1)
    except RequestException:
        click.echo(click.style('Failed to check for newer version of swcc:', fg='red'), err=True)
        raise

    session = SwccSession(url)
    ctx.obj = CliContext(session=session, url=url.rstrip('/'), json_output=json_output)


@cli.group(name='dataset', short_help='get information about datasets')
@click.pass_obj
def dataset(ctx):
    pass


@dataset.command(name='create', help='create a dataset')
@click.argument('name', type=str)
@click.argument('groomed-pattern', type=str)
@click.argument('segmentation-pattern', type=str)
@click.argument('particles-pattern', type=str)
@click.pass_obj
def create(ctx, name, groomed_pattern, segmentation_pattern, particles_pattern):
    dataset = Dataset.create(
        ctx,
        name=name,
        groomed_pattern=groomed_pattern,
        segmentation_pattern=segmentation_pattern,
        particles_pattern=particles_pattern,
    )
    click.echo(dataset)


@dataset.command(name='list', help='list datasets')
@click.pass_obj
def list_(ctx):
    datasets = Dataset.list(ctx)

    if ctx.json_output:
        for dataset in datasets:
            click.echo(dataset.json())
    else:
        console = Console()

        table = Table(show_header=True, header_style='bold green')
        table.add_column('ID')
        table.add_column('Created')
        table.add_column('Name', width=50)

        for dataset in datasets:
            table.add_row(f'{dataset.id}', dataset.created.strftime('%c'), dataset.name)

        console.print(table)


@dataset.command(name='download', help='download a dataset')
@click.argument('id_', type=int, metavar='ID')
@click.argument('dest', type=click.Path(exists=False, file_okay=False, dir_okay=True))
@click.option('-s', '--subject-id', type=int, multiple=True)
@click.pass_obj
def download(ctx, id_: int, dest, subject_id):
    dest = Path(dest)
    dest.mkdir(exist_ok=True)
    dataset = Dataset.from_id(ctx, id_)

    segmentations = Path(dest / 'segmentations')
    segmentations.mkdir(exist_ok=True, parents=True)
    for x in dataset.segmentations(ctx):
        if (not subject_id) or (x.subject in subject_id):
            x.download(ctx, segmentations)

    groomed = Path(dest / 'groomed')
    groomed.mkdir(exist_ok=True, parents=True)
    for x in dataset.groomed(ctx):
        if (not subject_id) or (x.subject in subject_id):
            x.download(ctx, groomed)

    shape_models = Path(dest / 'shape_models')
    shape_models.mkdir(exist_ok=True, parents=True)
    for x in dataset.shape_models(ctx):
        x.download(ctx, shape_models)

        particles = Path(shape_models / x.name / 'particles')
        particles.mkdir(exist_ok=True, parents=True)
        for particle in dataset.particles(ctx, x.id):
            if (not subject_id) or (particle.subject in subject_id):
                particle.download(ctx, particles)


@cli.command(name='login', help='authenticate with shapeworks cloud')
@click.pass_obj
def login(ctx):
    while True:
        username = click.prompt('username', err=True)
        password = click.prompt('password', hide_input=True, err=True)

        # explicitly sidestep the session, since it checks for auth-related errors
        # to tell the user to login.
        r = requests.post(
            f'{ctx.url.rstrip("/").replace("/api/v1", "")}/api-token-auth/',
            data={'username': username, 'password': password},
        )

        if r.ok:
            update_config_value(SWCC_CONFIG_FILE, 'token', r.json()['token'])
            return click.echo(click.style('logged in successfully.', fg='green'), err=True)
        elif r.status_code == 400:
            continue
        else:
            # an error other than 'bad credentials'
            r.raise_for_status()


def main():
    try:
        cli()
    except Exception:
        click.echo(
            click.style(
                'The following unexpected error occurred while attempting your operation:\n',
                fg='red',
            ),
            err=True,
        )

        click.echo(traceback.format_exc(), err=True)

        click.echo(f'swcc:    v{__version__}', err=True)
        click.echo(f'python:  v{platform.python_version()}', err=True)
        click.echo(f'time:    {datetime.utcnow().isoformat()}', err=True)
        click.echo(f'os:      {platform.platform()}', err=True)
        click.echo(f'command: swcc {" ".join(sys.argv[1:])}\n', err=True)

        click.echo(
            click.style(
                'This is a bug in swcc and should be reported. You can open an issue below: ',
                fg='yellow',
            ),
            err=True,
        )
        click.echo(
            'https://github.com/girder/shapeworks-cloud/issues/new',
            err=True,
        )


if __name__ == '__main__':
    main()
