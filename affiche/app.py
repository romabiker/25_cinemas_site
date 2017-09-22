from flask import Flask, render_template


from affiche import commands
from affiche.extensions import debug_toolbar, cache, api
from affiche.settings import ProdConfig
from affiche.movies.views import movies_blueprint
from affiche.movies.rest.list import ListFilmsAPI


def create_app(config_object=ProdConfig):
    app = Flask(
        __name__.split('.')[0],
        static_url_path='/static',
        static_folder='static_files',
    )
    app.config.from_object(config_object)
    register_extensions(app)
    register_blueprints(app)
    register_api(app)
    register_errorhandlers(app)
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
    debug_toolbar.init_app(app)
    cache.init_app(app)
    return None


def register_errorhandlers(app):
    def render_error(error):
        error_code = getattr(error, 'code', 500)
        return render_template('{0}.html'.format(error_code)), error_code
    for errcode in [404, 500]:
        app.errorhandler(errcode)(render_error)
    return None


def register_commands(app):
    app.cli.add_command(commands.clean)
    app.cli.add_command(commands.key)
