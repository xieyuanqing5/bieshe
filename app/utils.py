from collections import Counter

from app.models import LostItem, FoundItem

# =========================
# 分类列表
# 注册页面、搜索页面下拉框使用
# =========================
CATEGORIES = [
    "지갑",
    "열쇠",
    "가방",
    "휴대폰",
    "전자기기",
    "책",
    "학생증",
    "의류",
    "기타",
]

# =========================
# 地点列表
# 注册页面、搜索页面下拉框使用
# =========================
LOCATIONS = [
    "도서관",
    "강의실",
    "기숙사",
    "학생회관",
    "식당",
    "카페",
    "운동장",
    "정문",
    "후문",
    "버스정류장",
    "주차장",
    "기타",
]


def normalize_text(value):
    """
    基础文本清洗
    """
    return (value or "").strip()


def normalize_category(category, item_name=""):
    """
    分类归一化：
    把用户输入的细碎分类或物品名，统一映射到更标准的类别
    """
    category = normalize_text(category).lower()
    item_name = normalize_text(item_name).lower()

    combined = f"{category} {item_name}".strip()

    # 지갑
    if any(keyword in combined for keyword in [
        "지갑", "wallet", "검정색 지갑", "검은 지갑", "카드지갑", "반지갑", "장지갑"
    ]):
        return "지갑"

    # 열쇠
    if any(keyword in combined for keyword in [
        "열쇠", "키", "key", "자동차키", "집열쇠", "사물함키"
    ]):
        return "열쇠"

    # 가방
    if any(keyword in combined for keyword in [
        "가방", "백팩", "배낭", "크로스백", "숄더백", "파우치", "bag"
    ]):
        return "가방"

    # 휴대폰
    if any(keyword in combined for keyword in [
        "휴대폰", "핸드폰", "폰", "스마트폰", "휴대 전화", "iphone", "galaxy"
    ]):
        return "휴대폰"

    # 전자기기
    if any(keyword in combined for keyword in [
        "노트북", "이어폰", "에어팟", "충전기", "마우스", "태블릿",
        "전자기기", "usb", "케이블", "아이패드", "헤드셋", "전자 제품"
    ]):
        return "전자기기"

    # 책
    if any(keyword in combined for keyword in [
        "책", "교재", "노트", "공책", "book", "전공책"
    ]):
        return "책"

    # 학생증
    if any(keyword in combined for keyword in [
        "학생증", "학생 카드", "학생카드", "id카드", "신분증", "증명서", "카드"
    ]):
        return "학생증"

    # 의류
    if any(keyword in combined for keyword in [
        "옷", "의류", "점퍼", "외투", "자켓", "코트", "모자", "장갑", "신발", "후드"
    ]):
        return "의류"

    return "기타"


def normalize_place(place):
    """
    地点归一化：
    把相近地点统一成固定地点，方便统计图显示更整齐
    """
    place = normalize_text(place).lower()

    if not place:
        return "기타"

    if any(keyword in place for keyword in ["도서관", "library"]):
        return "도서관"

    if any(keyword in place for keyword in ["강의실", "교실", "lecture", "classroom"]):
        return "강의실"

    if any(keyword in place for keyword in ["기숙사", "숙소", "dorm"]):
        return "기숙사"

    if any(keyword in place for keyword in ["학생회관", "학생관", "student center"]):
        return "학생회관"

    if any(keyword in place for keyword in ["식당", "학식", "restaurant", "cafeteria"]):
        return "식당"

    if any(keyword in place for keyword in ["카페", "cafe", "coffee"]):
        return "카페"

    if any(keyword in place for keyword in ["운동장", "체육관", "gym", "stadium"]):
        return "운동장"

    if any(keyword in place for keyword in ["정문", "main gate"]):
        return "정문"

    if any(keyword in place for keyword in ["후문", "back gate"]):
        return "후문"

    if any(keyword in place for keyword in ["버스", "정류장", "bus stop"]):
        return "버스정류장"

    if any(keyword in place for keyword in ["주차장", "parking"]):
        return "주차장"

    return "기타"


def statistics_data():
    """
    统计页面需要的数据

    返回：
    total_lost: int
    total_found: int
    lost_stats: dict
    found_stats: dict
    location_stats: dict
    """

    # 1. 查询数据
    lost_items = LostItem.query.all()
    found_items = FoundItem.query.all()

    total_lost = len(lost_items)
    total_found = len(found_items)

    # 2. 分类统计
    lost_counter = Counter()
    found_counter = Counter()

    for item in lost_items:
        normalized_category = normalize_category(item.category, item.name)
        lost_counter[normalized_category] += 1

    for item in found_items:
        normalized_category = normalize_category(item.category, item.name)
        found_counter[normalized_category] += 1

    # 统一分类顺序：按 CATEGORIES 显示
    lost_stats = {}
    found_stats = {}

    for category in CATEGORIES:
        lost_stats[category] = lost_counter.get(category, 0)
        found_stats[category] = found_counter.get(category, 0)

    # 如果有 CATEGORIES 以外的数据，补进去
    extra_categories = sorted(
        (set(lost_counter.keys()) | set(found_counter.keys())) - set(CATEGORIES)
    )
    for category in extra_categories:
        lost_stats[category] = lost_counter.get(category, 0)
        found_stats[category] = found_counter.get(category, 0)

    # 3. 地点统计
    lost_place_counter = Counter()
    found_place_counter = Counter()

    for item in lost_items:
        normalized_place = normalize_place(item.place)
        lost_place_counter[normalized_place] += 1

    for item in found_items:
        normalized_place = normalize_place(item.place)
        found_place_counter[normalized_place] += 1

    location_stats = {}

    for place in LOCATIONS:
        location_stats[place] = {
            "lost": lost_place_counter.get(place, 0),
            "found": found_place_counter.get(place, 0),
        }

    # 如果有 LOCATIONS 以外的地点，补进去
    extra_places = sorted(
        (set(lost_place_counter.keys()) | set(found_place_counter.keys())) - set(LOCATIONS)
    )
    for place in extra_places:
        location_stats[place] = {
            "lost": lost_place_counter.get(place, 0),
            "found": found_place_counter.get(place, 0),
        }

    return total_lost, total_found, lost_stats, found_stats, location_stats