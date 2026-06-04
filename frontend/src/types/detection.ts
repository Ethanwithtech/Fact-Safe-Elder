// 检测结果类型定义
export interface DetectionResult {
  level: 'safe' | 'warning' | 'danger';
  score: number;
  confidence: number;
  message: string;
  reasons: string[];
  suggestions: string[];
  categories?: string[];
  keywords?: string[];
  timestamp: Date;
  detection_id?: string;
  detection_method?: string;
  // AI特有字段
  ai_models_used?: string[];
  explanation_report?: any;
  feature_importance?: any;
  // 视频检测特有字段
  transcript?: string;       // 语音转写文本
  ocr_text?: string;         // OCR 识别文本
  frames_used?: number;      // 抽帧数
  merged_text?: string;      // 合并后的全部文本（用于异步 GPT 核查）
  // 各模型独立分数
  bert_score?: number | null;
  tfidf_score?: number | null;
  // 突破点2: 老年人认知操控手法（多标签）
  manipulation_features?: string[];                 // 命中的特征 key
  manipulation_detail?: ManipulationFeature[];      // 含中文名+说明，供证据链展示
  manipulation_source?: 'cognitive_model' | 'weak_rule' | null;
  cognitive_risk?: number | null;
  // 突破点1: 跨模态错位
  asr_ocr_conflict?: CrossModalConflict;
  crossmodal?: {
    visual_risk?: number;
    audio_risk?: number;
    divergence?: number;
    joint_risk?: number;
    mismatch?: boolean;
    method?: string;
  };
  // 突破点3: 流式增量风险轨迹
  risk_trajectory?: RiskTrajectoryPoint[];
  // 突破点4: 证据链 / 案例关联
  evidence_chain?: EvidenceChain;
  related_cases?: RelatedCase[];
  // 各阶段耗时
  timing?: { ocr_seconds?: number; asr_seconds?: number; ai_seconds?: number };
  // GPT 事实核查
  gpt_fact_check?: GPTFactCheckResult;
}

// 老年人认知操控手法
export interface ManipulationFeature {
  key: string;
  name: string;
  desc: string;
}

// 跨模态错位冲突
export interface CrossModalConflict {
  conflict: boolean;
  reason: string;
  reason_en?: string;
  severity: 'high' | 'medium' | 'low';
  method?: string;          // rule | model | gpt_cot
  cot_explanation?: string; // GPT 多模态思维链解释
}

// 流式增量风险轨迹点（突破点3）
export interface RiskTrajectoryPoint {
  t: number;            // 视频时间(秒)或片段序号
  score: number;        // 该时刻累计风险分
  level: 'safe' | 'warning' | 'danger';
  note?: string;        // 触发说明
}

// 证据链（突破点4）
export interface EvidenceChain {
  claims?: FalseClaim[];                 // 声明提取与纠正
  techniques?: ManipulationFeature[];    // 诈骗手法标注
  cases?: RelatedCase[];                 // 关联真实案例
  summary?: string;
}

// 关联的真实诈骗案例
export interface RelatedCase {
  case_id: string;
  title: string;
  category: string;
  similarity: number;
  victims?: number;       // 已知受害人数
  avg_loss?: number;      // 平均损失(元)
  source?: string;
}

// GPT 事实核查结果
export interface GPTFactCheckResult {
  verdict: 'true' | 'false' | 'misleading' | 'unverifiable';
  confidence: number;
  risk_level: 'safe' | 'warning' | 'danger';
  summary: string;
  analysis: string;
  false_claims: FalseClaim[];
  fact_points: string[];
  risk_factors: string[];
  safety_advice: string[];
  related_scam_type: string;
  gpt_model?: string;
  gpt_latency?: number;
  fallback?: boolean;
  fallback_reason?: string;
}

// GPT 识别的虚假声明
export interface FalseClaim {
  original: string;    // 原文中的虚假声明
  correction: string;  // 正确的事实
  severity: 'high' | 'medium' | 'low';
}

// 音频捕获类型
export interface AudioCapture {
  isRecording: boolean;
  audioData: Blob | null;
  transcript: string;
}

// 视频信息类型
export interface VideoInfo {
  title: string;
  description: string;
  duration: number;
  platform: 'douyin' | 'wechat' | 'kuaishou' | 'other';
}

// 用户设置类型
export interface UserSettings {
  fontSize: 'normal' | 'large' | 'extra-large';
  highContrast: boolean;
  sensitivity: 'low' | 'medium' | 'high';
  enableSound: boolean;
  familyContact: string;
}

// API响应类型
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string;
  code: number;
}

// 检测历史记录类型
export interface DetectionHistory {
  id: string;
  timestamp: Date;
  content: string;
  result: DetectionResult;
  platform: string;
}

// 风险关键词类型
export interface RiskKeywords {
  financial: string[];
  medical: string[];
  general: string[];
}

// 语音转文字结果类型
export interface SpeechToTextResult {
  text: string;
  confidence: number;
  language: string;
  duration: number;
}

// 视频内容类型
export interface VideoContent {
  id: number;
  username: string;
  avatar: string;
  title: string;
  description: string;
  likes: string;
  comments: string;
  shares: string;
  music: string;
  verified: boolean;
  tags: string[];
  riskLevel: 'safe' | 'warning' | 'danger';
  content: string;
  videoUrl?: string;
  duration: number;
  thumbnail: string;
  danmus?: Array<{
    time: number;
    text: string;
    risk: boolean;
  }>;
}

