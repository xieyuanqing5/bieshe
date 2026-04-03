# app/views_ai.py

from flask import Blueprint, request, jsonify
from app.ai_match import ai_match_items

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/match", methods=["POST"])
def match_items():
    data = request.get_json()
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "설명 내용을 입력해주세요."}), 400

    results = ai_match_items(text)
    return jsonify(results)
