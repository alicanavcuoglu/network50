# app/routes/__init__.py
from flask import Blueprint

# Create blueprints
auth = Blueprint('auth', __name__)
main = Blueprint('main', __name__)

# Export blueprints
__all__ = ['auth', 'main']

# Import routes AFTER blueprint creation
from . import auth_routes
from . import main_routes