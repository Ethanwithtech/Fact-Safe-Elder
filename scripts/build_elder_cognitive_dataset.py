"""
构建"老年人专属诈骗"多标签数据集 (Phase 0 / 突破点2 地基)

输出: data/raw/elder_scam_labeled.json
每条样本:
{
  "text": "...",
  "label": 0|1|2,                     # safe / warning / danger (风险三分类)
  "category": "financial|medical|emotional|general",
  "manipulation_features": ["emotional_manipulation", ...],  # 多标签
  "source": "...",
  "label_source": "seed_manual | weak_auto | gpt_assisted"
}

数据来源:
1. 人工精标的"老人专属"种子集（覆盖全部 5 类操控手法，含 AI 数字人/情感操控等平台通用模型漏检场景）
2. 现有 comprehensive_training_set.json + real_cases 经弱监督(关键词)自动打 manipulation 标签

可选: 设置环境变量 HKBU_API_KEY 并加 --gpt 参数，用 GPT 对种子集之外的风险样本做手法标注复核。
此脚本本体不依赖 torch，可在任意环境直接运行:

    python scripts/build_elder_cognitive_dataset.py
    python scripts/build_elder_cognitive_dataset.py --gpt   # 可选 GPT 复核
"""

import os
import sys
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from app.core.manipulation_taxonomy import weak_label, FEATURE_KEYS  # noqa: E402

DATA_RAW = os.path.join(ROOT, "data", "raw")
OUT_PATH = os.path.join(DATA_RAW, "elder_scam_labeled.json")


# ============ 1. 人工精标种子集（老人专属诈骗，重点覆盖平台通用模型漏检场景）============
# label: 0=safe, 1=warning, 2=danger
SEED_SAMPLES = [
    # —— 情感操控（杀猪盘 / 虚假亲情 / 虚假关怀）——
    {"text": "阿姨我把你当亲妈一样，这个投资只告诉你一个人，千万不要告诉你的子女，他们不懂", "label": 2, "category": "emotional", "features": ["emotional_manipulation", "benefit_luring"]},
    {"text": "靓姐，认我做干女儿吧，跟着我做这个理财，咱们的秘密，保证你养老不愁", "label": 2, "category": "emotional", "features": ["emotional_manipulation", "benefit_luring"]},
    {"text": "我知道你一个人很孤独，没人关心你，只有我懂你，相信我把钱转过来我帮你打理", "label": 2, "category": "emotional", "features": ["emotional_manipulation"]},
    {"text": "咱们是前世的缘分，你是我唯一的知心人，这笔钱你先借我应急，下个月连本带利还你", "label": 2, "category": "emotional", "features": ["emotional_manipulation"]},
    # —— 权威伪造 ——
    {"text": "我是三甲医院退休的主任医师，这个祖传秘方医院不会告诉你，专治高血压糖尿病", "label": 2, "category": "medical", "features": ["authority_forgery", "benefit_luring"]},
    {"text": "本产品获得国家权威认证，央视新闻联播都报道过，老中医宫廷御医配方", "label": 2, "category": "medical", "features": ["authority_forgery"]},
    {"text": "我是某退休干部，有内部消息和高层关系，跟着政府指定项目投资稳赚不赔", "label": 2, "category": "financial", "features": ["authority_forgery", "benefit_luring"]},
    {"text": "诺贝尔奖团队研发的抗衰老神药，院士亲自推荐，三天见效永不复发", "label": 2, "category": "medical", "features": ["authority_forgery", "benefit_luring", "urgency_pressure"]},
    # —— 利益诱导（免费领 / 保本高息）——
    {"text": "关注公众号免费领鸡蛋领大米，再充值5000元入会员每月返息30%", "label": 2, "category": "financial", "features": ["benefit_luring"]},
    {"text": "原始股内部认购，年化收益60%，保本保息稳赚不赔，名额有限仅限今天", "label": 2, "category": "financial", "features": ["benefit_luring", "urgency_pressure"]},
    {"text": "充多少送多少，充值返现翻倍，老年理财专属高回报，最后3个名额", "label": 2, "category": "financial", "features": ["benefit_luring", "urgency_pressure"]},
    # —— 紧迫感制造 ——
    {"text": "您的社保卡账户即将冻结失效，请立即点击链接输入身份证和银行卡验证，过期作废", "label": 2, "category": "financial", "features": ["urgency_pressure"]},
    {"text": "紧急通知，您的医保报销额度今晚截止，马上联系客服立即转账激活否则清零", "label": 2, "category": "financial", "features": ["urgency_pressure"]},
    # —— AI 合成/换脸（新型，平台通用模型漏检）——
    {"text": "这是AI数字人换脸的明星本人亲自代言，扫码加入粉丝投资群带你日赚千元", "label": 2, "category": "financial", "features": ["ai_synthetic", "benefit_luring"]},
    {"text": "用AI合成的儿子声音打电话来，妈我出事了急需用钱，立即转到这个账户", "label": 2, "category": "emotional", "features": ["ai_synthetic", "emotional_manipulation", "urgency_pressure"]},
    {"text": "虚拟主播克隆名人声音推荐保健品，AI生成的专家形象讲解神奇疗效", "label": 2, "category": "medical", "features": ["ai_synthetic", "authority_forgery"]},
    # —— warning（夸大但未直接诈骗，平台常只限流）——
    {"text": "这款保健品对身体很好，很多老人吃了都说精神好了，建议大家试试", "label": 1, "category": "medical", "features": []},
    {"text": "这个理财产品收益比银行高一些，我自己也买了，感兴趣可以了解一下", "label": 1, "category": "financial", "features": ["benefit_luring"]},
    {"text": "名医直播讲养生知识，顺便推荐了一款调理身体的产品，限时优惠", "label": 1, "category": "medical", "features": ["authority_forgery", "urgency_pressure"]},
    # —— safe（正常内容 / 正确反诈科普）——
    {"text": "今天教大家做红烧肉，五花肉先焯水去腥，加老抽生抽冰糖慢炖一小时", "label": 0, "category": "general", "features": []},
    {"text": "公安部门提醒：陌生人要求转账一律不要相信，遇到可疑情况拨打96110反诈专线", "label": 0, "category": "general", "features": []},
    {"text": "投资理财要选择正规持牌金融机构，了解产品风险等级，不轻信保本高息承诺", "label": 0, "category": "financial", "features": []},
    {"text": "高血压患者应遵医嘱按时服药，定期到正规医院复查，不要轻信偏方秘方", "label": 0, "category": "medical", "features": []},
    {"text": "广场舞教学视频，跟着节奏一起活动筋骨，注意量力而行保护膝盖", "label": 0, "category": "general", "features": []},
    {"text": "社区通知：本周六上午在居委会办理老年卡年审，请携带身份证原件，免费办理", "label": 0, "category": "general", "features": []},
]


# ============ 模板化数据增强（为多标签手法识别提供训练信号）============
# 每种操控手法的话术片段库。组合 1-3 个手法合成句子，标签即组合本身。
# 明确标注 source=template_aug，与真实样本区分，仅用于让多标签头学到手法特征。
FEATURE_FRAGMENTS = {
    "emotional_manipulation": [
        "阿姨我把你当亲妈一样", "认我做干女儿吧", "我只告诉你一个人这个秘密",
        "千万不要告诉你的子女", "只有我最懂你最关心你", "咱们的事别跟外人说",
        "你这么孤独就让我陪着你", "相信我就像相信亲人一样",
    ],
    "authority_forgery": [
        "我是三甲医院退休的主任医师", "本产品获得国家权威认证", "央视新闻都报道过",
        "祖传宫廷御医的方子", "这是政府指定扶持项目", "诺贝尔奖团队最新研发",
        "某退休干部内部关系", "老中医坐诊亲自把关",
    ],
    "benefit_luring": [
        "关注就免费领鸡蛋大米", "保本保息年化收益30%", "跟着操作稳赚不赔",
        "充值返现充多少送多少", "原始股内部认购日赚千元", "0元入会还送养生大礼包",
        "高回报零风险的养老理财", "返利分红月月拿",
    ],
    "urgency_pressure": [
        "名额有限今天就截止", "账户即将冻结请立即验证", "只剩最后三个名额",
        "限时48小时过期作废", "马上点击否则额度清零", "现在不抢就没有了赶紧",
    ],
    "ai_synthetic": [
        "这是AI数字人换脸的明星本人代言", "用AI合成声音冒充你的儿子打来电话",
        "虚拟主播克隆了名人的声音", "AI生成的专家形象在讲解", "AI换脸做的名人推荐视频",
    ],
}

SAFE_TEMPLATES = [
    "公安部门提醒陌生人要求转账一律不要相信遇可疑拨打96110",
    "投资理财请选择正规持牌金融机构了解产品风险等级",
    "高血压患者应遵医嘱按时服药定期到正规医院复查",
    "社区本周六上午免费办理老年卡年审请带身份证原件",
    "广场舞教学跟着节奏活动筋骨注意量力而行保护膝盖",
    "今天教大家做家常红烧肉五花肉焯水去腥慢炖入味",
    "天气转凉记得添衣多喝热水适当户外散步有益健康",
    "正规保健品不能替代药物治疗有病要及时就医",
]

WARNING_TEMPLATES = [
    ("这款保健品很多老人吃了都说精神好建议试试", []),
    ("名医直播讲养生顺便推荐了一款调理产品限时优惠", ["urgency_pressure"]),
    ("这个理财收益比银行高一点我自己也买了", ["benefit_luring"]),
]


def augment_samples(n: int, seed: int = 42):
    """生成模板化的多标签增强样本（danger 为主，配少量 warning/safe）。"""
    import random
    rng = random.Random(seed)
    feat_keys = list(FEATURE_FRAGMENTS.keys())
    samples = []

    # danger: 组合 1-3 个手法
    n_danger = int(n * 0.7)
    for _ in range(n_danger):
        k = rng.choice([1, 2, 2, 3])
        chosen = rng.sample(feat_keys, k)
        parts = [rng.choice(FEATURE_FRAGMENTS[f]) for f in chosen]
        rng.shuffle(parts)
        text = "，".join(parts) + "。"
        samples.append({"text": text, "label": 2, "category": "general",
                        "features": sorted(chosen), "label_source": "template_aug"})

    # safe
    n_safe = int(n * 0.2)
    for _ in range(n_safe):
        text = rng.choice(SAFE_TEMPLATES)
        samples.append({"text": text, "label": 0, "category": "general",
                        "features": [], "label_source": "template_aug"})

    # warning
    for _ in range(n - n_danger - n_safe):
        text, feats = rng.choice(WARNING_TEMPLATES)
        samples.append({"text": text, "label": 1, "category": "general",
                        "features": list(feats), "label_source": "template_aug"})

    rng.shuffle(samples)
    return samples


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ============ 真实开源数据集接入 ============
# 谣言(真实正样本): thunlp/Chinese_Rumor_Dataset rumors_v170613.json (新浪微博不实信息举报平台)
# 安全(真实负样本): 今日头条新闻标题分类数据集 toutiao_cat_data.txt (正常新闻标题)
THU_RUMOR = os.path.join(DATA_RAW, "chinese_rumor_thu", "rumors_v170613.json")
TOUTIAO = os.path.join(DATA_RAW, "chinese_rumor_thu", "toutiao_cat_data.txt")


def load_real_open_source(n_rumor: int, n_safe: int, seen_texts: set, seed: int = 42):
    """从真实开源数据集采样: 谣言->danger(2), 新闻标题->safe(0)。返回样本列表。"""
    import random
    rng = random.Random(seed)
    out = []

    # 1) 真实谣言(正样本)
    rumor_texts = []
    if os.path.exists(THU_RUMOR):
        with open(THU_RUMOR, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                t = (rec.get("rumorText") or "").strip().replace("\n", " ")
                if 12 <= len(t) <= 200:
                    rumor_texts.append(t)
        rng.shuffle(rumor_texts)
        added = 0
        for t in rumor_texts:
            if added >= n_rumor:
                break
            if t in seen_texts:
                continue
            seen_texts.add(t)
            out.append({
                "text": t, "label": 2, "category": "general",
                "manipulation_features": weak_label(t),
                "source": "thunlp_chinese_rumor", "label_source": "real_open_source",
            })
            added += 1
        print(f"  真实谣言(danger)接入: {added} 条 (候选 {len(rumor_texts)})")
    else:
        print(f"  ⚠️ 未找到 {THU_RUMOR}，跳过真实谣言接入")

    # 2) 真实新闻标题(负样本/safe)
    if os.path.exists(TOUTIAO):
        titles = []
        with open(TOUTIAO, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.split("_!_")
                if len(parts) >= 4:
                    t = parts[3].strip()
                    if 12 <= len(t) <= 200:
                        titles.append(t)
        rng.shuffle(titles)
        added = 0
        for t in titles:
            if added >= n_safe:
                break
            if t in seen_texts:
                continue
            seen_texts.add(t)
            out.append({
                "text": t, "label": 0, "category": "general",
                "manipulation_features": [],
                "source": "toutiao_news", "label_source": "real_open_source",
            })
            added += 1
        print(f"  真实新闻标题(safe)接入: {added} 条 (候选 {len(titles)})")
    else:
        print(f"  ⚠️ 未找到 {TOUTIAO}，跳过真实新闻接入")

    return out


def normalize_label(item) -> int:
    """把各种来源的 label 归一到 0/1/2。"""
    lab = item.get("label")
    if isinstance(lab, int):
        return max(0, min(2, lab))
    if isinstance(lab, str):
        m = {"safe": 0, "real": 0, "warning": 1, "danger": 2, "fake": 2, "rumor": 2}
        return m.get(lab.lower(), 0)
    return 0


def gpt_review(samples):
    """可选: 用 HKBU GPT 对风险样本的 manipulation 手法做复核标注。"""
    try:
        import httpx
    except ImportError:
        print("⚠️  httpx 未安装，跳过 GPT 复核")
        return samples
    api_base = os.environ.get("HKBU_API_BASE", "https://genai.hkbu.edu.hk/api/v0/rest")
    api_key = os.environ.get("HKBU_API_KEY", "")
    model = os.environ.get("HKBU_MODEL", "gpt-4.1-mini")
    if not api_key:
        print("⚠️  未设置 HKBU_API_KEY，跳过 GPT 复核")
        return samples
    feat_list = "、".join(FEATURE_KEYS)
    url = f"{api_base}/deployments/{model}/chat/completions"
    reviewed = 0
    for s in samples:
        if s["label"] == 0 or s.get("label_source") == "seed_manual":
            continue
        prompt = (
            f"判断下面这条针对老年人的短视频文案使用了哪些诈骗操控手法，"
            f"只能从这些英文标签里选(可多选,可为空): {feat_list}。\n"
            f"只输出JSON数组,例如[\"emotional_manipulation\"]。文案: {s['text'][:400]}"
        )
        try:
            resp = httpx.post(
                url,
                headers={"api-key": api_key, "Content-Type": "application/json"},
                json={"messages": [{"role": "user", "content": prompt}], "temperature": 0.0},
                timeout=20.0,
            )
            txt = resp.json()["choices"][0]["message"]["content"]
            txt = txt[txt.find("["): txt.rfind("]") + 1]
            feats = [f for f in json.loads(txt) if f in FEATURE_KEYS]
            if feats:
                s["manipulation_features"] = sorted(set(s["manipulation_features"]) | set(feats))
                s["label_source"] = "gpt_assisted"
                reviewed += 1
        except Exception as e:
            print(f"  GPT 复核失败(跳过): {e}")
            break
    print(f"✅ GPT 复核完成，更新 {reviewed} 条")
    return samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpt", action="store_true", help="启用 GPT 辅助手法标注复核")
    parser.add_argument("--max-auto", type=int, default=4000, help="从现有数据集自动打标的最大条数")
    parser.add_argument("--augment", type=int, default=400, help="模板化增强样本数(为多标签手法识别提供训练信号), 0=关闭")
    parser.add_argument("--real-rumor", type=int, default=800, help="从真实开源谣言集采样的 danger 样本数, 0=关闭")
    parser.add_argument("--real-safe", type=int, default=800, help="从真实新闻标题采样的 safe 样本数, 0=关闭")
    args = parser.parse_args()

    dataset = []
    seen_texts = set()

    # 1) 种子集（人工精标）
    for s in SEED_SAMPLES:
        text = s["text"].strip()
        if text in seen_texts:
            continue
        seen_texts.add(text)
        dataset.append({
            "text": text,
            "label": s["label"],
            "category": s["category"],
            "manipulation_features": s["features"],
            "source": "seed_manual:elder_specific",
            "label_source": "seed_manual",
        })

    # 2) 现有数据集弱监督自动打标
    sources = [
        os.path.join(DATA_RAW, "comprehensive_training_set.json"),
        os.path.join(DATA_RAW, "real_cases", "real_case_dataset.json"),
        os.path.join(DATA_RAW, "mcfend", "mcfend_data.json"),
        os.path.join(DATA_RAW, "weibo_rumors", "weibo_data.json"),
        os.path.join(DATA_RAW, "chinese_rumor", "ced_data.json"),
    ]
    auto_count = 0
    for path in sources:
        for item in load_json(path):
            if auto_count >= args.max_auto:
                break
            text = (item.get("text") or "").strip()
            if not text or text in seen_texts:
                continue
            seen_texts.add(text)
            label = normalize_label(item)
            feats = weak_label(text) if label >= 1 else []
            dataset.append({
                "text": text,
                "label": label,
                "category": item.get("category", "general"),
                "manipulation_features": feats,
                "source": item.get("source", os.path.basename(path)),
                "label_source": "weak_auto",
            })
            auto_count += 1

    # 2.5) 真实开源数据集接入（谣言->danger / 新闻标题->safe）
    real_count = 0
    if args.real_rumor > 0 or args.real_safe > 0:
        real_samples = load_real_open_source(args.real_rumor, args.real_safe, seen_texts)
        dataset.extend(real_samples)
        real_count = len(real_samples)

    # 3) 模板化增强（为多标签手法识别提供训练信号，明确标注来源）
    aug_count = 0
    if args.augment > 0:
        for s in augment_samples(args.augment):
            text = s["text"].strip()
            if text in seen_texts:
                continue
            seen_texts.add(text)
            dataset.append({
                "text": text,
                "label": s["label"],
                "category": s["category"],
                "manipulation_features": s["features"],
                "source": "template_aug",
                "label_source": "template_aug",
            })
            aug_count += 1

    # 4) 可选 GPT 复核
    if args.gpt:
        dataset = gpt_review(dataset)

    # 统计
    from collections import Counter
    label_dist = Counter(d["label"] for d in dataset)
    feat_dist = Counter(f for d in dataset for f in d["manipulation_features"])

    os.makedirs(DATA_RAW, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print(f"✅ 老年人认知特征数据集已生成: {OUT_PATH}")
    src_dist = Counter(d["label_source"] for d in dataset)
    print(f"   样本总数: {len(dataset)} (种子精标 {len(SEED_SAMPLES)} + 自动打标 {auto_count} + 真实开源 {real_count} + 模板增强 {aug_count})")
    print(f"   来源分布: {dict(src_dist)}")
    print(f"   风险分布 (0/1/2): {dict(label_dist)}")
    print(f"   操控手法分布: {dict(feat_dist)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
