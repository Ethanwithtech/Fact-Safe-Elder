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
    const configuredURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    const browserHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
    const isRemotePreview = browserHost !== 'localhost' && browserHost !== '127.0.0.1';

    // 手机真机访问电脑 IP 时，不能继续请求 localhost:8000；应自动切到同一主机的 8000 端口。
    if (isRemotePreview && configuredURL.includes('localhost')) {
      this.baseURL = `${window.location.protocol}//${browserHost}:8000`;
    } else {
      this.baseURL = configuredURL;
    }

    console.log('[DetectionService] 初始化, API地址:', this.baseURL);
  }

  /**
   * 检测内容是否为虚假信息
   * 策略：始终调用后端 AI API 进行深度检测，本地规则作为补充
   */
  private getSensitivity(): string {
    try {
      const raw = localStorage.getItem('elderSafetySettings');
      if (!raw) return 'precision';
      const s = JSON.parse(raw);
      const v = (s.sensitivity || 'low').toLowerCase();
      if (v === 'low' || v === 'precision') return 'precision';
      if (v === 'high' || v === 'recall') return 'recall';
      return 'balanced';
    } catch {
      return 'precision';
    }
  }

  /** 分离 ASR（口播）与 OCR（标题+描述）做语义 + 跨模态检测 */
  async detectVideoContent(params: {
    asrText: string;
    ocrText: string;
    title: string;
  }): Promise<DetectionResult> {
    const cacheKey = this.generateCacheKey(`${params.title}|${params.ocrText}|${params.asrText}`);
    const cached = this.cache.get(cacheKey);
    if (cached && Date.now() - cached.time < this.cacheTimeout) {
      return cached.result;
    }

    try {
      const response = await axios.post(
        `${this.baseURL}/api/detect`,
        {
          text: params.asrText,
          audio_text: params.asrText,
          ocr_text: params.ocrText,
          title: params.title,
          sensitivity: this.getSensitivity(),
        },
        { timeout: 15000, headers: { 'Content-Type': 'application/json' } },
      );
      const apiData = response.data?.data || response.data;
      const result = this.mapApiResult(apiData);
      this.cache.set(cacheKey, { result, time: Date.now() });
      return result;
    } catch (apiError: any) {
      console.warn('[DetectionService] API 失败，降级本地:', apiError?.message);
      const merged = `${params.title} ${params.ocrText} ${params.asrText}`;
      const quickResult = this.quickLocalDetection(merged);
      quickResult.detection_method = 'local_rule_engine';
      this.cache.set(cacheKey, { result: quickResult, time: Date.now() });
      return quickResult;
    }
  }

  async detectContent(content: string): Promise<DetectionResult> {
    return this.detectVideoContent({
      asrText: content,
      ocrText: '',
      title: '',
    });
  }

  private mapApiResult(apiData: any): DetectionResult {
    return {
      level: apiData.level || 'safe',
      score: apiData.score ?? 0,
      confidence: apiData.confidence ?? 0.8,
      message: apiData.message || '',
      reasons: apiData.reasons || [],
      suggestions: apiData.suggestions || [],
      detection_method: apiData.detection_method || 'ai_multimodal',
      manipulation_detail: apiData.manipulation_detail,
      manipulation_features: apiData.manipulation_features,
      asr_ocr_conflict: apiData.asr_ocr_conflict,
      crossmodal: apiData.crossmodal,
      related_cases: apiData.related_cases,
      evidence_chain: apiData.evidence_chain,
      keywords: apiData.keywords,
      merged_text: apiData.merged_text,
      timestamp: new Date(),
    };
  }

  /**
   * 上传视频/音频文件进行 AI 快速检测（ASR 转写 + OCR + BERT + TF-IDF）
   * GPT 事实核查由前端异步调用 factCheck() 追加
   */
  async detectVideo(file: File, text?: string): Promise<DetectionResult> {
    try {
      const formData = new FormData();
      formData.append('video', file);
      if (text) formData.append('text', text);
      formData.append('sensitivity', this.getSensitivity());

      console.log('[DetectionService] 上传视频文件:', file.name, '大小:', (file.size / 1024 / 1024).toFixed(1), 'MB');

      const response = await axios.post(`${this.baseURL}/detect/video`, formData, {
        timeout: 120000, // 120秒超时（视频转写可能需要较长时间）
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      console.log('[DetectionService] 视频检测响应:', response.status, response.data?.success);

      const apiData = response.data?.data || response.data;

      const result: DetectionResult = {
        level: apiData.level || 'safe',
        score: apiData.score ?? 0,
        confidence: apiData.confidence ?? 0.8,
        message: apiData.message || '',
        reasons: apiData.reasons || [],
        suggestions: apiData.suggestions || [],
        detection_method: apiData.detection_method || 'ai_video_upload',
        timestamp: new Date(),
        detection_id: apiData.detection_id,
        transcript: apiData.transcript || '',
        ocr_text: apiData.ocr_text || '',
        frames_used: apiData.frames_used || 0,
        merged_text: apiData.merged_text || '',
        bert_score: apiData.bert_score ?? null,
        tfidf_score: apiData.tfidf_score ?? null,
        timing: apiData.timing || undefined,
      };

      console.log('[DetectionService] 视频检测结果:', result.level, '分数:', result.score,
        '转写:', result.transcript ? `${result.transcript.length}字` : '无',
        'OCR:', result.ocr_text ? `${result.ocr_text.length}字` : '无');

      return result;
    } catch (error: any) {
      console.error('[DetectionService] 视频检测失败:', error?.message || error);

      // 降级：把文件名作为文本发送到文本检测
      console.warn('[DetectionService] 降级为文本检测');
      const fallbackContent = `[视频文件] ${file.name} - 用户上传的视频文件`;
      const fallbackResult = await this.detectContent(fallbackContent);
      fallbackResult.detection_method = 'video_fallback_text';
      return fallbackResult;
    }
  }

  /**
   * SSE 流式视频检测 — 每个阶段完成后立即回调
   * @param onEvent 每收到一个 SSE 事件就调用
   * @returns Promise<void> 流结束时 resolve
   */
  /**
   * 从本地设置读取检测敏感度，映射到后端 precision/balanced/recall
   */
  getDetectSensitivity(): string {
    try {
      const raw = localStorage.getItem('elderSafetySettings');
      if (!raw) return 'precision';
      const s = JSON.parse(raw).sensitivity as string;
      if (s === 'high') return 'recall';
      if (s === 'medium') return 'balanced';
      return 'precision'; // low 默认：宁漏勿误
    } catch {
      return 'precision';
    }
  }

  /**
   * 用户反馈 — 标记误报/漏报，写入后端用于迭代模型
   */
  async submitFeedback(payload: {
    content_snippet: string;
    predicted_level: string;
    predicted_score: number;
    feedback_type: 'false_positive' | 'false_negative' | 'correct';
    comment?: string;
  }): Promise<boolean> {
    try {
      const resp = await axios.post(`${this.baseURL}/feedback`, payload, { timeout: 8000 });
      return resp.data?.success === true;
    } catch (e) {
      console.warn('[DetectionService] 反馈提交失败', e);
      return false;
    }
  }

  async detectVideoStream(
    file: File,
    text: string,
    onEvent: (event: string, data: any) => void,
    sensitivity?: string,
  ): Promise<void> {
    const formData = new FormData();
    formData.append('video', file);
    if (text) formData.append('text', text);
    formData.append('sensitivity', sensitivity || this.getDetectSensitivity());

    console.log('[DetectionService] 开始流式视频检测:', file.name);

    const response = await fetch(`${this.baseURL}/detect/video/stream`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok || !response.body) {
      throw new Error(`Stream failed: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent = '';
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ') && currentEvent) {
          try {
            const data = JSON.parse(line.slice(6));
            onEvent(currentEvent, data);
          } catch { /* ignore parse error */ }
          currentEvent = '';
        }
      }
    }
  }

  /**
   * 异步 GPT 事实核查（在 AI 检测结果展示后调用）
   * 返回 GPTFactCheckResult 或 null（失败时）
   */
  async factCheck(
    text: string,
    context?: string,
    detectionResult?: Partial<DetectionResult>,
  ): Promise<import('../types/detection').GPTFactCheckResult | null> {
    try {
      console.log('[DetectionService] 发起 GPT 事实核查, 文本长度:', text.length);

      const response = await axios.post(`${this.baseURL}/api/fact-check`, {
        text,
        context: context || undefined,
        detection_result: detectionResult ? {
          level: detectionResult.level,
          score: detectionResult.score,
          reasons: detectionResult.reasons,
        } : undefined,
      }, {
        timeout: 45000, // 45秒超时
        headers: { 'Content-Type': 'application/json' },
      });

      const apiData = response.data?.data || response.data;
      console.log('[DetectionService] GPT 核查完成:', apiData?.verdict, apiData?.risk_level);
      return apiData;
    } catch (error: any) {
      console.warn('[DetectionService] GPT 事实核查失败:', error?.message || error);
      return null;
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

    const eduSafe = ['不能代替', '不能替代', '不要轻信', '建议咨询', '正规医院', '遵医嘱', '科学科普'];
    if (eduSafe.some((p) => text.includes(p))) {
      return {
        level: 'safe',
        score: 0.08,
        confidence: 0.6,
        message: '科普提醒语境，未发现推销诈骗',
        reasons: [],
        suggestions: ['如有疑问可咨询家人'],
        detection_method: 'local_rule_engine',
        timestamp: new Date(),
      };
    }

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
      '偏方', '特效药',
      '三无产品', '假药', '违禁药', '激素'
    ];

    const scamCombo = /加微信|加微|包治|根治|特效|央视|订购/;
    const transferScam = /转账|汇款/.test(text) && !/不要.{0,12}转账|勿转账|别转账/.test(text);
    if (/保健品|营养品/.test(text) && (scamCombo.test(text) || transferScam)) {
      riskScore += 0.45;
      reasons.push('保健品推销并诱导私下联系');
    }

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

    // 平台内正常带货：小黄车/官旗等 + 无典型诈骗话术 → 压低误报
    const legitMarkers = [
      '官方旗舰店', '小黄车', '购物车', '直播间', '抖音商城',
      '包邮', '7天无理由', '现货', '正品', '官旗', '店铺客服',
    ];
    const scamMarkers = [
      '加微信', '加微', '私信买', '包治百病', '保证收益', '无风险',
      '月入万元', '稳赚', '祖传秘方', '央视推荐', '传销',
    ];
    const legitHits = legitMarkers.filter((m) => text.includes(m));
    const scamHits = scamMarkers.filter((m) => text.includes(m)).filter((m) => {
      if (m === '加微信' || m === '加微') {
        return !/不要.{0,10}(加微信|加微|私信)/.test(text);
      }
      return true;
    });
    if (legitHits.length >= 2 && scamHits.length === 0) {
      riskScore = Math.min(riskScore, 0.22);
      const filtered = reasons.filter(
        (r) => !r.includes('金融') && !r.includes('诈骗常用') && !r.includes('医疗'),
      );
      reasons.length = 0;
      reasons.push(
        ...(filtered.length ? filtered : ['平台内商品介绍，未发现典型诈骗话术']),
      );
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
