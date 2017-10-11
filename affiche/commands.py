import os


import click
import requests


from affiche.utils import get_secret_key


HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.join(HERE, os.pardir)


@click.command()
def clean():
    for dirpath, dirnames, filenames in os.walk('.'):
        for filename in filenames:
            if filename.endswith('.pyc') or filename.endswith('.pyo'):
                full_pathname = os.path.join(dirpath, filename)
                click.echo('Removing {}'.format(full_pathname))
                os.remove(full_pathname)


@click.command()
def key():
    click.echo('New generated key:{}'.format(get_secret_key()))


@click.command()
@click.option('-u', '--url', help='url to load')
def load_page(url, path='test.html'):
    response = requests.get(url=url)
    response.raise_for_status()
    with open(path, 'w') as file_handler:
        file_handler.write(response.text)
    click.echo('{url} saved to {path}'.format(url=url, path=path))
