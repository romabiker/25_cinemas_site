from flask.helpers import get_debug_flag


from affiche.app import create_app
from affiche.settings import DevConfig, ProdConfig


CONFIG = DevConfig if get_debug_flag() else ProdConfig

app = create_app(CONFIG)
