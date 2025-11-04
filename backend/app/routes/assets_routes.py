from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.supabase_service import *
from app.services.assets_service import delete_asset, create_asset, add_asset_price

assets_bp = Blueprint("assets", __name__)

@assets_bp.route('/add', methods=['POST'])
@jwt_required()
def create_asset_route():
    email = get_jwt_identity()
    data = request.get_json()
    print(data)
    res = create_asset(email, data)
    refresh_materialized_view('portfolio_daily_positions')
    return jsonify(res)
    
@assets_bp.route('/<int:asset_id>', methods=['DELETE'])
@jwt_required()
def delete_asset_route(asset_id):
    res = delete_asset(asset_id)
    refresh_materialized_view('portfolio_daily_positions')
    return jsonify(res)

@assets_bp.route('/add_price', methods=['POST'])
@jwt_required()
def add_asset_price_route():
    data = request.get_json()
    res = add_asset_price(data)
    refresh_materialized_view('asset_daily_prices')
    refresh_materialized_view('asset_lastest_prices_full')
    return jsonify(res)
