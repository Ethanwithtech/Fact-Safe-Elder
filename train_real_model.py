#!/usr/bin/env python3
"""
真实AI模型训练脚本
使用sklearn训练虚假信息检测模型
"""

import os
import json
import joblib
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, classification_report

print("""
╔════════════════════════════════════════════════════════════╗
║     真实AI模型训练脚本                                      ║
║     使用sklearn训练虚假信息检测模型                          ║
╚════════════════════════════════════════════════════════════╝
""")

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"


def load_all_datasets():
    """加载所有可用数据集"""
    texts = []
    labels = []
    
    # 标签映射
    label_to_int = {'safe': 0, 'warning': 1, 'danger': 2}
    
    # 1. 加载真实数据集
    real_datasets_path = DATA_DIR / "real_datasets" / "combined"
    for split in ['train', 'val', 'test']:
        split_file = real_datasets_path / f"{split}.json"
        if split_file.exists():
            with open(split_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    text = item.get('text', '')
                    label_str = item.get('label', 'safe')
                    if text and label_str in label_to_int:
                        texts.append(text)
                        labels.append(label_to_int[label_str])
    
    # 2. 加载mcfend数据集
    mcfend_path = DATA_DIR / "raw" / "mcfend" / "mcfend_data.json"
    if mcfend_path.exists():
        with open(mcfend_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                text = item.get('text', '')
                label = item.get('label', '')
                if text:
                    # 映射标签
                    if label in ['fake', 'rumor']:
                        labels.append(2)  # danger
                    elif label in ['real', 'non-rumor']:
                        labels.append(0)  # safe
                    else:
                        labels.append(1)  # warning
                    texts.append(text)
    
    # 3. 加载weibo数据集
    weibo_path = DATA_DIR / "raw" / "weibo_rumors" / "weibo_data.json"
    if weibo_path.exists():
        with open(weibo_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                text = item.get('text', '')
                label = item.get('label', '')
                if text:
                    if label in ['rumor']:
                        labels.append(2)  # danger
                    elif label in ['real']:
                        labels.append(0)  # safe
                    else:
                        labels.append(1)  # warning
                    texts.append(text)
    
    # 4. 加载真实案例
    real_cases_path = DATA_DIR / "raw" / "real_cases" / "real_case_dataset.json"
    if real_cases_path.exists():
        with open(real_cases_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                text = item.get('text', '')
                label_str = item.get('label', '')
                if text and label_str in label_to_int:
                    texts.append(text)
                    labels.append(label_to_int[label_str])
    
    print(f"[OK] 总共加载 {len(texts)} 条数据")
    
    # 显示标签分布
    from collections import Counter
    label_counts = Counter(labels)
    print(f"[INFO] 标签分布:")
    print(f"  - safe (0): {label_counts.get(0, 0)}")
    print(f"  - warning (1): {label_counts.get(1, 0)}")
    print(f"  - danger (2): {label_counts.get(2, 0)}")
    
    return texts, labels


def train_models(texts, labels):
    """训练多个模型并选择最佳模型"""
    
    # 数据分割
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )
    
    print(f"\n[INFO] 训练集: {len(X_train)} 样本")
    print(f"[INFO] 测试集: {len(X_test)} 样本")
    
    # TF-IDF 向量化
    print("\n[STEP 1] TF-IDF向量化...")
    vectorizer = TfidfVectorizer(
        max_features=10000,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95
    )
    
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)
    
    print(f"[OK] 特征数量: {X_train_tfidf.shape[1]}")
    
    # 训练多个模型
    models = {
        'LogisticRegression': LogisticRegression(
            max_iter=1000,
            class_weight='balanced',
            random_state=42
        ),
        'RandomForest': RandomForestClassifier(
            n_estimators=100,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        ),
        'GradientBoosting': GradientBoostingClassifier(
            n_estimators=100,
            random_state=42
        )
    }
    
    best_model = None
    best_model_name = None
    best_f1 = 0
    
    print("\n[STEP 2] 训练模型...")
    
    for name, model in models.items():
        print(f"\n  训练 {name}...")
        model.fit(X_train_tfidf, y_train)
        
        # 预测
        y_pred = model.predict(X_test_tfidf)
        
        # 评估
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='weighted')
        precision = precision_score(y_test, y_pred, average='weighted')
        recall = recall_score(y_test, y_pred, average='weighted')
        
        print(f"  {name} 结果:")
        print(f"    准确率: {acc:.4f}")
        print(f"    F1分数: {f1:.4f}")
        print(f"    精确率: {precision:.4f}")
        print(f"    召回率: {recall:.4f}")
        
        if f1 > best_f1:
            best_f1 = f1
            best_model = model
            best_model_name = name
    
    print(f"\n[OK] 最佳模型: {best_model_name} (F1={best_f1:.4f})")
    
    # 详细评估最佳模型
    y_pred = best_model.predict(X_test_tfidf)
    
    print(f"\n[STEP 3] 最佳模型详细评估:")
    print(classification_report(
        y_test, y_pred,
        target_names=['safe', 'warning', 'danger']
    ))
    
    return best_model, best_model_name, vectorizer, {
        'accuracy': accuracy_score(y_test, y_pred),
        'f1': f1_score(y_test, y_pred, average='weighted'),
        'precision': precision_score(y_test, y_pred, average='weighted'),
        'recall': recall_score(y_test, y_pred, average='weighted')
    }


def save_model(model, model_name, vectorizer, metrics):
    """保存模型"""
    output_dir = MODELS_DIR / "trained"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = output_dir / "simple_ai_model.joblib"
    
    model_data = {
        'model': model,
        'vectorizer': vectorizer,
        'model_name': model_name,
        'metrics': metrics,
        'label_map': {0: 'safe', 1: 'warning', 2: 'danger'}
    }
    
    joblib.dump(model_data, model_path)
    print(f"\n[OK] 模型已保存到: {model_path}")
    
    # 保存指标到JSON
    metrics_path = output_dir / "model_metrics.json"
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump({
            'model_name': model_name,
            'metrics': metrics,
            'model_path': str(model_path)
        }, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] 指标已保存到: {metrics_path}")


def test_model(model_path):
    """测试已保存的模型"""
    print("\n[STEP 4] 测试保存的模型...")
    
    model_data = joblib.load(model_path)
    model = model_data['model']
    vectorizer = model_data['vectorizer']
    label_map = model_data['label_map']
    
    test_texts = [
        "投资虚拟货币，保证高额回报，稳赚不赔！",
        "祖传秘方，包治百病，一次根治永不复发！",
        "今天天气真好，适合出去散步。",
        "限时抢购，错过再无！快点击链接购买！",
        "这款保健品可以延年益寿，效果神奇",
    ]
    
    print("\n测试样例预测:")
    for text in test_texts:
        text_vec = vectorizer.transform([text])
        pred = model.predict(text_vec)[0]
        proba = model.predict_proba(text_vec)[0]
        label = label_map[pred]
        
        print(f"\n  文本: {text[:40]}...")
        print(f"  预测: {label}")
        print(f"  概率: safe={proba[0]:.2f}, warning={proba[1]:.2f}, danger={proba[2]:.2f}")


def main():
    # 加载数据
    texts, labels = load_all_datasets()
    
    if len(texts) < 10:
        print("[ERROR] 数据量不足，请先运行 download_real_training_data.py")
        return
    
    # 训练模型
    model, model_name, vectorizer, metrics = train_models(texts, labels)
    
    # 保存模型
    save_model(model, model_name, vectorizer, metrics)
    
    # 测试模型
    model_path = MODELS_DIR / "trained" / "simple_ai_model.joblib"
    test_model(model_path)
    
    print("""
╔════════════════════════════════════════════════════════════╗
║     训练完成！                                              ║
╠════════════════════════════════════════════════════════════╣
║  模型已保存到 models/trained/simple_ai_model.joblib        ║
║  重启后端服务即可使用新模型                                 ║
╚════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()









