# app/ai_match.py
import re
from difflib import SequenceMatcher
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.models import LostItem, FoundItem
from sentence_transformers import SentenceTransformer, util

ai_bp = Blueprint("ai", __name__)

model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

SYNONYM_MAP = {
    "咖啡店": "咖啡",
    "咖啡馆": "咖啡",
    "咖啡厅": "咖啡",
    "커피숍": "커피",
    "카페": "커피",
    "커피샵": "커피",
    "咖啡": "咖啡",
    "커피": "커피",

    "图书馆": "图书馆",
    "阅览室": "图书馆",
    "도서관": "도서관",
    "열람실": "도서관",

    "钱包": "钱包",
    "皮夹": "钱包",
    "지갑": "지갑",

    "手机": "手机",
    "电话": "手机",
    "휴대폰": "휴대폰",
    "핸드폰": "휴대폰",
    "폰": "휴대폰",

    "노트북": "노트북",
    "笔记本": "笔记本",
    "笔记本电脑": "笔记本",

    "책": "책",
    "书": "书",

    "红色": "红色",
    "红": "红色",
    "빨간색": "빨강",
    "빨강": "빨강",
    "빨간": "빨강",
    "레드": "빨강",

    "蓝色": "蓝色",
    "蓝": "蓝色",
    "파란색": "파랑",
    "파랑": "파랑",
    "파란": "파랑",
    "블루": "파랑",

    "黑色": "黑色",
    "黑": "黑色",
    "검은색": "검정",
    "검정색": "검정",
    "검정": "검정",
    "검은": "검정",
    "블랙": "검정",

    "白色": "白色",
    "白": "白色",
    "흰색": "하양",
    "하얀색": "하양",
    "하얀": "하양",
    "화이트": "하양",
    "하양": "하양",
}

KNOWN_PLACES = [
    "커피", "카페", "커피숍",
    "광운역", "서울역", "광운대",
    "도서관", "열람실",
    "한글관", "기숙사", "강의동", "운동장", "식당",
    "library", "cafe"
]

KNOWN_COLORS = [
    "빨강", "파랑", "검정", "하양",
    "红色", "蓝色", "黑色", "白色"
]

KNOWN_ITEM_WORDS = [
    "지갑",
    "휴대폰",
    "노트북",
    "책",
    "钱包",
    "手机",
    "笔记本",
    "书"
]

KOREAN_FILLER_PATTERNS = [
    r"에서", r"에", r"을", r"를", r"이", r"가", r"은", r"는",
    r"와", r"과", r"도", r"로", r"으로",
    r"잃어버렸어요", r"잃어버렸습니다", r"분실했어요", r"분실했습니다",
    r"떨어뜨렸어요", r"떨어뜨렸습니다",
    r"주웠어요", r"주웠습니다", r"발견했어요", r"발견했습니다",
    r"찾아요", r"찾았습니다",
    r"입니다", r"이에요", r"예요",
    r"제가", r"나는", r"저는", r"저"
]

def normalize_text(text):
    text = str(text or "").strip().lower()
    text = text.replace("，", " ").replace(",", " ")
    text = text.replace("。", " ").replace(".", " ")
    text = text.replace("！", " ").replace("!", " ")
    text = text.replace("？", " ").replace("?", " ")
    text = text.replace("/", " ").replace("-", " ")
    text = text.replace(":", " ").replace(";", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def replace_synonyms(text):
    text = normalize_text(text)
    for k, v in SYNONYM_MAP.items():
        text = text.replace(k.lower(), v.lower())
    text = re.sub(r"\s+", " ", text).strip()
    return text

def strip_korean_fillers(text):
    text = replace_synonyms(text)
    for pattern in KOREAN_FILLER_PATTERNS:
        text = re.sub(pattern, " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def preprocess_user_text(text):
    text = replace_synonyms(text)
    text = strip_korean_fillers(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def similarity(a, b):
    a = preprocess_user_text(a)
    b = preprocess_user_text(b)

    if not a or not b:
        return 0.0

    if a in b or b in a:
        return 1.0

    return round(SequenceMatcher(None, a, b).ratio(), 4)

def keyword_overlap_score(user_text, field_text):
    user_text = preprocess_user_text(user_text)
    field_text = preprocess_user_text(field_text)

    if not user_text or not field_text:
        return 0.0

    user_keywords = [w for w in re.split(r"[\s,，。.!！？;；:/\-]+", user_text) if w]
    if not user_keywords:
        return 0.0

    matched = sum(1 for word in user_keywords if word in field_text)
    return round(matched / len(user_keywords), 4)

def semantic_similarity(user_text, field_text):
    user_text = preprocess_user_text(user_text)
    field_text = preprocess_user_text(field_text)

    if not user_text or not field_text:
        return 0.0

    emb1 = model.encode(user_text, convert_to_tensor=True)
    emb2 = model.encode(field_text, convert_to_tensor=True)
    score = util.cos_sim(emb1, emb2).item()

    score = max(0.0, min(1.0, score))
    return round(score, 4)

def combined_text_score(user_text, field_text):
    overlap_score = keyword_overlap_score(user_text, field_text)
    lexical_score = similarity(user_text, field_text)
    semantic_score = semantic_similarity(user_text, field_text)

    total = (
        overlap_score * 0.3 +
        lexical_score * 0.2 +
        semantic_score * 0.5
    )

    if overlap_score >= 0.8:
        total += 0.1

    return round(min(total, 1.0), 4)

def extract_date_from_text(text):
    text = str(text or "")
    match = re.search(r"(\d{4})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})", text)
    if not match:
        return ""

    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

def extract_place_from_text(text):
    text = preprocess_user_text(text)
    for place in KNOWN_PLACES:
        normalized_place = preprocess_user_text(place)
        if normalized_place and normalized_place in text:
            return normalized_place
    return ""

def extract_color_from_text(text):
    text = preprocess_user_text(text)
    for color in KNOWN_COLORS:
        normalized_color = preprocess_user_text(color)
        if normalized_color and normalized_color in text:
            return normalized_color
    return ""

def extract_item_word_from_text(text):
    text = preprocess_user_text(text)
    sorted_words = sorted(KNOWN_ITEM_WORDS, key=lambda x: len(preprocess_user_text(x)), reverse=True)

    for item_word in sorted_words:
        normalized_item_word = preprocess_user_text(item_word)
        if normalized_item_word and normalized_item_word in text:
            return normalized_item_word

    return ""

def extract_item_word_from_item(item):
    item_name = getattr(item, "name", "") or ""
    item_category = getattr(item, "category", "") or ""
    item_description = getattr(item, "description", "") or ""
    item_text = f"{item_name} {item_category} {item_description}"
    return extract_item_word_from_text(item_text)

def remove_known_tokens(text, tokens):
    text = preprocess_user_text(text)
    for token in tokens:
        if token:
            normalized_token = preprocess_user_text(token)
            text = text.replace(normalized_token, " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def date_score(user_text, item_date):
    user_date = extract_date_from_text(user_text)
    item_date = str(item_date or "").strip()

    if not user_date or not item_date:
        return 0.0

    try:
        d1 = datetime.strptime(user_date, "%Y-%m-%d")
        d2 = datetime.strptime(item_date, "%Y-%m-%d")
        diff = abs((d1 - d2).days)

        if diff == 0:
            return 1.0
        elif diff == 1:
            return 0.7
        elif diff <= 3:
            return 0.4
        return 0.0
    except Exception:
        return 0.0

def color_score(user_text, item_name, item_description):
    user_color = extract_color_from_text(user_text)
    item_text = f"{item_name} {item_description}"
    item_color = extract_color_from_text(item_text)

    if not user_color:
        return 0.0
    if not item_color:
        return 0.0
    if user_color == item_color:
        return 1.0
    return -0.2

def item_word_penalty(user_text, item):
    user_item_word = extract_item_word_from_text(user_text)
    db_item_word = extract_item_word_from_item(item)

    if not user_item_word:
        return 0.0
    if not db_item_word:
        return 0.0
    if user_item_word == db_item_word:
        return 0.0

    return -0.15

def calculate_weighted_score(user_text, item):
    item_name = getattr(item, "name", "") or ""
    item_place = getattr(item, "place", "") or ""
    item_description = getattr(item, "description", "") or ""
    item_date = getattr(item, "date", "") or ""

    user_date = extract_date_from_text(user_text)
    user_place = extract_place_from_text(user_text)
    user_color = extract_color_from_text(user_text)
    user_item_word = extract_item_word_from_text(user_text)

    cleaned_text = remove_known_tokens(
        user_text,
        [user_date, user_place, user_color, user_item_word]
    )

    if not cleaned_text:
        cleaned_text = user_text

    if user_item_word or user_color:
        name_source = f"{user_item_word} {user_color}".strip()
        name_base_score = combined_text_score(name_source, item_name)
    else:
        name_base_score = combined_text_score(cleaned_text, item_name)

    if user_place:
        place_score_val = combined_text_score(user_place, item_place)
    else:
        place_score_val = combined_text_score(user_text, item_place)

    description_source = cleaned_text if cleaned_text else user_text
    description_score_val = combined_text_score(description_source, item_description)

    date_score_val = date_score(user_text, item_date)
    color_score_val = color_score(user_text, item_name, item_description)

    name_score = round(
        max(0.0, min(1.0, (name_base_score * 0.6) + (color_score_val * 0.4))),
        4
    )
    description_score = round(
        max(0.0, min(1.0, (description_score_val * 0.7) + (color_score_val * 0.3))),
        4
    )

    total_score = (
        name_score * 0.3 +
        place_score_val * 0.3 +
        description_score * 0.3 +
        date_score_val * 0.1
    )

    item_penalty_val = item_word_penalty(user_text, item)
    total_score += item_penalty_val
    total_score = max(0.0, min(1.0, total_score))

    return {
        "total_score": round(total_score, 4),
        "name_score": round(name_score, 4),
        "place_score": round(place_score_val, 4),
        "description_score": round(description_score, 4),
        "date_score": round(date_score_val, 4),
        "debug": {
            "user_date": user_date,
            "user_place": user_place,
            "user_color": user_color,
            "user_item_word": user_item_word,
            "cleaned_text": cleaned_text,
            "raw_name_base_score": round(name_base_score, 4),
            "raw_description_score": round(description_score_val, 4),
            "color_score": round(color_score_val, 4),
            "item_penalty": round(item_penalty_val, 4),
            "db_item_word": extract_item_word_from_item(item)
        }
    }

@ai_bp.route("/ai/match", methods=["POST"])
def ai_match():
    try:
        data = request.get_json(silent=True) or {}
        user_text = (data.get("text") or "").strip()

        if not user_text:
            return jsonify([])

        results = []

        lost_items = LostItem.query.all()
        found_items = FoundItem.query.all()

        print("==== FINAL MATCH DEBUG START ====")
        print("user_text:", user_text)
        print("preprocessed:", preprocess_user_text(user_text))
        print("lost_items count:", len(lost_items))
        print("found_items count:", len(found_items))

        for item in lost_items:
            score_detail = calculate_weighted_score(user_text, item)

            if score_detail["total_score"] >= 0.05:
                results.append({
                    "type": "lost",
                    "id": item.id,
                    "name": getattr(item, "name", "") or "이름 없음",
                    "category": getattr(item, "category", "") or "",
                    "place": getattr(item, "place", "") or "",
                    "date": str(getattr(item, "date", "") or ""),
                    "description": getattr(item, "description", "") or "",
                    "score": score_detail["total_score"],
                    "score_detail": {
                        "name": score_detail["name_score"],
                        "place": score_detail["place_score"],
                        "description": score_detail["description_score"],
                        "date": score_detail["date_score"]
                    },
                    "debug": score_detail["debug"]
                })

        for item in found_items:
            score_detail = calculate_weighted_score(user_text, item)

            if score_detail["total_score"] >= 0.05:
                results.append({
                    "type": "found",
                    "id": item.id,
                    "name": getattr(item, "name", "") or "이름 없음",
                    "category": getattr(item, "category", "") or "",
                    "place": getattr(item, "place", "") or "",
                    "date": str(getattr(item, "date", "") or ""),
                    "description": getattr(item, "description", "") or "",
                    "score": score_detail["total_score"],
                    "score_detail": {
                        "name": score_detail["name_score"],
                        "place": score_detail["place_score"],
                        "description": score_detail["description_score"],
                        "date": score_detail["date_score"]
                    },
                    "debug": score_detail["debug"]
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:5]

        print("match results:", results)
        print("==== FINAL MATCH DEBUG END ====")

        return jsonify(results)

    except Exception as e:
        print("AI MATCH ERROR:", str(e))
        return jsonify({"error": str(e)}), 500