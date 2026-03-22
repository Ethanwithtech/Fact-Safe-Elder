"""
# 🛡️ AI虚假信息检测模型训练
## 用于Google Colab的训练脚本

将此文件上传到Google Colab，然后运行以训练模型。
或者创建新的Colab Notebook，将代码复制到单元格中运行。

参考文献:
1. Zhang et al. "AnswerFact: Fact Checking in Product Question Answering" (EMNLP 2020)
2. Ma et al. "Attention-based Rumor Detection with Tree-structured RvNN" (TIST 2020)

使用方法:
1. 打开 https://colab.research.google.com/
2. 创建新笔记本
3. 将下面的代码块复制到单元格中运行
4. 确保选择 GPU 运行时 (Runtime -> Change runtime type -> GPU)
"""

# ============================================================
# 第1部分: 环境设置 (Cell 1)
# ============================================================
"""
# 在Colab中运行此命令安装依赖
!nvidia-smi
!pip install transformers torch scikit-learn pandas tqdm accelerate -q
"""

import os
import json
import random
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

from transformers import (
    BertModel, 
    BertTokenizer,
    AdamW,
    get_linear_schedule_with_warmup
)

from sklearn.metrics import classification_report, confusion_matrix, f1_score
from tqdm import tqdm

# 设置随机种子
def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

set_seed(42)

# 设备配置
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'使用设备: {device}')

# ============================================================
# 第2部分: 训练数据 (Cell 2)
# ============================================================

# 金融诈骗类真实案例 - 来源于公安部反诈中心
FINANCIAL_FRAUD_SAMPLES = [
    {"text": "【内部消息】某央企即将重组，股价必涨300%，加我微信获取内幕", "label": "danger"},
    {"text": "数字货币投资平台，日收益5%，已有上万人获利，扫码入群", "label": "danger"},
    {"text": "【限时】期货配资10倍杠杆，专业老师带单，稳赚不赔！", "label": "danger"},
    {"text": "中老年人专属理财，年化收益18%，银行担保本金安全", "label": "danger"},
    {"text": "股票交流群：每日精选牛股，跟着大师操作月入十万不是梦", "label": "danger"},
    {"text": "外汇平台诚招代理，高额返佣，躺着也能赚钱！", "label": "danger"},
    {"text": "消费返利平台，购物全额返现，邀请好友再得奖励", "label": "danger"},
    {"text": "区块链挖矿项目，零投入高回报，每天躺赚几千元", "label": "danger"},
    {"text": "私募基金内部份额，最低投资1万，年化回报50%以上", "label": "danger"},
    {"text": "网贷平台急需资金，利息翻倍返还，限时抢购名额有限", "label": "danger"},
    {"text": "免费领取意外险，只需填写身份信息即可获得百万保障", "label": "danger"},
    {"text": "彩票预测软件，准确率98%，已帮助数万人中奖发财", "label": "danger"},
    {"text": "在家兼职刷单，每单佣金50-200元，日结工资不拖欠", "label": "danger"},
    {"text": "您好，我是XX银行工作人员，您的账户存在风险，请配合验证", "label": "danger"},
    {"text": "公安局通知：您涉嫌洗钱案，请立即将资金转入安全账户", "label": "danger"},
    {"text": "投资理财新机会，一夜暴富不是梦！内幕消息，必涨股票！", "label": "danger"},
    {"text": "保证收益20%，无风险投资，银行内部产品！", "label": "danger"},
    {"text": "跟着专家炒股，包赚不赔，月收益翻倍！", "label": "danger"},
    {"text": "无抵押贷款，秒批秒放，利息超低，不看征信！", "label": "danger"},
    {"text": "虚拟货币投资，日赚千元，错过后悔终生！", "label": "danger"},
]

# 医疗健康虚假信息 - 来源于国家卫健委辟谣
MEDICAL_MISINFO_SAMPLES = [
    {"text": "祖传秘方专治糖尿病，一个月停药，三个月根治不复发", "label": "danger"},
    {"text": "癌症克星！纯天然草药配方，已治愈数千名癌症患者", "label": "danger"},
    {"text": "高血压不用吃药，每天坚持这个动作，血压自然降下来", "label": "danger"},
    {"text": "失眠多年？用这个土方法，一觉睡到天亮，永不失眠", "label": "danger"},
    {"text": "白发变黑发，不用染发剂，用它洗头三次见效", "label": "danger"},
    {"text": "近视眼福音！中药眼药水，用一个月恢复正常视力", "label": "danger"},
    {"text": "关节炎特效贴，贴一次管一年，彻底告别疼痛", "label": "danger"},
    {"text": "深海鱼油软胶囊，清除血管垃圾，预防心脑血管疾病", "label": "danger"},
    {"text": "酵素排毒减肥，一周瘦十斤，清肠道排宿便", "label": "danger"},
    {"text": "震惊！这种常见蔬菜竟然致癌，很多人还不知道天天吃", "label": "danger"},
    {"text": "喝白开水等于慢性自杀！快看看你每天喝的水安全吗", "label": "danger"},
    {"text": "碱性体质不得癌，每天喝柠檬水调节酸碱平衡", "label": "danger"},
    {"text": "喝板蓝根预防新冠，专家证实有效率达90%", "label": "danger"},
    {"text": "包治百病的神药，一个疗程见效，永不复发", "label": "danger"},
    {"text": "神奇保健品，一次根治，永不复发，药到病除！", "label": "danger"},
]

# 可疑内容
SUSPICIOUS_SAMPLES = [
    {"text": "限时特价！原价999现在只要99，仅剩最后10件", "label": "warning"},
    {"text": "朋友圈代购正品保证，比专柜便宜一半", "label": "warning"},
    {"text": "老顾客专属优惠，充值1000送500，机会难得", "label": "warning"},
    {"text": "直播间福利来袭，关注即送价值298元大礼包", "label": "warning"},
    {"text": "投资小课堂：教你如何选择适合自己的理财产品", "label": "warning"},
    {"text": "保健品特卖，买二送一，中老年人养生必备", "label": "warning"},
    {"text": "免费体验课程，学完即可月入过万，名额有限先到先得", "label": "warning"},
    {"text": "会员专享折扣，今日下单立减200元", "label": "warning"},
    {"text": "新用户注册送100元优惠券，购物满200可用", "label": "warning"},
    {"text": "分享赚钱，邀请好友下载APP各得50元红包", "label": "warning"},
]

# 正常内容
NORMAL_SAMPLES = [
    {"text": "今日天气：多云转晴，气温15-25度，空气质量良好", "label": "safe"},
    {"text": "本市新建三所学校将于今年秋季开学招生", "label": "safe"},
    {"text": "地铁3号线因设备检修，今日末班车提前至22:30", "label": "safe"},
    {"text": "市图书馆周末举办亲子阅读活动，免费参加名额有限", "label": "safe"},
    {"text": "医生建议：成年人每天应保证7-8小时睡眠时间", "label": "safe"},
    {"text": "合理膳食，荤素搭配，每天摄入足够的蔬菜水果", "label": "safe"},
    {"text": "定期体检很重要，建议每年至少做一次全面检查", "label": "safe"},
    {"text": "感冒发烧请及时就医，不要自行服用抗生素", "label": "safe"},
    {"text": "银行提醒：投资有风险，入市需谨慎，请根据自身情况合理配置", "label": "safe"},
    {"text": "国债发行公告：本期国债年利率3.2%，发行期限为三年", "label": "safe"},
    {"text": "正规贷款需要审核征信，请勿相信无需任何资质的贷款广告", "label": "safe"},
    {"text": "今天分享一道家常红烧肉的做法，简单易学又美味", "label": "safe"},
    {"text": "周末好天气，适合带家人去公园散步放松心情", "label": "safe"},
    {"text": "春节临近，提醒大家注意出行安全，遵守交通规则", "label": "safe"},
    {"text": "世界卫生组织建议：成年人每周应进行150分钟中等强度运动", "label": "safe"},
]

# 合并所有数据
all_samples = FINANCIAL_FRAUD_SAMPLES + MEDICAL_MISINFO_SAMPLES + SUSPICIOUS_SAMPLES + NORMAL_SAMPLES

# 数据增强
def augment_samples(samples):
    augmented = []
    keyword_variants = {
        "保证收益": ["稳赚不赔", "百分百赚", "绝对盈利"],
        "月入万元": ["日赚千元", "轻松月入过万", "躺着也能赚"],
        "内幕消息": ["内部信息", "独家资讯", "第一手消息"],
        "限时": ["仅剩", "最后机会", "错过不再"],
        "包治百病": ["药到病除", "一次根治", "永不复发"],
        "祖传秘方": ["独家配方", "民间偏方", "家传秘方"],
    }
    
    for sample in samples:
        text = sample['text']
        label = sample['label']
        for original, variants in keyword_variants.items():
            if original in text:
                for variant in variants:
                    new_text = text.replace(original, variant)
                    if new_text != text:
                        augmented.append({"text": new_text, "label": label})
    return augmented

augmented_samples = augment_samples(all_samples)
all_samples = all_samples + augmented_samples

print(f"总样本数: {len(all_samples)}")
print(f"Danger: {len([s for s in all_samples if s['label'] == 'danger'])}")
print(f"Warning: {len([s for s in all_samples if s['label'] == 'warning'])}")
print(f"Safe: {len([s for s in all_samples if s['label'] == 'safe'])}")

# 创建数据集划分
random.shuffle(all_samples)
train_size = int(len(all_samples) * 0.7)
val_size = int(len(all_samples) * 0.15)

train_data = all_samples[:train_size]
val_data = all_samples[train_size:train_size + val_size]
test_data = all_samples[train_size + val_size:]

print(f"训练集: {len(train_data)}, 验证集: {len(val_data)}, 测试集: {len(test_data)}")

# ============================================================
# 第3部分: 模型定义 (Cell 3)
# ============================================================

class MultiHeadSelfAttention(nn.Module):
    """多头自注意力机制 - 参考Ma et al. (2020)"""
    def __init__(self, hidden_size, num_heads=8, dropout=0.1):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        
        self.query = nn.Linear(hidden_size, hidden_size)
        self.key = nn.Linear(hidden_size, hidden_size)
        self.value = nn.Linear(hidden_size, hidden_size)
        self.output = nn.Linear(hidden_size, hidden_size)
        
        self.dropout = nn.Dropout(dropout)
        self.scale = self.head_dim ** -0.5
    
    def forward(self, x, mask=None):
        batch_size, seq_len, _ = x.size()
        
        Q = self.query(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        K = self.key(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        V = self.value(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        
        scores = torch.matmul(Q, K.transpose(-2, -1)) * self.scale
        
        if mask is not None:
            mask = mask.unsqueeze(1).unsqueeze(2)
            scores = scores.masked_fill(mask == 0, float('-inf'))
        
        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)
        
        context = torch.matmul(attn_weights, V)
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, self.hidden_size)
        
        return self.output(context), attn_weights


class EvidenceRankingModule(nn.Module):
    """证据排序模块 - 参考Zhang et al. (2020)"""
    def __init__(self, hidden_size):
        super().__init__()
        self.scorer = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size // 2, 1)
        )
    
    def forward(self, hidden_states, attention_mask):
        scores = self.scorer(hidden_states).squeeze(-1)
        scores = scores.masked_fill(attention_mask == 0, float('-inf'))
        weights = F.softmax(scores, dim=-1)
        weighted = torch.bmm(weights.unsqueeze(1), hidden_states).squeeze(1)
        return weighted, weights


class BERTFraudDetector(nn.Module):
    """BERT + Attention 虚假信息检测模型"""
    
    def __init__(self, num_classes=3, dropout=0.1):
        super().__init__()
        
        self.bert = BertModel.from_pretrained('hfl/chinese-bert-wwm-ext')
        self.hidden_size = self.bert.config.hidden_size
        
        self.self_attention = MultiHeadSelfAttention(self.hidden_size, num_heads=8)
        self.evidence_module = EvidenceRankingModule(self.hidden_size)
        self.layer_norm = nn.LayerNorm(self.hidden_size)
        
        self.classifier = nn.Sequential(
            nn.Linear(self.hidden_size * 2, self.hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(self.hidden_size, self.hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(self.hidden_size // 2, num_classes)
        )
    
    def forward(self, input_ids, attention_mask):
        bert_output = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        hidden_states = bert_output.last_hidden_state
        
        attn_output, _ = self.self_attention(hidden_states, attention_mask)
        attn_output = self.layer_norm(hidden_states + attn_output)
        
        cls_output = attn_output[:, 0, :]
        evidence_output, _ = self.evidence_module(attn_output, attention_mask)
        
        combined = torch.cat([cls_output, evidence_output], dim=-1)
        logits = self.classifier(combined)
        
        return logits


# 数据集类
class FraudDataset(Dataset):
    def __init__(self, data, tokenizer, max_length=128):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.label_map = {'safe': 0, 'warning': 1, 'danger': 2}
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        encoding = self.tokenizer(
            item['text'],
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(0),
            'attention_mask': encoding['attention_mask'].squeeze(0),
            'label': torch.tensor(self.label_map[item['label']], dtype=torch.long)
        }


# ============================================================
# 第4部分: 训练 (Cell 4)
# ============================================================

# 超参数
BATCH_SIZE = 16
LEARNING_RATE = 2e-5
NUM_EPOCHS = 5
MAX_LENGTH = 128
WARMUP_STEPS = 100

# 加载tokenizer和创建数据集
print("加载tokenizer...")
tokenizer = BertTokenizer.from_pretrained('hfl/chinese-bert-wwm-ext')

train_dataset = FraudDataset(train_data, tokenizer, MAX_LENGTH)
val_dataset = FraudDataset(val_data, tokenizer, MAX_LENGTH)
test_dataset = FraudDataset(test_data, tokenizer, MAX_LENGTH)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE)

# 初始化模型
print("初始化模型...")
model = BERTFraudDetector(num_classes=3).to(device)
print(f"模型参数量: {sum(p.numel() for p in model.parameters()):,}")

# 优化器和调度器
optimizer = AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
total_steps = len(train_loader) * NUM_EPOCHS
scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=WARMUP_STEPS, num_training_steps=total_steps)
criterion = nn.CrossEntropyLoss()


def train_epoch(model, dataloader, optimizer, scheduler, criterion, device):
    model.train()
    total_loss = 0
    for batch in tqdm(dataloader, desc="Training"):
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['label'].to(device)
        
        optimizer.zero_grad()
        logits = model(input_ids, attention_mask)
        loss = criterion(logits, labels)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()
        total_loss += loss.item()
    
    return total_loss / len(dataloader)


def evaluate(model, dataloader, criterion, device):
    model.eval()
    total_loss = 0
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for batch in tqdm(dataloader, desc="Evaluating"):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['label'].to(device)
            
            logits = model(input_ids, attention_mask)
            loss = criterion(logits, labels)
            total_loss += loss.item()
            
            preds = torch.argmax(logits, dim=-1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    
    accuracy = np.mean(np.array(all_preds) == np.array(all_labels))
    f1 = f1_score(all_labels, all_preds, average='weighted')
    
    return {'loss': total_loss / len(dataloader), 'accuracy': accuracy, 'f1': f1, 
            'predictions': all_preds, 'labels': all_labels}


# 训练循环
print("\n" + "="*60 + "\n开始训练\n" + "="*60)

best_f1 = 0
history = {'train_loss': [], 'val_loss': [], 'val_accuracy': [], 'val_f1': []}

for epoch in range(NUM_EPOCHS):
    print(f"\nEpoch {epoch+1}/{NUM_EPOCHS}")
    
    train_loss = train_epoch(model, train_loader, optimizer, scheduler, criterion, device)
    print(f"训练损失: {train_loss:.4f}")
    
    val_results = evaluate(model, val_loader, criterion, device)
    print(f"验证损失: {val_results['loss']:.4f}, 准确率: {val_results['accuracy']:.4f}, F1: {val_results['f1']:.4f}")
    
    history['train_loss'].append(train_loss)
    history['val_loss'].append(val_results['loss'])
    history['val_accuracy'].append(val_results['accuracy'])
    history['val_f1'].append(val_results['f1'])
    
    if val_results['f1'] > best_f1:
        best_f1 = val_results['f1']
        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'val_f1': best_f1,
            'history': history
        }, 'best_fraud_detector.pth')
        print(f"✅ 保存最佳模型 (F1: {best_f1:.4f})")

print(f"\n训练完成！最佳F1: {best_f1:.4f}")

# ============================================================
# 第5部分: 测试和导出 (Cell 5)
# ============================================================

# 加载最佳模型并测试
checkpoint = torch.load('best_fraud_detector.pth')
model.load_state_dict(checkpoint['model_state_dict'])

test_results = evaluate(model, test_loader, criterion, device)
print(f"\n测试集结果 - 准确率: {test_results['accuracy']:.4f}, F1: {test_results['f1']:.4f}")
print("\n分类报告:")
print(classification_report(test_results['labels'], test_results['predictions'], 
                            target_names=['safe', 'warning', 'danger']))

# 导出最终模型
torch.save({
    'model_state_dict': model.state_dict(),
    'model_config': {'num_classes': 3, 'pretrained_model': 'hfl/chinese-bert-wwm-ext'},
    'label_map': {0: 'safe', 1: 'warning', 2: 'danger'},
    'training_info': {
        'epochs': NUM_EPOCHS,
        'best_f1': best_f1,
        'test_accuracy': test_results['accuracy'],
        'test_f1': test_results['f1']
    },
    'history': history,
    'created_at': datetime.now().isoformat()
}, 'fraud_detector_final.pth')

print("\n模型已保存为 fraud_detector_final.pth")
print("请下载此文件并部署到后端服务")

# 如果在Colab中运行，可以下载模型
# from google.colab import files
# files.download('fraud_detector_final.pth')









