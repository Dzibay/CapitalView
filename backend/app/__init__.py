from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS


db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:SuFBz6vBq68z67rg@db.wnoulslvcvyhnwvjiixw.supabase.co:5432/postgres'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'secret'

    CORS(app, origins=["http://localhost:5173"])

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    from .routes import auth_bp
    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()

    return app
