"""
Инициализация расширений Flask.
Все расширения создаются здесь и инициализируются в create_app.
"""
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from supabase import create_client, Client as SupabaseClient
from app.config import Config

# Инициализация расширений
bcrypt = Bcrypt()
jwt = JWTManager()
cors = CORS()

# Supabase клиент (инициализируется при создании приложения)
supabase: SupabaseClient = None


def init_extensions(app=None):
    """Инициализирует все расширения Flask."""
    if app:
        # Bcrypt для хеширования паролей
        bcrypt.init_app(app)
        
        # JWT для аутентификации
        jwt.init_app(app)
        
        # CORS для кросс-доменных запросов
        cors.init_app(
            app,
            origins=Config.CORS_ORIGINS,
            supports_credentials=Config.CORS_SUPPORTS_CREDENTIALS,
            resources={r"/*": {"origins": "*"}},
            methods=Config.CORS_METHODS,
        )
    
    # Supabase клиент
    global supabase
    if not supabase:
        Config.validate()
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    
    return app

