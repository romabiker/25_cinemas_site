import os


DEBUG = True
SECRET_KEY = os.environ.get('AFFICHE_SECRET', 'secret-key')
APP_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
JSON_AS_ASCII = False
CACHE_TYPE = 'simple'
