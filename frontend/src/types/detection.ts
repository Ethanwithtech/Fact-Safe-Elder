// 检测结果类型定义
export interface DetectionResult {
  level: 'safe' | 'warning' | 'danger';
  score: number;
  confidence: number;
  message: string;
  reasons: string[];
  suggestions: string[];
  timestamp: Date;
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

// 扩展的检测结果类型（包含AI特有字段）
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
  // AI特有字段
  ai_models_used?: string[];
  explanation_report?: any;
  feature_importance?: any;
}
