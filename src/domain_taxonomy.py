# -*- coding: utf-8 -*-
"""Canonical domain aliases and keyword routing for private autopilot modules.

``art_direction`` and ``visual_director`` used to carry near-identical maps.
Keeping the taxonomy here prevents a new topic from routing to one visual theme
but a different editing grammar.  The public motion kit remains standalone and
owns its finer style routing; this module only chooses the broad editing domain.
"""
from __future__ import annotations

from collections.abc import Collection


DOMAIN_ALIASES = {
    "teaching": "ai", "tech": "ai", "tutorial": "ai", "教育": "ai", "教學": "ai", "科技": "ai",
    "美食": "food", "餐廳": "food", "料理": "food", "ramen": "food",
    "旅遊": "travel", "旅行": "travel", "景點": "travel", "vlog": "travel",
    "unboxing": "product", "開箱": "product", "3c": "product", "review": "product", "評測": "product",
    "玩具": "toy", "模型": "toy", "公仔": "toy",
    "gaming": "game", "遊戲": "game", "gameplay": "game",
    "手作": "diy", "製作": "diy", "改造": "diy",
    "coffee": "cafe", "咖啡": "cafe", "甜點": "cafe", "dessert": "cafe",
    "紀錄片": "documentary", "紀實": "documentary", "doc": "documentary",
    "訪談": "interview", "專訪": "interview", "interview": "interview", "podcast": "interview",
    "重機": "automotive", "汽車": "automotive", "機車": "automotive", "motovlog": "automotive",
    "健身": "fitness", "運動": "fitness", "fitness": "fitness",
    "時尚": "fashion", "穿搭": "fashion", "美妝": "fashion", "fashion": "fashion",
    "建築": "architecture", "室內": "architecture", "空間": "architecture",
    "商業": "business", "財經": "business", "創業": "business", "business": "business",
    "寵物": "nature", "生態": "nature", "自然": "nature", "nature": "nature",
    "音樂": "music", "演出": "music", "music": "music",
    "產品": "product", "product": "product",
}


# Order is the deterministic tie-break.  Product precedes toy so a generic
# 「開箱」 routes to product; an explicit 玩具／模型／公仔 still routes to toy.
DOMAIN_KEYWORDS = {
    "ai": ("ai", "人工智慧", "claude", "chatgpt", "prompt", "教學", "軟體", "工具", "code", "程式"),
    "food": ("美食", "餐廳", "小吃", "拉麵", "料理", "吃", "菜單", "價格", "夜市"),
    "travel": ("旅遊", "旅行", "景點", "飯店", "出國", "登山", "海邊", "城市", "散步"),
    "product": ("3c", "手機", "相機", "評測", "產品", "規格", "科技開箱", "開箱"),
    "toy": ("玩具", "模型", "公仔", "盲盒", "收藏", "lego", "樂高"),
    "game": ("遊戲", "game", "boss", "戰鬥", "抽卡", "角色", "steam", "gameplay"),
    "diy": ("diy", "手作", "改造", "組裝", "製作", "修理", "教你做"),
    "cafe": ("咖啡", "甜點", "下午茶", "烘焙", "拿鐵"),
    "documentary": ("紀錄片", "紀實", "田野", "調查", "真相", "人物故事", "幕後"),
    "interview": ("訪談", "專訪", "對談", "來賓", "podcast", "人物訪問"),
    "automotive": ("重機", "機車", "摩托", "汽車", "跑車", "試駕", "騎乘", "motovlog"),
    "fitness": ("健身", "訓練", "運動", "跑步", "重訓", "肌肉", "瑜伽"),
    "fashion": ("時尚", "穿搭", "美妝", "妝容", "保養", "outfit", "makeup"),
    "architecture": ("建築", "室內", "空間", "裝潢", "房子", "house tour", "格局"),
    "business": ("商業", "創業", "行銷", "銷售", "財經", "投資", "營收", "品牌"),
    "nature": ("寵物", "生態", "動物", "野生", "鳥", "貓", "狗", "自然"),
    "music": ("音樂", "演出", "樂團", "演唱", "cover", "舞蹈", "舞台"),
}

SUPPORTED_DOMAINS = tuple(DOMAIN_KEYWORDS) + ("general",)


def normalize_domain(value: str | None, allowed: Collection[str] | None = None) -> str:
    """Normalize an explicit domain hint, falling back to ``general``."""
    key = str(value or "general").strip().lower()
    key = DOMAIN_ALIASES.get(key, key)
    valid = set(allowed or SUPPORTED_DOMAINS)
    return key if key in valid else "general"


def score_domains(text: str = "", allowed: Collection[str] | None = None) -> dict[str, int]:
    """Return explainable substring scores in canonical tie-break order."""
    src = str(text or "").lower()
    valid = set(allowed or SUPPORTED_DOMAINS)
    return {
        domain: sum(src.count(word.lower()) for word in words)
        for domain, words in DOMAIN_KEYWORDS.items()
        if domain in valid
    }


def infer_domain(text: str = "", hint: str | None = None,
                 allowed: Collection[str] | None = None) -> str:
    """Prefer an explicit hint, otherwise route with deterministic keyword scores."""
    raw_hint = str(hint or "").strip().lower()
    if raw_hint not in ("", "auto", "none"):
        normalized = normalize_domain(raw_hint, allowed)
        if normalized != "general" or raw_hint == "general":
            return normalized
    scores = score_domains(text, allowed)
    best = max(scores, key=scores.get) if scores else "general"
    return best if scores.get(best, 0) > 0 else "general"


def self_test() -> None:
    assert infer_domain("Claude AI 教學") == "ai"
    assert infer_domain("拉麵價格與夜市小吃") == "food"
    assert infer_domain("手機相機盲測評測") == "product"
    assert infer_domain("重機試駕與過彎") == "automotive"
    assert infer_domain("anything", "玩具") == "toy"
    assert normalize_domain("unknown") == "general"
    print("domain_taxonomy self-test GREEN")


if __name__ == "__main__":
    self_test()
