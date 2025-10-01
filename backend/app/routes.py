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
