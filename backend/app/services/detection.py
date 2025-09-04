"""
虚假信息检测引擎服务
"""

import time
import uuid
import asyncio
import re
from typing import List, Dict, Optional, Any
from datetime import datetime
from loguru import logger

from app.models.detection import DetectionResult, RiskLevel, DetectionStats
from app.core.config import settings
from app.core.logging_config import LoggerMixin, log_detection_result


class DetectionEngine(LoggerMixin):
    """虚假信息检测引擎"""
    
    def __init__(self):
        self.logger = logger.bind(name="DetectionEngine")
        self.cache: Dict[str, DetectionResult] = {}
        self.statistics = DetectionStats()
        self.keywords_db = self._load_keywords()
        self.is_initialized = False
    
    async def initialize(self):
        """初始化检测引擎"""
        try:
            self.logger.info("🔄 正在初始化检测引擎...")
            
            # 加载关键词数据库
            self.keywords_db = self._load_keywords()
            self.logger.info(f"✅ 关键词数据库加载完成，包含{len(self.keywords_db)}个分类")
            
            # 初始化统计信息
            self.statistics = DetectionStats()
            
            # 测试检测功能
            test_result = await self.detect_text("测试文本")
            if test_result:
                self.logger.info("✅ 检测功能测试通过")
            
            self.is_initialized = True
            self.logger.info("🎉 检测引擎初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 检测引擎初始化失败: {e}", exc_info=True)
            raise
    
    def _load_keywords(self) -> Dict[str, List[str]]:
        """加载关键词数据库"""
        return {
            # 金融诈骗关键词
            "financial_fraud": [
                # 投资理财诈骗
                "保证收益", "无风险投资", "月入万元", "稳赚不赔", "高收益",
                "内幕消息", "股票推荐", "期货黄金", "虚拟货币", "数字货币",
                "挖矿", "ico", "区块链投资", "外汇交易", "原油投资",
                "贵金属投资", "邮币卡", "艺术品投资", "红酒投资",
                
                # 传销诈骗
                "传销", "微商", "代理", "加盟费", "入会费", "会员费",
                "拉人头", "层级分销", "金字塔", "多层次营销",
                
                # 借贷诈骗
                "无抵押贷款", "秒批", "黑户贷款", "征信修复", "代办信用卡",
                "花呗提现", "借呗套现", "网贷", "裸贷", "高利贷",
                "信用卡套现", "pos机", "刷单", "代还信用卡",
                
                # 诱导性词汇
                "限时优惠", "马上行动", "机会难得", "不要错过", "立即抢购",
                "仅限今天", "名额有限", "先到先得", "绝密消息"
            ],
            
            # 医疗虚假信息关键词
            "medical_fraud": [
                # 夸大疗效
                "包治百病", "神奇疗效", "祖传秘方", "一次根治", "永不复发",
                "药到病除", "立竿见影", "奇迹般康复", "绝对有效",
                "100%治愈", "三天见效", "一周康复",
                
                # 虚假权威
                "医院不告诉你", "医生都在用", "专家推荐", "权威认证",
                "国际领先", "诺贝尔奖", "美国进口", "德国技术",
                "中科院研发", "军工技术", "航天科技",
                
                # 疾病恐吓
                "癌症克星", "延年益寿", "排毒养颜", "减肥神器",
                "壮阳补肾", "丰胸美白", "抗衰老", "增高神器",
                "明目护眼", "护肝养胃", "补脑益智", "强身健体",
                
                # 产品宣传
                "保健品", "营养品", "特效药", "偏方", "土方",
                "民间验方", "宫廷秘方", "古方", "中药秘方",
                "三无产品", "假药", "违禁药", "激素药"
            ],
            
            # 通用诈骗关键词
            "general_fraud": [
                # 联系方式
                "加微信", "联系qq", "私信我", "留电话", "扫码进群",
                "微信号", "qq群", "电话咨询", "在线客服", "联系客服",
                
                # 支付转账
                "转账", "汇款", "支付宝", "微信支付", "银行卡", "打款",
                "预付款", "定金", "押金", "保证金", "手续费",
                
                # 中奖诈骗
                "中奖", "恭喜获奖", "幸运用户", "免费领取", "0元购",
                "秒杀", "特价", "清仓", "亏本甩卖", "跳楼价",
                
                # 紧急性词汇
                "赶紧", "立即", "马上", "快速", "紧急", "限时",
                "截止今晚", "最后一天", "错过后悔", "机不可失"
            ],
            
            # 情感诱导词汇
            "emotional_manipulation": [
                "可怜", "救救", "帮帮", "求助", "捐款", "爱心",
                "善心", "做好事", "积德", "功德", "报应", "因果",
                "老人", "孩子", "病人", "残疾", "困难", "贫困"
            ]
        }
    
    @log_detection_result()
    async def detect_text(
        self, 
        text: str, 
        user_id: Optional[str] = None, 
        platform: str = "unknown"
    ) -> DetectionResult:
        """
        检测文本内容是否为虚假信息
        
        Args:
            text: 待检测的文本
            user_id: 用户ID
            platform: 平台来源
            
        Returns:
            DetectionResult: 检测结果
        """
        start_time = time.time()
        detection_id = str(uuid.uuid4())
        
        try:
            # 检查缓存
            cache_key = self._generate_cache_key(text)
            if cache_key in self.cache:
                self.logger.debug(f"使用缓存结果: {cache_key[:8]}")
                cached_result = self.cache[cache_key]
                cached_result.detection_id = detection_id
                return cached_result
            
            # 文本预处理
            cleaned_text = self._preprocess_text(text)
            
            # 执行检测
            result = await self._perform_detection(cleaned_text, detection_id)
            
            # 缓存结果
            self.cache[cache_key] = result
            self._cleanup_cache()
            
            # 更新统计信息
            processing_time = time.time() - start_time
            self._update_statistics(result, processing_time)
            
            self.logger.info(
                f"检测完成 | ID: {detection_id[:8]} | "
                f"风险: {result.level} | 评分: {result.score:.3f} | "
                f"耗时: {processing_time:.3f}秒"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"文本检测失败: {str(e)}", exc_info=True)
            # 返回安全结果，避免服务中断
            return DetectionResult(
                level=RiskLevel.SAFE,
                score=0.0,
                confidence=0.1,
                message="检测服务异常，请手动验证内容安全性",
                reasons=["系统检测异常"],
                suggestions=["建议人工确认内容真实性"],
                detection_id=detection_id
            )
    
    async def detect_batch(
        self, 
        texts: List[str], 
        user_id: Optional[str] = None
    ) -> List[DetectionResult]:
        """
        批量检测文本内容
        
        Args:
            texts: 待检测的文本列表
            user_id: 用户ID
            
        Returns:
            List[DetectionResult]: 检测结果列表
        """
        try:
            # 并发检测，但限制并发数
            semaphore = asyncio.Semaphore(3)  # 最多3个并发
            
            async def detect_single(text: str) -> DetectionResult:
                async with semaphore:
                    return await self.detect_text(text, user_id)
            
            tasks = [detect_single(text) for text in texts]
            results = await asyncio.gather(*tasks)
            
            self.logger.info(f"批量检测完成，处理了{len(results)}个文本")
            return results
            
        except Exception as e:
            self.logger.error(f"批量检测失败: {str(e)}", exc_info=True)
            # 返回空结果列表
            return []
    
    async def _perform_detection(self, text: str, detection_id: str) -> DetectionResult:
        """执行具体的检测逻辑"""
        risk_score = 0.0
        confidence = 0.8
        reasons = []
        suggestions = []
        categories = []
        keywords_found = []
        
        # 1. 关键词匹配检测
        for category, keywords in self.keywords_db.items():
            matches = self._count_keyword_matches(text, keywords)
            if matches > 0:
                category_score = min(matches * 0.15, 0.6)  # 单个分类最高0.6分
                risk_score += category_score
                
                matched_keywords = [kw for kw in keywords if kw in text]
                keywords_found.extend(matched_keywords[:5])  # 最多记录5个关键词
                
                categories.append(category)
                reasons.append(f"发现{matches}个{category}相关关键词")
                
                # 添加分类特定的建议
                if category == "financial_fraud":
                    suggestions.append("投资需谨慎，高收益往往伴随高风险")
                    suggestions.append("不要轻易相信保证收益的投资项目")
                elif category == "medical_fraud":
                    suggestions.append("有病请找正规医院，不要轻信偏方")
                    suggestions.append("保健品不能替代药物治疗")
                elif category == "general_fraud":
                    suggestions.append("谨防诈骗，不要轻易转账或泄露个人信息")
        
        # 2. 语言模式检测
        pattern_score = self._detect_language_patterns(text)
        if pattern_score > 0.1:
            risk_score += pattern_score
            reasons.append("检测到可疑的语言模式")
        
        # 3. 联系方式检测
        contact_score = self._detect_contact_info(text)
        if contact_score > 0 and risk_score > 0:
            risk_score += contact_score
            reasons.append("含有联系方式且存在其他风险因素")
            suggestions.append("不要轻易添加陌生人联系方式")
        
        # 4. 紧急性检测
        urgency_score = self._detect_urgency(text)
        if urgency_score > 0.1:
            risk_score += urgency_score
            reasons.append("内容使用大量紧急性语言，可能是诱导手段")
            suggestions.append("冷静思考，不要被紧急性语言误导")
        
        # 5. 数字和比例检测（如收益率、价格等）
        number_score = self._detect_suspicious_numbers(text)
        if number_score > 0:
            risk_score += number_score
            reasons.append("检测到可疑的数字承诺")
        
        # 限制总分在0-1之间
        risk_score = min(risk_score, 1.0)
        
        # 确定风险等级
        if risk_score >= 0.7:
            level = RiskLevel.DANGER
            message = "检测到高风险内容，建议立即停止观看"
        elif risk_score >= 0.4:
            level = RiskLevel.WARNING
            message = "内容存在可疑信息，请谨慎对待"
        else:
            level = RiskLevel.SAFE
            message = "暂未发现明显风险"
        
        # 添加通用建议
        if level != RiskLevel.SAFE:
            suggestions.extend([
                "如有疑问，请咨询家人或专业人士",
                "遇到要求转账的情况请立即警惕"
            ])
        
        return DetectionResult(
            level=level,
            score=risk_score,
            confidence=confidence,
            message=message,
            reasons=reasons,
            suggestions=suggestions,
            categories=categories,
            keywords=keywords_found,
            detection_id=detection_id
        )
    
    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        # 转换为小写
        text = text.lower()
        
        # 移除多余的空格和换行符
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 移除特殊字符但保留中文、数字和基本标点
        text = re.sub(r'[^\u4e00-\u9fff\w\s.,!?;:()（）！？；：、。，]', '', text)
        
        return text
    
    def _count_keyword_matches(self, text: str, keywords: List[str]) -> int:
        """计算关键词匹配数量"""
        count = 0
        for keyword in keywords:
            if keyword in text:
                count += 1
        return count
    
    def _detect_language_patterns(self, text: str) -> float:
        """检测可疑的语言模式"""
        score = 0.0
        
        # 检测重复的感叹号或问号
        if re.search(r'[!！]{2,}|[?？]{2,}', text):
            score += 0.1
        
        # 检测过度使用的形容词
        excessive_adjectives = ['神奇', '绝对', '完美', '顶级', '极品', '史上最', '世界级']
        for adj in excessive_adjectives:
            if adj in text:
                score += 0.05
        
        # 检测夸张的数字表达
        if re.search(r'\d+倍|百分之\d+|\d+%', text):
            score += 0.05
        
        return min(score, 0.3)
    
    def _detect_contact_info(self, text: str) -> float:
        """检测联系方式"""
        score = 0.0
        
        contact_patterns = [
            r'微信|qq|电话|手机|联系',
            r'\d{11}',  # 手机号
            r'qq:\s*\d+',  # QQ号
            r'微信:\s*\w+'  # 微信号
        ]
        
        for pattern in contact_patterns:
            if re.search(pattern, text):
                score += 0.05
        
        return min(score, 0.2)
    
    def _detect_urgency(self, text: str) -> float:
        """检测紧急性词汇"""
        urgency_words = ['赶紧', '立即', '马上', '快速', '紧急', '限时', '截止', '最后']
        count = sum(1 for word in urgency_words if word in text)
        
        return min(count * 0.05, 0.2)
    
    def _detect_suspicious_numbers(self, text: str) -> float:
        """检测可疑数字"""
        score = 0.0
        
        # 高收益率
        if re.search(r'(\d+)%.*收益|收益.*(\d+)%', text):
            matches = re.findall(r'(\d+)%', text)
            for match in matches:
                if int(match) > 20:  # 超过20%的收益率
                    score += 0.1
        
        # 大额金钱
        money_patterns = [r'(\d+)万', r'(\d+)千', r'(\d+)元']
        for pattern in money_patterns:
            if re.search(pattern, text):
                score += 0.05
        
        return min(score, 0.3)
    
    def _generate_cache_key(self, text: str) -> str:
        """生成缓存键"""
        import hashlib
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _cleanup_cache(self):
        """清理缓存"""
        if len(self.cache) > 1000:  # 限制缓存大小
            # 删除最旧的50%缓存
            items_to_remove = len(self.cache) // 2
            keys_to_remove = list(self.cache.keys())[:items_to_remove]
            for key in keys_to_remove:
                del self.cache[key]
    
    def _update_statistics(self, result: DetectionResult, processing_time: float):
        """更新统计信息"""
        self.statistics.total_detections += 1
        
        if result.level == RiskLevel.SAFE:
            self.statistics.safe_count += 1
        elif result.level == RiskLevel.WARNING:
            self.statistics.warning_count += 1
        elif result.level == RiskLevel.DANGER:
            self.statistics.danger_count += 1
        
        # 更新平均处理时间
        total_time = self.statistics.avg_processing_time * (self.statistics.total_detections - 1)
        self.statistics.avg_processing_time = (total_time + processing_time) / self.statistics.total_detections
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        cache_hit_rate = 0.0
        if self.statistics.total_detections > 0:
            cache_hit_rate = len(self.cache) / self.statistics.total_detections
        
        return {
            "total_detections": self.statistics.total_detections,
            "safe_count": self.statistics.safe_count,
            "warning_count": self.statistics.warning_count,
            "danger_count": self.statistics.danger_count,
            "avg_processing_time": round(self.statistics.avg_processing_time, 3),
            "cache_size": len(self.cache),
            "cache_hit_rate": round(cache_hit_rate, 3),
            "keywords_categories": len(self.keywords_db),
            "is_initialized": self.is_initialized,
            "last_updated": datetime.now()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 执行简单的检测测试
            test_result = await self.detect_text("测试文本")
            
            return {
                "status": "healthy" if self.is_initialized else "not_initialized",
                "test_passed": test_result is not None,
                "cache_size": len(self.cache),
                "keywords_loaded": len(self.keywords_db) > 0,
                "timestamp": datetime.now()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now()
            }
    
    async def cleanup(self):
        """清理资源"""
        try:
            self.cache.clear()
            self.logger.info("检测引擎资源清理完成")
        except Exception as e:
            self.logger.error(f"检测引擎清理失败: {e}")
    
    # 以下是占位符方法，可以在后续版本中实现
    async def record_feedback(self, detection_id: str, feedback: str, rating: int):
        """记录用户反馈"""
        self.logger.info(f"收到反馈 | ID: {detection_id} | 评分: {rating}")
        # TODO: 实现反馈存储逻辑
    
    async def get_detection_history(self, user_id: str = None, limit: int = 20, offset: int = 0):
        """获取检测历史"""
        # TODO: 实现历史记录查询
        return []
    
    async def delete_detection_record(self, detection_id: str) -> bool:
        """删除检测记录"""
        # TODO: 实现记录删除
        return True
