"""
Конфигурация Swagger/OpenAPI документации.
"""
SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs",
    "title": "CapitalView API Documentation",
    "version": "1.0.0",
    "description": """
    API документация для CapitalView - системы управления портфелями и активами.
    
    ## Аутентификация
    
    Большинство endpoints требуют JWT токен. Получите токен через `/api/auth/login` 
    и используйте его в заголовке `Authorization: Bearer <token>`.
    
    ## Основные разделы API
    
    - **Auth** - Аутентификация и регистрация пользователей
    - **Portfolio** - Управление портфелями
    - **Assets** - Управление активами
    - **Transactions** - Управление транзакциями
    - **Dashboard** - Данные дашборда
    - **Analytics** - Аналитика по портфелям
    """,
    "termsOfService": "",
    "contact": {
        "name": "API Support",
        "email": "support@capitalview.com"
    },
    "license": {
        "name": "MIT",
    },
    "schemes": ["http", "https"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT токен. Формат: Bearer {token}"
        }
    },
    "security": [
        {
            "Bearer": []
        }
    ],
}

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "CapitalView API",
        "description": "API для управления портфелями и активами",
        "version": "1.0.0",
    },
    "basePath": "/api",
    "schemes": ["http", "https"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT токен. Формат: Bearer {token}"
        }
    },
}

