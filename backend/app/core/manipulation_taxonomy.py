"""
老年人认知操控特征分类法 (Elder Cognitive Manipulation Taxonomy)

这是 FactSafe 区别于大厂"通用反诈模型"的核心：针对老年人短视频诈骗，
显式建模诈骗分子使用的认知操控手法。该分类法被以下组件共用：

1. scripts/build_elder_cognitive_dataset.py  —— 弱监督自动打标（关键词/正则）
2. scripts/train_elder_cognitive_model.py    —— 多任务模型的标签空间
3. backend/app/services/multimodal_detector.py —— 推理时输出 manipulation_features
4. backend/app/services/case_retriever.py     —— 证据链中的"手法标注"

每个特征包含:
- key:        英文标识（模型多标签输出的列名，顺序固定）
- name_zh:    中文名
- name_yue:   粤语/书面广东话名（前端展示）
- desc:       含义说明（写入证据链解释）
- signals:    弱监督关键词/短语（用于自动打标与规则兜底）
"""

from typing import Dict, List

# 固定顺序 —— 多标签模型的输出维度顺序必须与此一致
MANIPULATION_FEATURES: List[Dict] = [
    {
        "key": "emotional_manipulation",
        "name_zh": "情感操控",
        "name_yue": "情感操控",
        "desc": "用亲昵称呼、排他承诺、虚假亲情或恐吓孤独感来建立信任并降低戒备，常见于'杀猪盘'、虚假关怀类诈骗。",
        "signals": [
            "干女儿", "干儿子", "认我做", "叫我一声", "我只告诉你",
            "不要告诉你的子女", "不要告诉家人", "只告诉你一个人", "咱们的秘密",
            "把你当亲人", "缘分", "前世", "唯一", "贴心", "陪伴你",
            "孤独", "没人关心你", "只有我懂你", "相信我",
            "靓姐", "靚姐", "阿姨", "叔叔", "老伴", "知心",
            "唔好話俾", "唔好同仔女講", "我淨係話俾你聽", "當你係親人",
        ],
    },
    {
        "key": "authority_forgery",
        "name_zh": "权威伪造",
        "name_yue": "權威偽造",
        "desc": "伪造专家、医生、官员、官方机构、央视背书或证书文件，借助权威光环骗取信任。",
        "signals": [
            "专家", "教授", "主任医师", "三甲医院", "权威认证", "国家认证",
            "央视", "新闻联播", "官方推荐", "政府指定", "公安提醒", "银保监",
            "证书", "红头文件", "内部消息", "高层关系", "退休干部", "老中医",
            "祖传", "宫廷御医", "诺贝尔", "院士",
            "專家", "教授", "三甲醫院", "權威認證", "國家認證", "官方推薦",
            "老中醫", "祖傳", "政府指定", "退休幹部",
        ],
    },
    {
        "key": "benefit_luring",
        "name_zh": "利益诱导",
        "name_yue": "利益誘導",
        "desc": "用免费领取、保本高息、名额有限、稳赚不赔等利益承诺，利用占便宜心理诱导参与。",
        "signals": [
            "免费领", "免费送", "免费领取", "0元", "领鸡蛋", "领米", "送大礼",
            "保本", "保息", "保证收益", "稳赚", "稳赚不赔", "高收益", "高回报",
            "年化", "日赚", "月入", "翻倍", "返现", "返利", "分红", "原始股",
            "充值返", "充多少送多少", "最后名额", "名额有限", "仅限",
            "免費領", "免費送", "保本", "保息", "保證收益", "穩賺", "高回報",
            "派米", "派蛋", "領大禮", "名額有限", "限量",
        ],
    },
    {
        "key": "urgency_pressure",
        "name_zh": "紧迫感制造",
        "name_yue": "緊迫感製造",
        "desc": "用倒计时、最后期限、立即行动、账户冻结等紧迫话术压缩思考时间，阻止老人咨询子女。",
        "signals": [
            "马上", "立即", "立刻", "赶紧", "尽快", "限时", "倒计时",
            "今天截止", "今晚截止", "最后一天", "最后机会", "过期作废",
            "即将失效", "账户冻结", "立即点击", "立即转账", "立即验证", "错过后悔",
            "馬上", "立即", "趕緊", "限時", "今晚截止", "最後機會",
            "即將失效", "賬戶凍結", "即刻", "而家就", "過期作廢",
        ],
    },
    {
        "key": "ai_synthetic",
        "name_zh": "AI合成/换脸",
        "name_yue": "AI合成/換臉",
        "desc": "使用 AI 数字人、AI 换脸、AI 合成语音冒充明星名人或亲属，是新型针对老人的诈骗手段，平台通用模型识别滞后。",
        "signals": [
            "ai换脸", "ai合成", "ai数字人", "数字人", "虚拟主播", "ai生成",
            "换脸", "合成语音", "克隆声音", "明星代言", "名人推荐", "本人亲自",
            "ai換臉", "ai合成", "數字人", "虛擬主播", "換臉", "克隆聲音",
            "明星代言", "名人推薦",
        ],
    },
]

# 顺序固定的 key 列表（模型多标签维度）
FEATURE_KEYS: List[str] = [f["key"] for f in MANIPULATION_FEATURES]

# 便捷查表
FEATURE_BY_KEY: Dict[str, Dict] = {f["key"]: f for f in MANIPULATION_FEATURES}


def weak_label(text: str) -> List[str]:
    """
    基于关键词/短语的弱监督打标，返回命中的 manipulation 特征 key 列表。
    用于自动构建训练标签 + 推理时的规则兜底（当模型不可用时）。
    """
    if not text:
        return []
    t = text.lower()
    hits: List[str] = []
    for feat in MANIPULATION_FEATURES:
        for sig in feat["signals"]:
            if sig.lower() in t:
                hits.append(feat["key"])
                break
    return hits


def feature_to_multihot(keys: List[str]) -> List[int]:
    """把特征 key 列表转成固定顺序的 multi-hot 向量。"""
    keyset = set(keys or [])
    return [1 if k in keyset else 0 for k in FEATURE_KEYS]


def multihot_to_features(vec: List[float], threshold: float = 0.5) -> List[str]:
    """把模型输出的多标签概率向量转回命中的特征 key 列表。"""
    out: List[str] = []
    for i, p in enumerate(vec):
        if i < len(FEATURE_KEYS) and float(p) >= threshold:
            out.append(FEATURE_KEYS[i])
    return out


def describe_features(keys: List[str], lang: str = "zh") -> List[Dict]:
    """把特征 key 列表展开成 {key,name,desc} 便于前端证据链展示。"""
    out: List[Dict] = []
    for k in keys or []:
        f = FEATURE_BY_KEY.get(k)
        if not f:
            continue
        out.append({
            "key": k,
            "name": f["name_yue"] if lang == "yue" else f["name_zh"],
            "desc": f["desc"],
        })
    return out


__all__ = [
    "MANIPULATION_FEATURES",
    "FEATURE_KEYS",
    "FEATURE_BY_KEY",
    "weak_label",
    "feature_to_multihot",
    "multihot_to_features",
    "describe_features",
]
