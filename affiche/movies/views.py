from flask import (
    Blueprint,
    render_template,
)

from affiche.movies import graber
from affiche.extensions import cache


movies_blueprint = Blueprint(
    'movies', __name__,
    template_folder='../templates/movies',
)


@movies_blueprint.route('/', methods=['GET'])
@cache.cached(timeout=60*60*24, key_prefix='list_top_rated')
def list_top_rated():
    top_movies = graber.fetch_top_movies_with_data()
    return render_template('movies.html', top_movies=top_movies)


@movies_blueprint.route('/api/info', methods=['GET'])
@cache.cached(timeout=60*60*24, key_prefix='rest_api_info')
def show_rest_api_info():
    return render_template('rest_api_info.html')
