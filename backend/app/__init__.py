from flask import Flask
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from supabase import create_client, Client as SupabaseClient
import os
from datetime import timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем ключ Supabase из переменных окружения
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

# Создаем клиент Supabase
supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)

bcrypt = Bcrypt()

    
def create_app():
    app = Flask(__name__)
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        raise ValueError("JWT_SECRET_KEY must be set in environment variables")
    app.config["JWT_SECRET_KEY"] = jwt_secret
    CORS(app, origins=["http://localhost:5173"], supports_credentials=True, resources={r"/*": {"origins": "*"}}, methods=["GET", "POST", "DELETE", "OPTIONS", "PUT"])
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)
    jwt = JWTManager(app)
    bcrypt.init_app(app)

    from app.routes.auth_routes import auth_bp
    from app.routes.portfolio_routes import portfolio_bp
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.assets_routes import assets_bp
    from app.routes.transaction_routes import transactions_bp
    from app.routes.analitics_routes import analytics_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(portfolio_bp, url_prefix="/api/portfolio")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(assets_bp, url_prefix="/api/assets")
    app.register_blueprint(transactions_bp, url_prefix="/api/transactions")
    app.register_blueprint(analytics_bp, url_prefix='/api/analitics')

    return app
