"""Application factory and configuration."""

from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

from app.models import db
from app.api.routes import main_bp


def create_app(config_name='development'):
    """Application factory function"""
    load_dotenv()

    from config import config
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    CORS(app)
    db.init_app(app)

    app.register_blueprint(main_bp)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with app.app_context():
        db.create_all()

    return app
