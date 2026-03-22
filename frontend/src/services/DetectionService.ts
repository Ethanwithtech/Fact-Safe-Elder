import axios from 'axios';
import { DetectionResult } from '../types/detection';

/**
 * 虚假信息检测服务
 */
export default class DetectionService {
  private baseURL: string;
  private cache: Map<string, { result: DetectionResult; time: number }> = new Map();
  private cacheTimeout = 30 * 1000; // 30秒缓存（缩短以支持实时检测体验）

  constructor() {
    this.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    console.log('[DetectionService] 初始化, API地址:', this.baseURL);
  }

  /**
   * 检测内容是否为虚假信息
   * 策略：始终调用后端 AI API 进行深度检测，本地规则作为补充
   */
  async detectContent(content: string): Promise<DetectionResult> {
    try {
      // 检查缓存（带过期时间）
      const cacheKey = this.generateCacheKey(content);
      const cached = this.cache.get(cacheKey);
      
      if (cached && (Date.now() - cached.time < this.cacheTimeout)) {
        console.log('[DetectionService] 使用缓存结果 (剩余', Math.round((this.cacheTimeout - (Date.now() - cached.time)) / 1000), '秒过期)');
        return cached.result;
      }

      // 本地快速检测（用于兜底和辅助判断，不再短路）
      const quickResult = this.quickLocalDetection(content);
      console.log('[DetectionService] 本地预检测:', quickResult.level, '分数:', quickResult.score.toFixed(2));

      // 始终调用后端 AI API 进行深度检测
      try {
        console.log('[DetectionService] 正在调用后端 AI API:', `${this.baseURL}/api/detect`);
        const response = await axios.post(`${this.baseURL}/api/detect`, {
          text: content,
          timestamp: new Date().toISOString()
        }, {
          timeout: 10000, // 10秒超时（BERT推理可能需要更长时间）
          headers: {
            'Content-Type': 'application/json'
          }
        });

        console.log('[DetectionService] 后端响应:', response.status, response.data?.success);

        // 后端返回 { success, message, data: { level, score, ... } }
        const apiData = response.data?.data || response.data;
        
        const result: DetectionResult = {
          level: apiData.level || quickResult.level,
          score: apiData.score ?? quickResult.score,
          confidence: apiData.confidence ?? 0.8,
          message: apiData.message || '',
          reasons: apiData.reasons || [],
          suggestions: apiData.suggestions || [],
          detection_method: apiData.detection_method || 'ai_multimodal',
          timestamp: new Date()
        };

        // 融合策略：如果 AI 判断为 safe 但本地关键词检测为 danger/warning，取更严格的
        if (result.level === 'safe' && quickResult.level !== 'safe') {
          result.level = quickResult.level;
          result.score = Math.max(result.score, quickResult.score);
          result.reasons = [...(quickResult.reasons || []), ...(result.reasons || [])];
          result.suggestions = [...new Set([...(quickResult.suggestions || []), ...(result.suggestions || [])])];
          result.message = quickResult.message;
          result.detection_method = 'hybrid';
        }

        console.log('[DetectionService] 最终结果:', result.level, '分数:', result.score, '方法:', result.detection_method);

        // 缓存结果
        this.cache.set(cacheKey, { result, time: Date.now() });
        
        // 清理过期缓存
        this.cleanExpiredCache();

        return result;
      } catch (apiError: any) {
        console.warn('[DetectionService] 后端 API 调用失败:', apiError?.message || apiError);
        console.warn('[DetectionService] 降级使用本地规则引擎检测');
        // API 失败时使用本地检测结果，标记检测方法
        quickResult.detection_method = 'local_rule_engine';
        this.cache.set(cacheKey, { result: quickResult, time: Date.now() });
        return quickResult;
      }

    } catch (error) {
      console.error('[DetectionService] 检测服务错误:', error);
      
      // 返回默认安全结果，避免系统崩溃
      return {
        level: 'safe',
        score: 0,
        confidence: 0.5,
        message: '检测服务暂时不可用',
        reasons: ['系统检测异常'],
        suggestions: ['建议谨慎对待此内容'],
        detection_method: 'error_fallback',
        timestamp: new Date()
      };
    }
  }

  /**
   * 本地快速检测 (基于关键词规则)
   */
  private quickLocalDetection(content: string): DetectionResult {
    const text = content.toLowerCase();
    let riskScore = 0;
    const reasons: string[] = [];
    const suggestions: string[] = [];

    // 金融诈骗关键词检测
    const financialRiskKeywords = [
      '保证收益', '无风险投资', '月入万元', '投资理财',
      '高收益', '稳赚不赔', '内幕消息', '股票推荐',
      '期货黄金', '虚拟货币', '挖矿', 'ico',
      '传销', '微商', '代理', '加盟费',
      '贷款', '借钱', '放款', '无抵押',
      '信用卡套现', '花呗', '借呗', '网贷'
    ];

    // 医疗虚假信息关键词
    const medicalRiskKeywords = [
      '包治百病', '神奇疗效', '祖传秘方', '一次根治',
      '医院不告诉你', '医生都在用', '癌症克星', '延年益寿',
      '排毒养颜', '减肥神器', '壮阳补肾', '丰胸美白',
      '偏方', '特效药', '保健品', '营养品',
      '三无产品', '假药', '违禁药', '激素'
    ];

    // 通用诈骗关键词
    const generalRiskKeywords = [
      '限时优惠', '马上行动', '不要错过', '机会难得',
      '扫码', '加微信', '联系电话', 'qq群',
      '转账', '汇款', '支付宝', '微信支付',
      '中奖', '免费领取', '0元购', '秒杀'
    ];

    // 检测金融风险
    const financialMatches = this.countKeywordMatches(text, financialRiskKeywords);
    if (financialMatches > 0) {
      riskScore += financialMatches * 0.3;
      reasons.push(`发现${financialMatches}个金融诈骗相关关键词`);
      suggestions.push('投资需谨慎，高收益往往伴随高风险');
    }

    // 检测医疗风险
    const medicalMatches = this.countKeywordMatches(text, medicalRiskKeywords);
    if (medicalMatches > 0) {
      riskScore += medicalMatches * 0.3;
      reasons.push(`发现${medicalMatches}个医疗虚假宣传关键词`);
      suggestions.push('有病请找正规医院，不要轻信偏方');
    }

    // 检测通用诈骗风险
    const generalMatches = this.countKeywordMatches(text, generalRiskKeywords);
    if (generalMatches > 0) {
      riskScore += generalMatches * 0.2;
      reasons.push(`发现${generalMatches}个诈骗常用话术`);
      suggestions.push('谨防诈骗，不要轻易转账或泄露个人信息');
    }

    // 检测紧急性和诱导性语言
    const urgencyKeywords = ['赶紧', '立即', '马上', '快速', '紧急', '限时'];
    const urgencyMatches = this.countKeywordMatches(text, urgencyKeywords);
    if (urgencyMatches > 2) {
      riskScore += 0.2;
      reasons.push('内容使用大量紧急性语言，可能是诱导手段');
      suggestions.push('冷静思考，不要被紧急性语言误导');
    }

    // 检测联系方式
    const hasContact = /微信|qq|电话|手机|联系/.test(text);
    if (hasContact && riskScore > 0) {
      riskScore += 0.1;
      reasons.push('含有联系方式且存在其他风险因素');
      suggestions.push('不要轻易添加陌生人联系方式');
    }

    // 计算最终风险等级
    riskScore = Math.min(riskScore, 1); // 限制在0-1之间
    
    let level: 'safe' | 'warning' | 'danger';
    let message: string;

    if (riskScore >= 0.7) {
      level = 'danger';
      message = '检测到高风险内容，建议立即停止观看';
    } else if (riskScore >= 0.4) {
      level = 'warning';
      message = '内容存在可疑信息，请谨慎对待';
    } else {
      level = 'safe';
      message = '暂未发现明显风险';
    }

    // 添加通用建议
    if (level !== 'safe') {
      suggestions.push('如有疑问，请咨询家人或专业人士');
      suggestions.push('遇到要求转账的情况请立即警惕');
    }

    return {
      level,
      score: riskScore,
      confidence: 0.8, // 本地检测置信度
      message,
      reasons,
      suggestions,
      timestamp: new Date()
    };
  }

  /**
   * 计算关键词匹配数量
   */
  private countKeywordMatches(text: string, keywords: string[]): number {
    let count = 0;
    keywords.forEach(keyword => {
      if (text.includes(keyword)) {
        count++;
      }
    });
    return count;
  }

  /**
   * 生成缓存键
   */
  private generateCacheKey(content: string): string {
    // 使用内容的哈希作为缓存键
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // 转换为32位整数
    }
    return hash.toString();
  }

  /**
   * 清理过期缓存
   */
  private cleanExpiredCache(): void {
    const now = Date.now();
    const keysToDelete: string[] = [];

    this.cache.forEach((entry, key) => {
      if (now - entry.time > this.cacheTimeout) {
        keysToDelete.push(key);
      }
    });

    keysToDelete.forEach(key => {
      this.cache.delete(key);
    });

    if (keysToDelete.length > 0) {
      console.log(`[DetectionService] 清理了 ${keysToDelete.length} 条过期缓存`);
    }
  }

  /**
   * 批量检测多个内容
   */
  async detectBatch(contents: string[]): Promise<DetectionResult[]> {
    const results: DetectionResult[] = [];
    
    // 并发检测，但限制并发数量
    const batchSize = 3;
    for (let i = 0; i < contents.length; i += batchSize) {
      const batch = contents.slice(i, i + batchSize);
      const batchPromises = batch.map(content => this.detectContent(content));
      const batchResults = await Promise.all(batchPromises);
      results.push(...batchResults);
    }

    return results;
  }

  /**
   * 获取检测统计信息
   */
  getStatistics(): {
    cacheSize: number;
    totalDetections: number;
    riskDetections: number;
  } {
    let riskCount = 0;
    this.cache.forEach(entry => {
      if (entry.result.level !== 'safe') {
        riskCount++;
      }
    });

    return {
      cacheSize: this.cache.size,
      totalDetections: this.cache.size,
      riskDetections: riskCount
    };
  }

  /**
   * 清除缓存
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * 设置API基础URL
   */
  setBaseURL(url: string): void {
    this.baseURL = url;
  }
}
