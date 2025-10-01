from flask import Blueprint, request, jsonify
from .tinkoff_service import get_portfolio_assets

portfolio_bp = Blueprint('portfolio', __name__)

@portfolio_bp.route("/portfolio", methods=["POST"])
def portfolio():
    # data = request.json
    # token = data.get("token")
    token = "t.Wwc9-ETWh-SiWqphi_F3TQ-U7TZNsuhUryWHiDWu1vqvq19ypX7I9il3E9PlfZgKyt4gPiHrXD4RjyNiVUHzzA"

    if not token:
        return jsonify({"error": "Требуется токен"}), 400

    try:
        assets = get_portfolio_assets(token)
        return jsonify(assets)
    except Exception as e:
        return jsonify({"error": str(e)}), 500



from .models import User, db
from . import bcrypt
from flask_jwt_extended import create_access_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    tinkoff_token = data.get("tinkoff_token")

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Пользователь с таким email уже существует"}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(id=email, email=email, tinkoff_token=tinkoff_token)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Пользователь успешно зарегистрирован"}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error": "Неверный email или пароль"}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify({"access_token": access_token})
