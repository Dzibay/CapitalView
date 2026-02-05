from flask import Blueprint, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.services.user_service import create_user, get_user_by_email
from app.extensions import bcrypt
from app.models.auth_models import RegisterRequest, LoginRequest
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from app.decorators import handle_errors, validate_json_body
from app.utils.response_helpers import success_response, error_response, not_found_response
from pydantic import ValidationError

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
@validate_json_body
@handle_errors
def register():
    """Регистрация нового пользователя."""
    # Валидация входных данных
    data = RegisterRequest(**request.get_json())
    
    # Проверка существования пользователя
    if get_user_by_email(data.email):
        return error_response(
            ErrorMessages.USER_ALREADY_EXISTS,
            status_code=HTTPStatus.BAD_REQUEST
        )
    
    # Создание пользователя
    create_user(data.email, data.password)
    
    return success_response(
        message=SuccessMessages.USER_CREATED,
        status_code=HTTPStatus.CREATED
    )


@auth_bp.route("/login", methods=["POST"])
@validate_json_body
@handle_errors
def login():
    """Вход пользователя в систему."""
    # Валидация входных данных
    data = LoginRequest(**request.get_json())
    
    # Проверка пользователя
    user = get_user_by_email(data.email)
    if not user or not bcrypt.check_password_hash(user["password_hash"], data.password):
        return error_response(
            ErrorMessages.INVALID_CREDENTIALS,
            status_code=HTTPStatus.UNAUTHORIZED
        )
    
    # Создание токена
    access_token = create_access_token(identity=data.email)
    
    return success_response(
        data={
            "access_token": access_token,
            "user": {
                "id": user["id"],
                "email": user["email"]
            }
        },
        message=SuccessMessages.LOGIN_SUCCESS
    )


@auth_bp.route("/check-token", methods=["GET"])
@jwt_required()
@handle_errors
def check_token():
    """Проверка валидности JWT токена."""
    email = get_jwt_identity()
    user = get_user_by_email(email)
    
    if not user:
        return not_found_response("Пользователь")
    
    return success_response(
        data={
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"]
            }
        },
        message="Token valid"
    )
