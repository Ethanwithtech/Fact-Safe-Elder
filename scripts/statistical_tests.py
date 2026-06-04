"""
统计显著性测试工具
用于验证 FYP Final Report 中的统计结论

功能:
- Paired t-test (配对 t 检验): 比较两个方法在相同数据集上的性能
- One-sample t-test (单样本 t 检验): 检验样本均值是否显著不同于已知总体均值
- K-fold Cross-Validation (K 折交叉验证): 评估模型泛化性能

引用:
- Section 4.3: "5-fold cross-validation, paired t-test p=0.003"
- Section 4.5: "OOD paired t-test p=0.028"
- Section 4.12: "UAT one-sample t-test t(9)=1.98, p=0.042"

作者: DENG Yuchen, Ethan
"""

import numpy as np
from scipy import stats
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import json


@dataclass
class TTestResult:
    """t 检验结果"""
    t_statistic: float
    p_value: float
    df: int  # 自由度
    mean_diff: Optional[float] = None
    ci_95: Optional[Tuple[float, float]] = None  # 95% 置信区间
    significant: bool = False  # p < 0.05 是否显著
    interpretation: str = ""


@dataclass
class CrossValidationResult:
    """交叉验证结果"""
    mean_score: float
    std_score: float
    scores: List[float]
    ci_95: Tuple[float, float]
    n_splits: int


def paired_t_test(
    method_a_scores: List[float],
    method_b_scores: List[float],
    alpha: float = 0.05
) -> TTestResult:
    """
    配对 t 检验 (Paired t-test)
    
    用于比较两个方法在**相同数据集**上的性能差异是否显著
    
    Args:
        method_a_scores: 方法 A 的得分列表 (如: 加了安全阀后的 F1 分数)
        method_b_scores: 方法 B 的得分列表 (如: 基线方法的 F1 分数)
        alpha: 显著性水平 (默认 0.05)
    
    Returns:
        TTestResult 对象
    
    示例:
        >>> # Section 4.3: 安全阀 vs 基线
        >>> with_valve = [0.970, 0.968, 0.972, 0.965, 0.971]
        >>> baseline = [0.952, 0.950, 0.955, 0.948, 0.953]
        >>> result = paired_t_test(with_valve, baseline)
        >>> print(f"p={result.p_value:.4f}, significant={result.significant}")
    """
    if len(method_a_scores) != len(method_b_scores):
        raise ValueError(f"样本量不一致: {len(method_a_scores)} vs {len(method_b_scores)}")
    
    if len(method_a_scores) < 2:
        raise ValueError("样本量至少需要 2 对数据")
    
    scores_a = np.array(method_a_scores)
    scores_b = np.array(method_b_scores)
    
    # 配对 t 检验
    t_stat, p_value = stats.ttest_rel(scores_a, scores_b)
    
    # 计算均值差异和置信区间
    diffs = scores_a - scores_b
    mean_diff = np.mean(diffs)
    se = stats.sem(diffs)  # 标准误
    ci_95 = stats.t.interval(
        0.95,
        df=len(diffs) - 1,
        loc=mean_diff,
        scale=se
    )
    
    # 判断是否显著
    significant = bool(p_value < alpha)
    
    # 解释
    direction = "优于" if mean_diff > 0 else "劣于"
    if significant:
        interpretation = (
            f"方法 A {direction} 方法 B (平均差异={mean_diff:.4f}, p={p_value:.4f} < {alpha})，"
            f"差异具有统计学显著性"
        )
    else:
        interpretation = (
            f"方法 A 与方法 B 的差异 (平均={mean_diff:.4f}, p={p_value:.4f} >= {alpha}) "
            f"不具有统计学显著性"
        )
    
    return TTestResult(
        t_statistic=float(t_stat),
        p_value=float(p_value),
        df=len(diffs) - 1,
        mean_diff=float(mean_diff),
        ci_95=(float(ci_95[0]), float(ci_95[1])),
        significant=significant,
        interpretation=interpretation
    )


def one_sample_t_test(
    sample_scores: List[float],
    population_mean: float,
    alpha: float = 0.05
) -> TTestResult:
    """
    单样本 t 检验 (One-sample t-test)
    
    用于检验样本均值是否显著不同于已知的总体均值 (或理论值)
    
    Args:
        sample_scores: 样本得分列表 (如: UAT 的 10 个 SUS 分数)
        population_mean: 总体均值 (如: SUS 行业平均分 68)
        alpha: 显著性水平
    
    Returns:
        TTestResult 对象
    
    示例:
        >>> # Section 4.12: UAT SUS 分数 vs 行业平均
        >>> sus_scores = [75, 80, 65, 70, 78, 72, 68, 77, 71, 69]
        >>> result = one_sample_t_test(sus_scores, population_mean=68)
        >>> print(f"t({result.df})={result.t_statistic:.2f}, p={result.p_value:.3f}")
    """
    if len(sample_scores) < 2:
        raise ValueError("样本量至少需要 2")
    
    scores = np.array(sample_scores)
    
    # 单样本 t 检验
    t_stat, p_value = stats.ttest_1samp(scores, population_mean)
    
    # 计算样本统计量
    sample_mean = np.mean(scores)
    se = stats.sem(scores)
    ci_95 = stats.t.interval(
        0.95,
        df=len(scores) - 1,
        loc=sample_mean,
        scale=se
    )
    
    significant = bool(p_value < alpha)
    
    # 解释
    direction = "高于" if sample_mean > population_mean else "低于"
    if significant:
        interpretation = (
            f"样本均值 {sample_mean:.2f} {direction} 总体均值 {population_mean:.2f}, "
            f"t({len(scores)-1})={t_stat:.2f}, p={p_value:.4f} < {alpha}, "
            f"差异具有统计学显著性"
        )
    else:
        interpretation = (
            f"样本均值 {sample_mean:.2f} 与总体均值 {population_mean:.2f} 的差异 "
            f"(t({len(scores)-1})={t_stat:.2f}, p={p_value:.4f} >= {alpha}) "
            f"不具有统计学显著性"
        )
    
    return TTestResult(
        t_statistic=float(t_stat),
        p_value=float(p_value),
        df=len(scores) - 1,
        mean_diff=float(sample_mean - population_mean),
        ci_95=(float(ci_95[0]), float(ci_95[1])),
        significant=significant,
        interpretation=interpretation
    )


def k_fold_cross_validation(
    X: np.ndarray,
    y: np.ndarray,
    model,
    n_splits: int = 5,
    metric_fn=None,
    random_state: int = 42
) -> CrossValidationResult:
    """
    K 折交叉验证
    
    用于评估模型泛化性能,避免过拟合
    
    Args:
        X: 特征矩阵
        y: 标签向量
        model: sklearn 兼容的模型 (需有 fit/predict 方法)
        n_splits: 折数 (默认 5)
        metric_fn: 评估指标函数 (默认使用 accuracy)
        random_state: 随机种子
    
    Returns:
        CrossValidationResult 对象
    
    示例:
        >>> from sklearn.ensemble import RandomForestClassifier
        >>> from sklearn.metrics import f1_score
        >>> 
        >>> model = RandomForestClassifier(random_state=42)
        >>> result = k_fold_cross_validation(X, y, model, metric_fn=f1_score)
        >>> print(f"Mean F1: {result.mean_score:.3f} ± {result.std_score:.3f}")
    """
    from sklearn.model_selection import KFold
    from sklearn.metrics import accuracy_score
    
    if metric_fn is None:
        metric_fn = accuracy_score
    
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    scores = []
    
    for train_idx, val_idx in kf.split(X):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        
        model.fit(X_train, y_train)
        y_pred = model.predict(X_val)
        
        score = metric_fn(y_val, y_pred)
        scores.append(score)
    
    scores_arr = np.array(scores)
    mean_score = np.mean(scores_arr)
    std_score = np.std(scores_arr, ddof=1)  # 样本标准差
    
    # 95% 置信区间
    se = std_score / np.sqrt(n_splits)
    ci_95 = stats.t.interval(
        0.95,
        df=n_splits - 1,
        loc=mean_score,
        scale=se
    )
    
    return CrossValidationResult(
        mean_score=float(mean_score),
        std_score=float(std_score),
        scores=[float(s) for s in scores],
        ci_95=(float(ci_95[0]), float(ci_95[1])),
        n_splits=n_splits
    )


import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_labeled_binary():
    """读取 elder_scam_labeled.json，返回 (texts, y_binary[risky=1/safe=0])。"""
    path = os.path.join(ROOT, "data", "raw", "elder_scam_labeled.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    texts = [d.get("text", "") for d in data]
    y = [1 if int(d.get("label", 0)) >= 1 else 0 for d in data]
    return texts, y


def real_model_vs_rule_cv(n_splits: int = 5, seed: int = 42):
    """
    真实 5 折交叉验证（不再用硬编码数字）：
      - 模型组: TF-IDF(char n-gram) + LogisticRegression
      - 基线组: 关键词规则（命中操控手法词即判风险）
    返回每折 F1 列表，可直接做配对 t 检验。
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold
    from sklearn.metrics import f1_score
    import sys as _sys
    _sys.path.insert(0, os.path.join(ROOT, "backend"))
    from app.core.manipulation_taxonomy import weak_label

    # 规则基线兜底关键词（与生产规则引擎同源的高频诈骗词）
    RULE_KW = ["保证收益", "无风险", "稳赚", "包治百病", "祖传秘方", "免费领", "转账",
               "加微信", "限时", "立即", "名额有限", "原始股", "高收益", "特效药"]

    texts, y = _load_labeled_binary()
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    model_f1, rule_f1 = [], []
    for tr, va in skf.split(texts, y):
        tr_t = [texts[i] for i in tr]; tr_y = [y[i] for i in tr]
        va_t = [texts[i] for i in va]; va_y = [y[i] for i in va]
        vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
        Xtr = vec.fit_transform(tr_t)
        clf = LogisticRegression(max_iter=1000, class_weight="balanced")
        clf.fit(Xtr, tr_y)
        pred = clf.predict(vec.transform(va_t))
        model_f1.append(float(f1_score(va_y, pred, zero_division=0)))
        rule_pred = [1 if (weak_label(t) or any(k in t for k in RULE_KW)) else 0 for t in va_t]
        rule_f1.append(float(f1_score(va_y, rule_pred, zero_division=0)))
    return model_f1, rule_f1


def crossmodal_paired_test():
    """从 crossmodal_eval_results.json 取真实逐样本正确性做配对检验（基线融合 vs 联合推理）。"""
    path = os.path.join(ROOT, "scripts", "crossmodal_eval_results.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("rows", [])
    base_c, joint_c = [], []
    for r in rows:
        exp = r.get("expected_danger")
        base_c.append(1.0 if r["baseline"]["danger"] == exp else 0.0)
        joint_c.append(1.0 if r["joint"]["danger"] == exp else 0.0)
    if len(base_c) < 2:
        return None
    return base_c, joint_c, data.get("summary", {})


def report_statistical_tests() -> Dict[str, Any]:
    """
    用**真实实验数据**复现统计检验（替换原硬编码数字）。
    """
    results: Dict[str, Any] = {}

    # ===== 真实 5 折 CV：TF-IDF 模型 vs 关键词规则基线 =====
    try:
        model_f1, rule_f1 = real_model_vs_rule_cv()
        results["model_vs_rule_cv"] = {
            "type": "paired_t_test",
            "model_f1_per_fold": [round(x, 4) for x in model_f1],
            "rule_f1_per_fold": [round(x, 4) for x in rule_f1],
            "result": paired_t_test(model_f1, rule_f1),
            "cv_summary": {
                "model_mean_f1": round(float(np.mean(model_f1)), 4),
                "model_std": round(float(np.std(model_f1, ddof=1)), 4),
                "rule_mean_f1": round(float(np.mean(rule_f1)), 4),
            },
            "data_source": "data/raw/elder_scam_labeled.json (真实标注集, 5-fold StratifiedKFold)",
        }
    except Exception as e:
        results["model_vs_rule_cv"] = {"error": str(e), "note": "需要 scikit-learn 与标注数据集"}

    # ===== 真实跨模态：单模态融合 vs 联合推理 =====
    cm = crossmodal_paired_test()
    if cm:
        base_c, joint_c, summary = cm
        entry = {
            "type": "paired_t_test",
            "result": paired_t_test(joint_c, base_c) if sum(joint_c) != sum(base_c) else None,
            "summary": summary,
            "data_source": "scripts/crossmodal_eval_results.json (eval_crossmodal.py 真实输出)",
            "note": "逐样本正确性配对检验；样本量小时建议结合 McNemar 检验解读",
        }
        results["crossmodal_joint_vs_baseline"] = entry
    else:
        results["crossmodal_joint_vs_baseline"] = {
            "note": "未找到 crossmodal_eval_results.json，请先运行 python scripts/eval_crossmodal.py",
        }

    # ===== UAT SUS：无真实问卷数据时不编造，标记待补 =====
    sus_path = os.path.join(ROOT, "data", "raw", "uat_sus_scores.json")
    if os.path.exists(sus_path):
        with open(sus_path, "r", encoding="utf-8") as f:
            sus_scores = json.load(f)
        results["uat_sus_vs_industry"] = {
            "type": "one_sample_t_test",
            "result": one_sample_t_test(sus_scores, 68),
            "data_source": sus_path,
        }
    else:
        results["uat_sus_vs_industry"] = {
            "status": "PENDING_REAL_USER_STUDY",
            "note": "SUS 可用性得分需真实老年用户测试采集；为保证科学诚信，未采集到数据前不提供任何分数。"
                    "采集后将数据写入 data/raw/uat_sus_scores.json 即可自动计算。",
        }

    return results


def _serialize(obj):
    if isinstance(obj, TTestResult):
        return {
            "t_statistic": obj.t_statistic, "p_value": obj.p_value, "df": obj.df,
            "mean_diff": obj.mean_diff, "ci_95": list(obj.ci_95) if obj.ci_95 else None,
            "significant": obj.significant, "interpretation": obj.interpretation,
        }
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    return obj


def main():
    """运行真实统计检验并打印结果"""
    print("=" * 80)
    print("FactSafe 统计显著性检验报告 (真实实验数据)")
    print("=" * 80)
    print()

    results = report_statistical_tests()
    output = _serialize(results)

    for name, entry in output.items():
        print(f"【{name}】")
        if isinstance(entry, dict):
            res = entry.get("result")
            if isinstance(res, dict):
                print(f"  t({res['df']})={res['t_statistic']:.4f}  p={res['p_value']:.4f}  "
                      f"significant={res['significant']}")
                print(f"  {res['interpretation']}")
            if entry.get("cv_summary"):
                print(f"  CV: {entry['cv_summary']}")
            if entry.get("status"):
                print(f"  状态: {entry['status']} — {entry.get('note','')}")
            elif entry.get("note") and not res:
                print(f"  说明: {entry['note']}")
        print()

    out_path = os.path.join(ROOT, "scripts", "statistical_tests_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"✅ 结果已保存到 {out_path}")


if __name__ == '__main__':
    main()
