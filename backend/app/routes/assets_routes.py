from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.supabase_service import *
from app.services.assets_service import delete_asset, create_asset

assets_bp = Blueprint("assets", __name__)

@assets_bp.route('/add', methods=['POST'])
@jwt_required()
def create_asset_route():
    email = get_jwt_identity()
    data = request.get_json()
    res = create_asset(email, data)
    return jsonify(res)
    

@assets_bp.route('/<int:asset_id>', methods=['DELETE'])
@jwt_required()
def delete_asset_route(asset_id):
    res = delete_asset(asset_id)
    return jsonify(res)
