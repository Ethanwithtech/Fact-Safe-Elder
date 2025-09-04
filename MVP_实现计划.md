# MVP实现计划和代码结构

## 1. 项目目录结构

```
Fact-Safe-Elder/
├── frontend/                 # React前端
│   ├── src/
│   │   ├── components/       # 组件
│   │   │   ├── VideoSimulator/
│   │   │   ├── DetectionFloater/
│   │   │   └── Settings/
│   │   ├── services/         # API服务
│   │   ├── utils/           # 工具函数
│   │   └── styles/          # 样式文件
│   ├── public/
│   └── package.json
├── backend/                  # Python后端
│   ├── app/
│   │   ├── api/             # API路由
│   │   ├── core/            # 核心配置
│   │   ├── models/          # 数据模型
│   │   ├── services/        # 业务服务
│   │   │   ├── detection.py # 检测服务
│   │   │   ├── audio.py     # 音频处理
│   │   │   └── ai_model.py  # AI模型
│   │   └── main.py
│   ├── data/                # 训练数据
│   ├── models/              # 模型文件
│   └── requirements.txt
├── docs/                    # 文档
├── docker-compose.yml       # 容器配置
└── README.md
```

## 2. MVP核心功能

### 2.1 Web模拟器功能
- ✅ 模拟短视频播放界面 (类似抖音)
- ✅ 实时音频捕获 (Web Audio API)
- ✅ 模拟视频文字/标题展示
- ✅ 基础浮窗显示

### 2.2 检测功能
- ✅ 基于关键词的规则检测 (金融、医疗)
- ✅ 风险等级评估 (绿/黄/红)
- ✅ 简单的置信度计算
- ❌ 复杂AI模型 (后续迭代)

### 2.3 用户交互
- ✅ 老人友好的浮窗设计
- ✅ 大字体、高对比度显示
- ✅ 简单的设置界面
- ❌ 家人提醒功能 (后续迭代)

## 3. 技术实现要点

### 3.1 前端关键技术
```javascript
// 音频捕获核心代码
const AudioCapture = () => {
  const [isListening, setIsListening] = useState(false);
  const [audioStream, setAudioStream] = useState(null);

  const startListening = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: true 
      });
      setAudioStream(stream);
      
      // 实时转换音频为文本
      const recognition = new window.webkitSpeechRecognition();
      recognition.continuous = true;
      recognition.onresult = (event) => {
        const transcript = event.results[event.results.length - 1][0].transcript;
        // 发送到后端检测
        detectContent(transcript);
      };
      recognition.start();
    } catch (error) {
      console.error('音频捕获失败:', error);
    }
  };
};
```

### 3.2 后端检测算法
```python
# 简单的规则引擎检测
class SimpleDetector:
    def __init__(self):
        # 金融诈骗关键词
        self.financial_keywords = [
            '高收益', '保证收益', '无风险', '月入万元',
            '投资理财', '股票内幕', '期货黄金', '虚拟币'
        ]
        
        # 医疗虚假信息关键词
        self.medical_keywords = [
            '包治百病', '神奇疗效', '祖传秘方', '一次根治',
            '医院不告诉你', '医生都在用', '癌症克星', '延年益寿'
        ]
    
    def detect_risk(self, text: str) -> DetectionResult:
        financial_score = self.calculate_financial_risk(text)
        medical_score = self.calculate_medical_risk(text)
        
        max_score = max(financial_score, medical_score)
        
        if max_score > 0.8:
            return DetectionResult(level='danger', score=max_score)
        elif max_score > 0.5:
            return DetectionResult(level='warning', score=max_score)
        else:
            return DetectionResult(level='safe', score=max_score)
```

## 4. MVP开发时间表

### Week 1: 基础框架搭建
- [ ] 创建React项目结构
- [ ] 搭建FastAPI后端
- [ ] 实现基础UI组件
- [ ] 配置开发环境

### Week 2: 核心功能开发
- [ ] 实现视频模拟器界面
- [ ] 集成Web Audio API
- [ ] 开发基础检测规则引擎
- [ ] 完成前后端API对接

### Week 3: 功能完善
- [ ] 优化浮窗交互体验
- [ ] 添加用户设置功能
- [ ] 实现检测结果展示
- [ ] 进行初步测试

### Week 4: 测试和优化
- [ ] 用户界面测试 (模拟老人操作)
- [ ] 检测准确性测试
- [ ] 性能优化
- [ ] 文档完善

## 5. 后续迭代规划

### Version 1.1 (Month 2)
- 集成真正的AI模型
- 添加语音转文字功能
- 实现家人提醒系统
- 增加检测历史记录

### Version 1.2 (Month 3)
- 移动端适配
- 更多平台支持 (微信、快手)
- 高级用户设置
- 数据分析面板

### Version 2.0 (Month 4-6)
- 原生移动应用
- 离线检测功能
- 个性化推荐
- 社区举报功能

## 6. 测试用例设计

### 6.1 金融诈骗测试用例
```json
{
  "test_cases": [
    {
      "input": "投资理财，月入3万，保证收益，无任何风险",
      "expected_output": {"level": "danger", "score": "> 0.8"}
    },
    {
      "input": "正规银行储蓄产品，年化收益3.5%",
      "expected_output": {"level": "safe", "score": "< 0.3"}
    }
  ]
}
```

### 6.2 医疗虚假信息测试用例
```json
{
  "test_cases": [
    {
      "input": "祖传秘方，包治百病，癌症三天见效",
      "expected_output": {"level": "danger", "score": "> 0.8"}
    },
    {
      "input": "正规医院专家建议，合理饮食有助健康",
      "expected_output": {"level": "safe", "score": "< 0.3"}
    }
  ]
}
```

## 7. 数据收集计划

### 7.1 训练数据来源
- **金融类**: 网络理财广告、投资诈骗案例、正规金融产品介绍
- **医疗类**: 保健品广告、医疗谣言、正规医疗科普内容
- **数据规模**: 每类1000-5000条样本

### 7.2 数据标注标准
```python
# 标注规范
AnnotationSchema = {
    "text": "原始文本内容",
    "label": {
        0: "安全内容",
        1: "可疑内容", 
        2: "高风险内容"
    },
    "domain": ["financial", "medical", "general"],
    "risk_factors": ["关键词", "语言模式", "情感倾向"],
    "confidence": "标注者信心度 0-1"
}
```

---

**MVP目标**: 2周内完成可演示的基础版本  
**技术负责人**: 开发团队  
**测试负责人**: 产品团队
