from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.supabase_service import *
from app.services.portfolio_service_async import (
    get_user_portfolios,
    get_portfolio_assets,
    get_portfolio_transactions,
    get_portfolio_value_history
)
import asyncio

portfolio_bp = Blueprint("portfolio", __name__)

@portfolio_bp.route("/list", methods=["GET"])
@jwt_required()
def list_portfolios_route():
    user_email = get_jwt_identity()
    data = asyncio.run(get_user_portfolios(user_email))
    return jsonify(data)

@portfolio_bp.route("/<int:portfolio_id>/assets", methods=["GET"])
@jwt_required()
def portfolio_assets_route(portfolio_id):
    data = asyncio.run(get_portfolio_assets(portfolio_id))
    return jsonify(data)

@portfolio_bp.route("/transactions/<int:portfolio_id>", methods=["GET"])
@jwt_required()
def portfolio_transactions_route(portfolio_id):
    data = asyncio.run(get_portfolio_transactions(portfolio_id))
    return jsonify(data)

@portfolio_bp.route("/transaction/add", methods=["POST"])
@jwt_required()
def add_transaction_route():
    payload = request.get_json()
    # предполагаем, что payload уже содержит portfolio_id, asset_id или ticker...
    res = table_insert("transactions", payload)
    return jsonify(res), 201

@portfolio_bp.route("/history/<int:portfolio_id>", methods=["GET"])
@jwt_required()
def portfolio_history(portfolio_id):
    data = asyncio.run(get_portfolio_value_history(portfolio_id))
    return jsonify(data)
