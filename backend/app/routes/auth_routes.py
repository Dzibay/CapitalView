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
