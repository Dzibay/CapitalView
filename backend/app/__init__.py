from flask import Flask

def create_app():
    app = Flask(__name__)

    # импортируем и регистрируем роуты
    from .routes import portfolio_bp
    app.register_blueprint(portfolio_bp)

    return app
