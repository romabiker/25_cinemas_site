from flask_debugtoolbar import DebugToolbarExtension
from flask_caching import Cache
from flask_restful import Api




debug_toolbar = DebugToolbarExtension()
cache = Cache()
api = Api()
