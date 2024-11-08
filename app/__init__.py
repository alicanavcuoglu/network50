# app/__init__.py
from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from .config import Config

# Initialize extensions
db = SQLAlchemy()
socketio = SocketIO()
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")
    mail.init_app(app)

    with app.app_context():
        # Register blueprints
        from app.errors import bp as errors_bp
        app.register_blueprint(errors_bp)
        
        from app.routes import auth, main

        app.register_blueprint(auth)
        app.register_blueprint(main)

        # Initialize Socket.IO events
        from app.events import init_socketio

        init_socketio(socketio)

    return app
