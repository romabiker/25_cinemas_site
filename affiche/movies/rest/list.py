from flask_restful import Resource


from affiche.extensions import cache
from affiche.movies import graber


class ListFilmsAPI(Resource):
    @cache.cached(timeout=60*60*24, key_prefix='api_list')
    def get(self):
        return list(graber.fetch_top_movies_with_data())
