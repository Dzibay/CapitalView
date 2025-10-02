from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.supabase_service import get_user_by_email, create_user
from app import bcrypt

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/check-token", methods=["GET"])
@jwt_required()
def check_token():
    # Получаем identity пользователя из токена
    user_email = get_jwt_identity()
    return jsonify({"msg": "Token is valid", "email": user_email}), 200

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if get_user_by_email(email):
        return jsonify({"msg": "User already exists"}), 400

    create_user(email, password)
    return jsonify({"msg": "User created successfully"}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = get_user_by_email(email)
    if not user or not bcrypt.check_password_hash(user["password_hash"], password):
        return jsonify({"msg": "Invalid email or password"}), 401

    access_token = create_access_token(identity=user["email"])
    return jsonify({"access_token": access_token})
