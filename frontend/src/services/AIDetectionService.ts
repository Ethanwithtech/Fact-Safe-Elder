/**
 * AI驱动的虚假信息检测服务
 * 集成ChatGLM等大模型进行多模态检测
 */

import axios from 'axios';
import { DetectionResult } from '../types/detection';

interface MultiModalData {
  text: string;
  username?: string;
  tags?: string[];
  verified?: boolean;
  engagement?: {
    likes: string;
    comments: string;
    shares: string;
  };
  images?: string[];
  audio?: Blob;
  videoFrames?: string[];
}

interface ModelPrediction {
  model: string;
  confidence: number;
  prediction: 'safe' | 'warning' | 'danger';
  explanation: string;
  features: {
    text_risk: number;
    behavior_risk: number;
    visual_risk: number;
    audio_risk: number;
  };
}

export default class AIDetectionService {
  private baseURL: string;
  private modelEndpoints: Map<string, string>;
  private cache: Map<string, DetectionResult>;
  private modelWeights: Map<string, number>;

  constructor() {
    this.baseURL = process.env.REACT_APP_AI_API_URL || 'http://localhost:8000';
    
    // 配置不同模型的端点
    this.modelEndpoints = new Map([
      ['chatglm', '/api/ai/chatglm/detect'],
      ['bert', '/api/ai/bert/detect'],
      ['llama', '/api/ai/llama/detect'],
      ['rule_based', '/api/detect'],
    ]);
    
    // 模型权重配置（用于集成学习）
    this.modelWeights = new Map([
      ['chatglm', 0.4],
      ['bert', 0.3],
      ['llama', 0.2],
      ['rule_based', 0.1],
    ]);
    
    this.cache = new Map();
  }

  /**
   * 多模态内容检测
   */
  async detectMultiModal(data: MultiModalData): Promise<DetectionResult> {
    try {
      // 检查缓存
      const cacheKey = this.generateCacheKey(data);
      if (this.cache.has(cacheKey)) {
        console.log('使用缓存的AI检测结果');
        return this.cache.get(cacheKey)!;
      }

      // 1. 文本特征提取
      const textFeatures = await this.extractTextFeatures(data.text);
      
      // 2. 行为特征提取
      const behaviorFeatures = this.extractBehaviorFeatures(data);
      
      // 3. 多模型预测（并行）
      const predictions = await this.multiModelPredict(data, textFeatures, behaviorFeatures);
      
      // 4. 模型集成（加权平均）
      const ensembleResult = this.ensemblePredictions(predictions);
      
      // 5. 生成解释性报告
      const explanation = this.generateExplanation(predictions, ensembleResult);
      
      // 6. 构建最终结果
      const result: DetectionResult = {
        level: ensembleResult.level,
        score: ensembleResult.score,
        confidence: ensembleResult.confidence,
        message: this.getMessageForLevel(ensembleResult.level),
        reasons: explanation.reasons,
        suggestions: this.getSuggestionsForLevel(ensembleResult.level, explanation),
        categories: this.identifyCategories(data, predictions),
        keywords: this.extractKeywords(data.text),
        timestamp: new Date(),
        detection_id: this.generateDetectionId(),
        // 新增AI特有字段
        ai_models_used: predictions.map(p => p.model),
        explanation_report: explanation.report,
        feature_importance: explanation.featureImportance,
      };

      // 缓存结果
      this.cache.set(cacheKey, result);
      
      // 异步发送到后端存储
      this.saveDetectionResult(result, data);
      
      return result;
      
    } catch (error) {
      console.error('AI检测失败:', error);
      
      // 降级到规则引擎
      return this.fallbackToRuleEngine(data);
    }
  }

  /**
   * 文本特征提取
   */
  private async extractTextFeatures(text: string): Promise<any> {
    try {
      const response = await axios.post(`${this.baseURL}/api/ai/features/text`, {
        text,
        models: ['bert', 'word2vec']
      });
      
      return response.data.features;
    } catch (error) {
      console.error('文本特征提取失败:', error);
      return this.extractBasicTextFeatures(text);
    }
  }

  /**
   * 基础文本特征提取（降级方案）
   */
  private extractBasicTextFeatures(text: string): any {
    return {
      length: text.length,
      exclamation_count: (text.match(/[!！]/g) || []).length,
      question_count: (text.match(/[?？]/g) || []).length,
      uppercase_ratio: (text.match(/[A-Z]/g) || []).length / text.length,
      emoji_count: (text.match(/[\u{1F600}-\u{1F64F}]/gu) || []).length,
      url_count: (text.match(/https?:\/\/[^\s]+/g) || []).length,
      phone_count: (text.match(/\d{11}/g) || []).length,
      money_mentions: (text.match(/[\d,]+元|万|千|百|十|块|毛|分|￥|\$/g) || []).length,
    };
  }

  /**
   * 行为特征提取
   */
  private extractBehaviorFeatures(data: MultiModalData): any {
    const features: any = {
      is_verified: data.verified || false,
      tag_count: data.tags?.length || 0,
      has_contact_info: /微信|qq|电话|手机|联系/.test(data.text),
    };

    // 解析互动数据
    if (data.engagement) {
      features.like_count = this.parseEngagement(data.engagement.likes);
      features.comment_count = this.parseEngagement(data.engagement.comments);
      features.share_count = this.parseEngagement(data.engagement.shares);
      
      // 计算互动比例
      const total = features.like_count + features.comment_count + features.share_count;
      if (total > 0) {
        features.like_ratio = features.like_count / total;
        features.comment_ratio = features.comment_count / total;
        features.share_ratio = features.share_count / total;
      }
    }

    return features;
  }

  /**
   * 解析互动数据（处理"万"、"k"等单位）
   */
  private parseEngagement(value: string): number {
    if (!value) return 0;
    
    const num = parseFloat(value.replace(/[^\d.]/g, ''));
    if (value.includes('万') || value.includes('w')) {
      return num * 10000;
    }
    if (value.includes('k') || value.includes('千')) {
      return num * 1000;
    }
    return num || 0;
  }

  /**
   * 多模型并行预测
   */
  private async multiModelPredict(
    data: MultiModalData, 
    textFeatures: any, 
    behaviorFeatures: any
  ): Promise<ModelPrediction[]> {
    const predictions: ModelPrediction[] = [];
    
    // 准备统一的输入数据
    const input = {
      text: data.text,
      text_features: textFeatures,
      behavior_features: behaviorFeatures,
      metadata: {
        username: data.username,
        tags: data.tags,
        verified: data.verified
      }
    };

    // 并行调用多个模型
    const modelPromises = Array.from(this.modelEndpoints.entries()).map(
      async ([model, endpoint]) => {
        try {
          const response = await axios.post(
            `${this.baseURL}${endpoint}`,
            input,
            { timeout: 5000 }
          );
          
          return {
            model,
            ...response.data
          } as ModelPrediction;
        } catch (error) {
          console.warn(`模型 ${model} 预测失败:`, error);
          return null;
        }
      }
    );

    const results = await Promise.allSettled(modelPromises);
    
    results.forEach(result => {
      if (result.status === 'fulfilled' && result.value) {
        predictions.push(result.value);
      }
    });

    // 如果没有模型返回结果，使用规则引擎
    if (predictions.length === 0) {
      predictions.push(await this.getRuleEngineResult(data));
    }

    return predictions;
  }

  /**
   * 模型集成（加权投票）
   */
  private ensemblePredictions(predictions: ModelPrediction[]): any {
    let totalScore = 0;
    let totalWeight = 0;
    let totalConfidence = 0;
    
    const levelVotes = { safe: 0, warning: 0, danger: 0 };
    
    predictions.forEach(pred => {
      const weight = this.modelWeights.get(pred.model) || 0.1;
      
      // 加权投票
      levelVotes[pred.prediction] += weight;
      
      // 加权平均分数
      const score = this.levelToScore(pred.prediction);
      totalScore += score * weight * pred.confidence;
      totalWeight += weight;
      totalConfidence += pred.confidence * weight;
    });
    
    // 确定最终等级
    let finalLevel: 'safe' | 'warning' | 'danger' = 'safe';
    let maxVote = 0;
    
    Object.entries(levelVotes).forEach(([level, vote]) => {
      if (vote > maxVote) {
        maxVote = vote;
        finalLevel = level as any;
      }
    });
    
    return {
      level: finalLevel,
      score: totalScore / totalWeight,
      confidence: totalConfidence / totalWeight,
      votes: levelVotes
    };
  }

  /**
   * 生成解释性报告
   */
  private generateExplanation(predictions: ModelPrediction[], ensemble: any): any {
    const reasons: string[] = [];
    const featureImportance: any = {};
    
    // 收集所有模型的解释
    predictions.forEach(pred => {
      if (pred.explanation) {
        reasons.push(`${pred.model}: ${pred.explanation}`);
      }
      
      // 合并特征重要性
      if (pred.features) {
        Object.entries(pred.features).forEach(([feature, importance]) => {
          featureImportance[feature] = (featureImportance[feature] || 0) + (importance as number);
        });
      }
    });
    
    // 标准化特征重要性
    const totalImportance = Object.values(featureImportance).reduce((a, b) => (a as number) + (b as number), 0) as number;
    Object.keys(featureImportance).forEach(key => {
      featureImportance[key] = featureImportance[key] / totalImportance;
    });
    
    // 生成详细报告
    const report = {
      summary: `基于${predictions.length}个AI模型的综合分析`,
      model_consensus: `${Math.round(ensemble.confidence * 100)}%的模型一致性`,
      risk_distribution: ensemble.votes,
      top_risk_factors: this.getTopRiskFactors(featureImportance),
      model_predictions: predictions.map(p => ({
        model: p.model,
        prediction: p.prediction,
        confidence: p.confidence
      }))
    };
    
    return {
      reasons,
      featureImportance,
      report
    };
  }

  /**
   * 获取主要风险因素
   */
  private getTopRiskFactors(featureImportance: any): string[] {
    return Object.entries(featureImportance)
      .sort((a, b) => (b[1] as number) - (a[1] as number))
      .slice(0, 3)
      .map(([feature, importance]) => {
        const percentage = Math.round((importance as number) * 100);
        return `${this.translateFeature(feature)} (${percentage}%)`;
      });
  }

  /**
   * 翻译特征名称为中文
   */
  private translateFeature(feature: string): string {
    const translations: any = {
      'text_risk': '文本风险',
      'behavior_risk': '行为模式风险',
      'visual_risk': '视觉内容风险',
      'audio_risk': '音频风险',
      'urgency_score': '紧急性语言',
      'money_mentions': '金钱相关',
      'has_contact_info': '联系方式'
    };
    
    return translations[feature] || feature;
  }

  /**
   * 等级转分数
   */
  private levelToScore(level: string): number {
    const scores: any = {
      'safe': 0.2,
      'warning': 0.6,
      'danger': 0.9
    };
    return scores[level] || 0.5;
  }

  /**
   * 规则引擎降级方案
   */
  private async getRuleEngineResult(data: MultiModalData): Promise<ModelPrediction> {
    try {
      const response = await axios.post(`${this.baseURL}/api/detect`, {
        text: data.text
      });
      
      return {
        model: 'rule_based',
        confidence: 0.7,
        prediction: response.data.data.level,
        explanation: response.data.data.message,
        features: {
          text_risk: response.data.data.score,
          behavior_risk: 0,
          visual_risk: 0,
          audio_risk: 0
        }
      };
    } catch (error) {
      // 最终降级：本地规则
      return this.getLocalRuleResult(data);
    }
  }

  /**
   * 本地规则检测（最终降级）
   */
  private getLocalRuleResult(data: MultiModalData): ModelPrediction {
    const dangerKeywords = ['保证收益', '月入万元', '包治百病', '祖传秘方'];
    const warningKeywords = ['投资', '理财', '保健品', '偏方'];
    
    let level: 'safe' | 'warning' | 'danger' = 'safe';
    let score = 0;
    
    dangerKeywords.forEach(keyword => {
      if (data.text.includes(keyword)) {
        level = 'danger';
        score = Math.max(score, 0.8);
      }
    });
    
    if (level === 'safe') {
      warningKeywords.forEach(keyword => {
        if (data.text.includes(keyword)) {
          level = 'warning';
          score = Math.max(score, 0.5);
        }
      });
    }
    
    return {
      model: 'local_rules',
      confidence: 0.6,
      prediction: level,
      explanation: '基于本地规则的快速检测',
      features: {
        text_risk: score,
        behavior_risk: 0,
        visual_risk: 0,
        audio_risk: 0
      }
    };
  }

  /**
   * 降级到规则引擎
   */
  private async fallbackToRuleEngine(data: MultiModalData): Promise<DetectionResult> {
    const ruleResult = await this.getRuleEngineResult(data);
    
    return {
      level: ruleResult.prediction,
      score: ruleResult.features.text_risk,
      confidence: ruleResult.confidence,
      message: ruleResult.explanation,
      reasons: ['AI服务暂时不可用，使用规则引擎检测'],
      suggestions: this.getDefaultSuggestions(),
      categories: [],
      keywords: [],
      timestamp: new Date(),
      detection_id: this.generateDetectionId()
    };
  }

  /**
   * 获取默认建议
   */
  private getDefaultSuggestions(): string[] {
    return [
      '谨慎对待涉及金钱的内容',
      '不要轻信保证收益的投资',
      '有病请到正规医院就诊',
      '如有疑问请咨询家人'
    ];
  }

  /**
   * 根据等级获取消息
   */
  private getMessageForLevel(level: string): string {
    const messages: any = {
      'safe': '内容安全，可以正常观看',
      'warning': '内容存在风险，请谨慎对待',
      'danger': '高风险内容，建议立即停止观看'
    };
    return messages[level] || '检测完成';
  }

  /**
   * 根据等级和解释生成建议
   */
  private getSuggestionsForLevel(level: string, explanation: any): string[] {
    const suggestions: string[] = [];
    
    if (level === 'danger') {
      suggestions.push('立即停止观看此内容');
      suggestions.push('不要点击任何链接或添加联系方式');
      suggestions.push('建议向家人或相关部门举报');
    } else if (level === 'warning') {
      suggestions.push('谨慎对待此内容');
      suggestions.push('建议查证信息来源');
      suggestions.push('如有疑问请咨询专业人士');
    }
    
    // 根据特征重要性添加针对性建议
    const topFactors = explanation.report?.top_risk_factors || [];
    topFactors.forEach((factor: string) => {
      if (factor.includes('金钱')) {
        suggestions.push('投资需谨慎，不要轻信高收益承诺');
      }
      if (factor.includes('联系方式')) {
        suggestions.push('不要轻易添加陌生人联系方式');
      }
      if (factor.includes('紧急')) {
        suggestions.push('冷静思考，不要被紧急性语言误导');
      }
    });
    
    return [...new Set(suggestions)]; // 去重
  }

  /**
   * 识别内容分类
   */
  private identifyCategories(data: MultiModalData, predictions: ModelPrediction[]): string[] {
    const categories = new Set<string>();
    
    // 基于文本内容识别
    if (/投资|理财|股票|基金|收益/.test(data.text)) {
      categories.add('金融');
    }
    if (/医|药|病|治|健康|养生/.test(data.text)) {
      categories.add('医疗');
    }
    if (/免费|中奖|领取|福利/.test(data.text)) {
      categories.add('营销');
    }
    
    // 基于标签识别
    data.tags?.forEach(tag => {
      if (tag.includes('投资') || tag.includes('理财')) {
        categories.add('金融');
      }
      if (tag.includes('健康') || tag.includes('医')) {
        categories.add('医疗');
      }
    });
    
    return Array.from(categories);
  }

  /**
   * 提取关键词
   */
  private extractKeywords(text: string): string[] {
    // 简单的关键词提取，实际应用中可以使用TF-IDF或TextRank
    const keywords = new Set<string>();
    
    const patterns = [
      /[投保贷借]资|理财|收益|回报/g,
      /[医药病治]疗|健康|养生|保健/g,
      /免费|优惠|折扣|秒杀/g,
      /微信|QQ|电话|联系/g
    ];
    
    patterns.forEach(pattern => {
      const matches = text.match(pattern);
      if (matches) {
        matches.forEach(match => keywords.add(match));
      }
    });
    
    return Array.from(keywords).slice(0, 10); // 最多返回10个关键词
  }

  /**
   * 生成缓存键
   */
  private generateCacheKey(data: MultiModalData): string {
    const text = data.text || '';
    const tags = (data.tags || []).join(',');
    return `${text.substring(0, 100)}_${tags}`.replace(/\s+/g, '_');
  }

  /**
   * 生成检测ID
   */
  private generateDetectionId(): string {
    return `det_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 异步保存检测结果
   */
  private async saveDetectionResult(result: DetectionResult, data: MultiModalData): Promise<void> {
    try {
      await axios.post(`${this.baseURL}/api/ai/results`, {
        result,
        original_data: data,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.warn('保存检测结果失败:', error);
    }
  }

  /**
   * 获取AI模型状态
   */
  async getModelStatus(): Promise<any> {
    try {
      const response = await axios.get(`${this.baseURL}/api/ai/status`);
      return response.data;
    } catch (error) {
      console.error('获取模型状态失败:', error);
      return {
        models: [],
        status: 'error',
        message: 'AI服务暂时不可用'
      };
    }
  }

  /**
   * 清除缓存
   */
  clearCache(): void {
    this.cache.clear();
    console.log('AI检测缓存已清除');
  }
}
