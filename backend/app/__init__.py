"""
Главный модуль приложения Flask.
Инициализирует приложение и регистрирует все компоненты.
"""
from flask import Flask
from flasgger import Swagger
from app.config import config
from app.extensions import init_extensions
from app.middleware.error_handler import register_error_handlers
from app.middleware.logging_config import setup_logging
from app.swagger_config import SWAGGER_CONFIG, SWAGGER_TEMPLATE


def create_app(config_name="default"):
    """
    Фабрика приложения Flask.
    
    Args:
        config_name: Имя конфигурации ('development', 'production', 'default')
    
    Returns:
        Flask приложение
    """
    app = Flask(__name__)
    
    # Загрузка конфигурации
    app.config.from_object(config.get(config_name, config["default"]))
    
    # Инициализация расширений
    init_extensions(app)
    
    # Настройка логирования
    setup_logging(app)
    
    # Регистрация обработчиков ошибок
    register_error_handlers(app)
    
    # Инициализация Swagger документации
    swagger = Swagger(app, config=SWAGGER_CONFIG, template=SWAGGER_TEMPLATE)
    
    # Регистрация blueprints (маршрутов)
    register_blueprints(app)
    
    return app


def register_blueprints(app):
    """Регистрирует все blueprints приложения."""
    from app.routes.auth_routes import auth_bp
    from app.routes.portfolio_routes import portfolio_bp
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.assets_routes import assets_bp
    from app.routes.transaction_routes import transactions_bp
    from app.routes.operations_routes import operations_bp
    from app.routes.analitics_routes import analytics_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(portfolio_bp, url_prefix="/api/portfolio")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(assets_bp, url_prefix="/api/assets")
    app.register_blueprint(transactions_bp, url_prefix="/api/transactions")
    app.register_blueprint(operations_bp, url_prefix="/api/operations")
    app.register_blueprint(analytics_bp, url_prefix="/api/analitics")
