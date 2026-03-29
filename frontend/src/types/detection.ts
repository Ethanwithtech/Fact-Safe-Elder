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
  // GPT 事实核查
  gpt_fact_check?: GPTFactCheckResult;
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

