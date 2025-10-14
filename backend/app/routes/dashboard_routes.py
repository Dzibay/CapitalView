from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.dashboard_service import get_dashboard_data
import asyncio

dashboard_bp = Blueprint("dashboard", __name__)

# Если запускаешь через async-capable сервер (Hypercorn), можно сделать async def:
@dashboard_bp.route("/", methods=["GET"])
@jwt_required()
async def dashboard():
    email = get_jwt_identity()
    data = await get_dashboard_data(email)
    return jsonify(data)
