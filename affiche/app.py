from flask import Flask, render_template


from affiche import commands
from affiche.extensions import cache, api
import affiche.settings as settings
from affiche.movies.views import movies_blueprint
from affiche.movies.rest.list import ListFilmsAPI


def create_app(config_object=settings):
    app = Flask(
        __name__.split('.')[0],
        static_url_path='/static',
        static_folder='static_files',
    )
    app.config.from_object(config_object)
    register_extensions(app)
    register_blueprints(app)
    register_api(app)
    register_commands(app)
    return app


def register_blueprints(app):
    app.register_blueprint(movies_blueprint)
    return None


def register_api(app):
    api.add_resource(ListFilmsAPI, '/api/movies')
    api.init_app(app)
    return None


def register_extensions(app):
    cache.init_app(app)
    return None


def register_commands(app):
    app.cli.add_command(commands.clean)
    app.cli.add_command(commands.key)
    app.cli.add_command(commands.load_page)
