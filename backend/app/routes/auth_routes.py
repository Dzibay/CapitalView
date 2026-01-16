from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.services.user_service import create_user, get_user_by_email
from app.extensions import bcrypt
from app.models.auth_models import RegisterRequest, LoginRequest
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from pydantic import ValidationError

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Регистрация нового пользователя.
    ---
    tags:
      - Auth
    summary: Регистрация нового пользователя
    description: Создает нового пользователя в системе
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        description: Данные для регистрации
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              format: email
              example: user@example.com
              description: Email пользователя
            password:
              type: string
              minLength: 6
              example: password123
              description: Пароль (минимум 6 символов)
    responses:
      201:
        description: Пользователь успешно создан
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Пользователь успешно создан
      400:
        description: Ошибка валидации или пользователь уже существует
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
            details:
              type: array
      500:
        description: Внутренняя ошибка сервера
    """
    try:
        # Валидация входных данных
        data = RegisterRequest(**request.get_json())
        
        # Проверка существования пользователя
        if get_user_by_email(data.email):
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_ALREADY_EXISTS
            }), HTTPStatus.BAD_REQUEST
        
        # Создание пользователя
        create_user(data.email, data.password)
        
        return jsonify({
            "success": True,
            "message": SuccessMessages.USER_CREATED
        }), HTTPStatus.CREATED
        
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": ErrorMessages.VALIDATION_ERROR,
            "details": e.errors()
        }), HTTPStatus.BAD_REQUEST
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Вход пользователя в систему.
    ---
    tags:
      - Auth
    summary: Вход в систему
    description: Аутентификация пользователя и получение JWT токена
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        description: Учетные данные пользователя
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              format: email
              example: user@example.com
            password:
              type: string
              example: password123
    responses:
      200:
        description: Успешный вход
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Успешный вход в систему
            access_token:
              type: string
              example: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
            user:
              type: object
              properties:
                id:
                  type: string
                email:
                  type: string
      401:
        description: Неверные учетные данные
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
              example: Неверные учетные данные
      400:
        description: Ошибка валидации
      500:
        description: Внутренняя ошибка сервера
    """
    try:
        # Валидация входных данных
        data = LoginRequest(**request.get_json())
        
        # Проверка пользователя
        user = get_user_by_email(data.email)
        if not user or not bcrypt.check_password_hash(user["password_hash"], data.password):
            return jsonify({
                "success": False,
                "error": ErrorMessages.INVALID_CREDENTIALS
            }), HTTPStatus.UNAUTHORIZED
        
        # Создание токена
        access_token = create_access_token(identity=data.email)
        
        return jsonify({
            "success": True,
            "message": SuccessMessages.LOGIN_SUCCESS,
            "access_token": access_token,
            "user": {
                "id": user["id"],
                "email": user["email"]
            }
        }), HTTPStatus.OK
        
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": ErrorMessages.VALIDATION_ERROR,
            "details": e.errors()
        }), HTTPStatus.BAD_REQUEST
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@auth_bp.route("/check-token", methods=["GET"])
@jwt_required()
def check_token():
    """
    Проверка валидности токена.
    ---
    tags:
      - Auth
    summary: Проверка токена
    description: Проверяет валидность JWT токена и возвращает данные пользователя
    security:
      - Bearer: []
    produces:
      - application/json
    responses:
      200:
        description: Токен валиден
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Token valid
            user:
              type: object
              properties:
                id:
                  type: string
                email:
                  type: string
      401:
        description: Токен недействителен или отсутствует
      404:
        description: Пользователь не найден
    """
    email = get_jwt_identity()
    user = get_user_by_email(email)
    
    if not user:
        return jsonify({
            "success": False,
            "error": ErrorMessages.USER_NOT_FOUND
        }), HTTPStatus.NOT_FOUND
    
    return jsonify({
        "success": True,
        "message": "Token valid",
        "user": {
            "id": user["id"],
            "email": user["email"]
        }
    }), HTTPStatus.OK
