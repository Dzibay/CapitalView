from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.services.user_service import create_user, get_user_by_email
from app import bcrypt

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    email, password = data.get("email"), data.get("password")
    if get_user_by_email(email):
        return jsonify({"msg": "User already exists"}), 400
    create_user(email, password)
    return jsonify({"msg": "User created successfully"}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email, password = data.get("email"), data.get("password")
    user = get_user_by_email(email)
    if not user or not bcrypt.check_password_hash(user["password_hash"], password):
        return jsonify({"msg": "Invalid credentials"}), 401
    access_token = create_access_token(identity=email)
    return jsonify({"access_token": access_token})

@auth_bp.route("/check-token", methods=["GET"])
@jwt_required()
def check_token():
    email = get_jwt_identity()
    user = get_user_by_email(email)
    return jsonify({"msg": "Token valid", "user": user})
