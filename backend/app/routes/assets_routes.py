from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.supabase_service import *
from app.services.user_service import get_user_by_email
from app.services.assets_service import delete_asset, create_asset, add_asset_price

assets_bp = Blueprint("assets", __name__)

@assets_bp.route('/add', methods=['POST'])
@jwt_required()
def create_asset_route():
    email = get_jwt_identity()
    data = request.get_json()
    res = create_asset(email, data)

    user_id = get_user_by_email(email)
    rpc('refresh_daily_data_for_user', {'p_user_id': user_id})
    return jsonify(res)
    
@assets_bp.route('/<int:asset_id>', methods=['DELETE'])
@jwt_required()
def delete_asset_route(asset_id):
    email = get_jwt_identity()
    res = delete_asset(asset_id)

    user_id = get_user_by_email(email)
    rpc('refresh_daily_data_for_user', {'p_user_id': user_id})
    return jsonify(res)

@assets_bp.route('/add_price', methods=['POST'])
@jwt_required()
def add_asset_price_route():
    email = get_jwt_identity()
    data = request.get_json()
    res = add_asset_price(data)

    user_id = get_user_by_email(email)
    rpc('refresh_daily_data_for_user', {'p_user_id': user_id})
    return jsonify(res)
