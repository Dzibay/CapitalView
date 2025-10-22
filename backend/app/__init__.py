from flask import Flask
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from supabase import create_client, Client as SupabaseClient
import os
from datetime import timedelta

# Получаем ключ Supabase из переменных окружения
SUPABASE_URL = "https://wnoulslvcvyhnwvjiixw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBh" \
"YmFzZSIsInJlZiI6Indub3Vsc2x2Y3Z5aG53dmppaXh3Iiwicm9sZSI6InNlcnZpY2Vf" \
"cm9sZSIsImlhdCI6MTc1OTM1Njg3NywiZXhwIjoyMDc0OTMyODc3fQ.bHnjP5uD5wLIk" \
"iRaaX60MdaCdEW5EK82ayWxYqxf0CY"

supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)
bcrypt = Bcrypt()

    
def create_app():
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "supersecret")
    CORS(app, origins=["http://localhost:5173"], supports_credentials=True, resources={r"/*": {"origins": "*"}}, methods=["GET", "POST", "DELETE", "OPTIONS", "PUT"])
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)
    jwt = JWTManager(app)
    bcrypt.init_app(app)

    from app.routes.auth_routes import auth_bp
    from app.routes.portfolio_routes import portfolio_bp
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.assets_routes import assets_bp
    from app.routes.transaction_routes import transactions_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(portfolio_bp, url_prefix="/api/portfolio")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(assets_bp, url_prefix="/api/assets")
    app.register_blueprint(transactions_bp, url_prefix="/api/transactions")

    return app
