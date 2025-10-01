from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app, origins=["http://localhost:5173"])
    
    # импортируем и регистрируем роуты
    from .routes import portfolio_bp
    app.register_blueprint(portfolio_bp)

    return app
