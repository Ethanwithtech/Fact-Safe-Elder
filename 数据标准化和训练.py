#!/usr/bin/env python3
"""
数据标准化和高准确率模型训练
"""
import json
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import classification_report, accuracy_score, f1_score
from datetime import datetime
from pathlib import Path

class AdvancedTrainer:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.data_file = self.project_root / "data/raw/comprehensive_training_set.json"
        self.model_dir = self.project_root / "models/trained"
        self.model_dir.mkdir(parents=True, exist_ok=True)
    
    def load_and_standardize_data(self):
        """加载并标准化数据"""
        print("[1/6] 加载训练数据...")
        
        with open(self.data_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        print(f"  原始数据: {len(raw_data)} 条")
        
        # 标准化标签
        texts = []
        labels = []
        
        for item in raw_data:
            text = item.get('text', '').strip()
            if not text:
                continue
            
            # 统一标签格式
            label = item.get('label')
            if label in [2, 'fake', 'rumor', '谣言', '虚假']:
                standard_label = 1  # 假消息
            elif label in [0, 'real', 'true', '真实']:
                standard_label = 0  # 真消息
            else:
                continue  # 跳过未知标签
            
            texts.append(text)
            labels.append(standard_label)
        
        print(f"  标准化后: {len(texts)} 条")
        print(f"  真实消息: {labels.count(0)} 条")
        print(f"  虚假消息: {labels.count(1)} 条")
        
        return texts, labels
    
    def augment_data(self, texts, labels):
        """数据增强（简单版本）"""
        print("[2/6] 数据增强...")
        
        # 当前简单返回，可以后续添加同义词替换、回译等技术
        print(f"  增强后数据量: {len(texts)} 条")
        return texts, labels
    
    def train_models(self, X_train, X_test, y_train, y_test):
        """训练多个模型并集成"""
        print("[3/6] 训练多个模型...")
        
        models = {}
        
        # 1. SVM (最好的单模型)
        print("  [1/4] 训练SVM...")
        svm = SVC(
            kernel='linear',
            C=1.0,
            probability=True,
            random_state=42,
            class_weight='balanced'
        )
        svm.fit(X_train, y_train)
        svm_acc = accuracy_score(y_test, svm.predict(X_test))
        print(f"    SVM准确率: {svm_acc:.4f}")
        models['svm'] = (svm, svm_acc)
        
        # 2. Random Forest
        print("  [2/4] 训练Random Forest...")
        rf = RandomForestClassifier(
            n_estimators=200,
            max_depth=20,
            min_samples_split=5,
            random_state=42,
            class_weight='balanced',
            n_jobs=-1
        )
        rf.fit(X_train, y_train)
        rf_acc = accuracy_score(y_test, rf.predict(X_test))
        print(f"    Random Forest准确率: {rf_acc:.4f}")
        models['rf'] = (rf, rf_acc)
        
        # 3. Gradient Boosting
        print("  [3/4] 训练Gradient Boosting...")
        gb = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        gb.fit(X_train, y_train)
        gb_acc = accuracy_score(y_test, gb.predict(X_test))
        print(f"    Gradient Boosting准确率: {gb_acc:.4f}")
        models['gb'] = (gb, gb_acc)
        
        # 4. Logistic Regression
        print("  [4/4] 训练Logistic Regression...")
        lr = LogisticRegression(
            C=1.0,
            max_iter=1000,
            random_state=42,
            class_weight='balanced'
        )
        lr.fit(X_train, y_train)
        lr_acc = accuracy_score(y_test, lr.predict(X_test))
        print(f"    Logistic Regression准确率: {lr_acc:.4f}")
        models['lr'] = (lr, lr_acc)
        
        return models
    
    def create_ensemble(self, models, X_train, X_test, y_train, y_test):
        """创建集成模型"""
        print("[4/6] 创建集成模型...")
        
        estimators = [
            ('svm', models['svm'][0]),
            ('rf', models['rf'][0]),
            ('gb', models['gb'][0]),
            ('lr', models['lr'][0])
        ]
        
        ensemble = VotingClassifier(
            estimators=estimators,
            voting='soft',  # 使用概率投票
            n_jobs=-1
        )
        
        ensemble.fit(X_train, y_train)
        
        ensemble_acc = accuracy_score(y_test, ensemble.predict(X_test))
        print(f"  集成模型准确率: {ensemble_acc:.4f}")
        
        return ensemble, ensemble_acc
    
    def evaluate_model(self, model, X_test, y_test):
        """详细评估模型"""
        print("[5/6] 模型评估...")
        
        y_pred = model.predict(X_test)
        
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='weighted')
        
        print(f"  准确率: {accuracy:.4f}")
        print(f"  F1分数: {f1:.4f}")
        print("\n  详细报告:")
        print(classification_report(y_test, y_pred, 
                                   target_names=['真实', '虚假'],
                                   digits=4))
        
        return {
            'accuracy': accuracy,
            'f1_score': f1
        }
    
    def save_model(self, model, vectorizer, metrics, data_size):
        """保存模型"""
        print("[6/6] 保存模型...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        model_data = {
            'model': model,
            'vectorizer': vectorizer,
            'metrics': metrics,
            'training_data_size': data_size,
            'timestamp': timestamp
        }
        
        # 保存最新模型
        model_file = self.model_dir / "advanced_model_latest.joblib"
        joblib.dump(model_data, model_file)
        print(f"  模型已保存: {model_file}")
        
        # 同时保存为系统使用的模型
        system_model_file = self.model_dir / "simple_ai_model.joblib"
        joblib.dump(model_data, system_model_file)
        print(f"  系统模型已更新: {system_model_file}")
        
        # 保存训练报告
        report = {
            'timestamp': timestamp,
            'training_data_size': data_size,
            'accuracy': metrics['accuracy'],
            'f1_score': metrics['f1_score'],
            'model_type': 'Ensemble (SVM + RF + GB + LR)'
        }
        
        report_file = self.model_dir / f"training_report_{timestamp}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"  训练报告已保存: {report_file}")
        
        return model_file
    
    def train(self):
        """完整训练流程"""
        print("="*60)
        print("🚀 开始训练高准确率AI模型")
        print("="*60)
        print()
        
        # 1. 加载和标准化数据
        texts, labels = self.load_and_standardize_data()
        
        # 2. 数据增强
        texts, labels = self.augment_data(texts, labels)
        
        # 3. 文本向量化
        print("[2/6] 文本向量化...")
        vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 3),
            min_df=2,
            max_df=0.8,
            sublinear_tf=True
        )
        X = vectorizer.fit_transform(texts)
        y = np.array(labels)
        
        print(f"  特征维度: {X.shape}")
        
        # 4. 分割数据集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"  训练集: {X_train.shape[0]} 条")
        print(f"  测试集: {X_test.shape[0]} 条")
        
        # 5. 训练多个模型
        models = self.train_models(X_train, X_test, y_train, y_test)
        
        # 6. 创建集成模型
        ensemble, ensemble_acc = self.create_ensemble(
            models, X_train, X_test, y_train, y_test
        )
        
        # 7. 评估最佳模型（使用集成模型）
        metrics = self.evaluate_model(ensemble, X_test, y_test)
        
        # 8. 保存模型
        model_file = self.save_model(ensemble, vectorizer, metrics, len(texts))
        
        print()
        print("="*60)
        print("✅ 训练完成！")
        print(f"🎯 最终准确率: {metrics['accuracy']:.2%}")
        print(f"📊 F1分数: {metrics['f1_score']:.4f}")
        print(f"💾 模型文件: {model_file}")
        print("="*60)
        
        return metrics['accuracy']

def main():
    trainer = AdvancedTrainer()
    accuracy = trainer.train()
    
    if accuracy >= 0.90:
        print("\n🎉 模型达到90%以上准确率！")
    elif accuracy >= 0.85:
        print("\n✅ 模型达到85%以上准确率！")
    else:
        print("\n⚠️  模型准确率需要继续提升，建议增加更多训练数据。")

if __name__ == "__main__":
    main()






