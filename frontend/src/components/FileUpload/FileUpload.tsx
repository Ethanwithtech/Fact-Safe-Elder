import React, { useState, useRef, useEffect } from 'react';
import DetectionService from '../../services/DetectionService';
import { DetectionResult, GPTFactCheckResult } from '../../types/detection';
import { Language, t } from '../../i18n';
import './FileUpload.css';

interface FileUploadProps {
  onDetectionResult?: (result: DetectionResult) => void;
  lang: Language;
}

/* 轻量 toast */
function showToast(text: string, type: 'success' | 'warning' | 'error' = 'success') {
  const existing = document.getElementById('fu-toast');
  if (existing) existing.remove();
  const el = document.createElement('div');
  el.id = 'fu-toast';
  el.className = `fu-toast fu-toast-${type}`;
  el.textContent = text;
  document.body.appendChild(el);
  requestAnimationFrame(() => el.classList.add('show'));
  setTimeout(() => { el.classList.remove('show'); setTimeout(() => el.remove(), 300); }, 2500);
}

const FileUpload: React.FC<FileUploadProps> = ({ onDetectionResult, lang }) => {
  const [file, setFile] = useState<File | null>(null);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMsg, setProgressMsg] = useState('');
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [dragOver, setDragOver] = useState(false);
  // GPT 异步核查
  const [gptResult, setGptResult] = useState<GPTFactCheckResult | null>(null);
  const [gptLoading, setGptLoading] = useState(false);
  // 实时分析日志
  const [analysisLog, setAnalysisLog] = useState<string[]>([]);
  const [scanProgress, setScanProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const logBoxRef = useRef<HTMLDivElement>(null);
  const detectionService = useRef(new DetectionService());

  // 清理 blob URL 防止内存泄漏
  useEffect(() => {
    return () => { if (fileUrl) URL.revokeObjectURL(fileUrl); };
  }, [fileUrl]);

  // 日志框自动滚动
  useEffect(() => {
    if (logBoxRef.current) logBoxRef.current.scrollTop = logBoxRef.current.scrollHeight;
  }, [analysisLog]);

  const acceptedTypes = [
    'video/mp4', 'video/avi', 'video/quicktime', 'video/x-msvideo', 'video/webm',
    'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp3',
  ];

  const handleFileSelect = (selectedFile: File) => {
    if (selectedFile.size > 100 * 1024 * 1024) {
      showToast(lang === 'zh' ? '文件大小不能超过100MB' : 'File size must be under 100MB', 'error');
      return;
    }
    if (fileUrl) URL.revokeObjectURL(fileUrl);
    const url = URL.createObjectURL(selectedFile);
    setFile(selectedFile);
    setFileUrl(url);
    setResult(null);
    setGptResult(null);
    setProgress(0);
    showToast(t(lang, 'uploadSuccess'), 'success');
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFileSelect(f);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFileSelect(f);
  };

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = () => setDragOver(false);

  const handleAnalyze = async () => {
    if (!file) {
      showToast(t(lang, 'uploadNoFile'), 'warning');
      return;
    }

    setIsAnalyzing(true);
    setProgress(0);
    setResult(null);
    setGptResult(null);
    setAnalysisLog([]);
    setScanProgress(0);

    const zh = lang === 'zh';

    // 实时分析阶段（模拟后端处理过程）
    const phases = zh
      ? [
          { text: '📡 连接AI检测引擎...', pct: 5 },
          { text: '📤 上传视频文件到服务器...', pct: 15 },
          { text: '🎞️ OpenCV 抽取关键帧...', pct: 25 },
          { text: '📝 EasyOCR 字幕/文字识别...', pct: 40 },
          { text: '🎙️ Whisper ASR 语音转写...', pct: 55 },
          { text: '🤖 MacBERT 中文语义编码...', pct: 70 },
          { text: '📊 TF-IDF 统计模型分析...', pct: 80 },
          { text: '🔍 关键词/诈骗模式扫描...', pct: 88 },
          { text: '🧠 三层融合风险评估...', pct: 92 },
        ]
      : [
          { text: '📡 Connecting AI engine...', pct: 5 },
          { text: '📤 Uploading video to server...', pct: 15 },
          { text: '🎞️ OpenCV frame extraction...', pct: 25 },
          { text: '📝 EasyOCR text recognition...', pct: 40 },
          { text: '🎙️ Whisper ASR transcription...', pct: 55 },
          { text: '🤖 MacBERT semantic encoding...', pct: 70 },
          { text: '📊 TF-IDF statistical analysis...', pct: 80 },
          { text: '🔍 Keyword / scam pattern scan...', pct: 88 },
          { text: '🧠 3-layer fusion risk assessment...', pct: 92 },
        ];

    // 逐步推出分析日志（与实际 API 调用并行）
    const showPhases = async () => {
      for (let i = 0; i < phases.length; i++) {
        setAnalysisLog(prev => [...prev, phases[i].text]);
        setScanProgress(phases[i].pct);
        setProgressMsg(phases[i].text);
        setProgress(phases[i].pct);
        await new Promise(r => setTimeout(r, 350 + Math.random() * 300));
      }
    };

    try {
      // 并行：显示分析阶段 + 实际 API 调用
      const [detResult] = await Promise.all([
        detectionService.current.detectVideo(file),
        showPhases(),
      ]);

      // 分析完成 — 逐条展示各模块的实际结果
      setScanProgress(100);
      setProgress(100);

      // OCR 识别结果
      if (detResult.ocr_text) {
        setAnalysisLog(prev => [...prev,
          `✅ ${zh ? 'OCR 识别' : 'OCR recognized'}: "${detResult.ocr_text!.slice(0, 100)}${detResult.ocr_text!.length > 100 ? '...' : ''}"`,
        ]);
      } else {
        setAnalysisLog(prev => [...prev, zh ? '⬚ OCR: 未识别到画面文字' : '⬚ OCR: No text found']);
      }

      // ASR 语音转写结果
      if (detResult.transcript) {
        setAnalysisLog(prev => [...prev,
          `✅ ${zh ? 'ASR 转写' : 'ASR transcript'}: "${detResult.transcript!.slice(0, 100)}${detResult.transcript!.length > 100 ? '...' : ''}"`,
        ]);
      } else {
        setAnalysisLog(prev => [...prev, zh ? '⬚ ASR: 未识别到语音' : '⬚ ASR: No speech found']);
      }

      // BERT 模型结果
      if (detResult.bert_score != null) {
        const bPct = Math.round(detResult.bert_score * 100);
        const bLabel = detResult.bert_score > 0.5
          ? (zh ? '⚠️ 风险' : '⚠️ Risky')
          : (zh ? '✅ 安全' : '✅ Safe');
        setAnalysisLog(prev => [...prev,
          `🤖 BERT ${zh ? '判定' : 'verdict'}: ${bLabel} (${zh ? '风险度' : 'risk'} ${bPct}%)`,
        ]);
      }

      // TF-IDF 模型结果
      if (detResult.tfidf_score != null) {
        const tPct = Math.round(detResult.tfidf_score * 100);
        const tLabel = detResult.tfidf_score > 0.5
          ? (zh ? '⚠️ 风险' : '⚠️ Risky')
          : (zh ? '✅ 安全' : '✅ Safe');
        setAnalysisLog(prev => [...prev,
          `📊 TF-IDF ${zh ? '判定' : 'verdict'}: ${tLabel} (${zh ? '置信度' : 'conf'} ${tPct}%)`,
        ]);
      }

      // 融合结论
      const levelLabel = detResult.level === 'danger'
        ? (zh ? '🚨 高风险' : '🚨 HIGH RISK')
        : detResult.level === 'warning'
          ? (zh ? '⚠️ 可疑' : '⚠️ SUSPICIOUS')
          : (zh ? '✅ 安全' : '✅ SAFE');
      const finalScore = Math.round((detResult.score ?? 0) * 100);
      setAnalysisLog(prev => [...prev,
        `━━ ${zh ? '融合结论' : 'Final verdict'}: ${levelLabel} (${finalScore}/100) ━━`,
      ]);

      setResult(detResult);
      setIsAnalyzing(false);
      onDetectionResult?.(detResult);

      // 第二阶段：异步 GPT 事实核查（后台静默进行）
      const textForGpt = detResult.merged_text || detResult.transcript || detResult.ocr_text || '';
      if (textForGpt.trim().length > 10) {
        setGptLoading(true);
        setAnalysisLog(prev => [...prev, zh ? '🔍 GPT 深度事实核查中...' : '🔍 GPT deep fact-checking...']);
        detectionService.current
          .factCheck(textForGpt, `视频: ${file.name}`, detResult)
          .then((gpt) => {
            if (gpt && !gpt.fallback) {
              setGptResult(gpt);

              // ★ 融合 GPT 结果更新最终判定
              const gptLevel = gpt.risk_level || 'safe';
              const gptVerdict = gpt.verdict; // true/false/misleading/unverifiable
              // GPT 判定为 false 或 danger 时，提升最终等级
              let finalLevel = detResult.level;
              let finalScore = detResult.score ?? 0;

              if (gptVerdict === 'false' || gptLevel === 'danger') {
                finalLevel = 'danger';
                finalScore = Math.max(finalScore, 0.75);
              } else if (gptVerdict === 'misleading' || gptLevel === 'warning') {
                if (finalLevel === 'safe') finalLevel = 'warning';
                finalScore = Math.max(finalScore, 0.5);
              }

              // 生成综合结论 message
              const verdictMap: Record<string, [string, string]> = {
                'false': [zh ? '❌ 虚假信息' : '❌ False Information', 'danger'],
                'misleading': [zh ? '⚠️ 误导性信息' : '⚠️ Misleading', 'warning'],
                'true': [zh ? '✅ 信息属实' : '✅ Verified True', 'safe'],
                'unverifiable': [zh ? '❓ 暂无法核实' : '❓ Unverifiable', 'warning'],
              };
              const [verdictText] = verdictMap[gptVerdict] || [gptVerdict, 'warning'];

              const bertLabel = detResult.bert_score != null
                ? `BERT: ${Math.round(detResult.bert_score * 100)}%${zh ? '风险' : ' risk'}`
                : '';
              const tfidfLabel = detResult.tfidf_score != null
                ? `TF-IDF: ${Math.round(detResult.tfidf_score * 100)}%${zh ? '风险' : ' risk'}`
                : '';
              const modelsLine = [bertLabel, tfidfLabel].filter(Boolean).join(' | ');

              const finalMessage = [
                `${zh ? 'GPT 事实核查' : 'GPT Fact Check'}: ${verdictText}`,
                gpt.summary || '',
                modelsLine ? `${zh ? 'AI 模型' : 'AI Models'}: ${modelsLine}` : '',
                gpt.related_scam_type && gpt.related_scam_type !== '无'
                  ? `${zh ? '诈骗类型' : 'Scam type'}: ${gpt.related_scam_type}` : '',
              ].filter(Boolean).join('\n');

              // 更新 result 为融合后的最终结果
              setResult(prev => prev ? {
                ...prev,
                level: finalLevel as 'safe' | 'warning' | 'danger',
                score: finalScore,
                message: finalMessage,
              } : prev);

              setAnalysisLog(prev => [
                ...prev,
                `✅ GPT: ${verdictText} (${gpt.gpt_latency || '?'}s)`,
                `━━ ${zh ? '最终综合判定' : 'Final combined verdict'}: ${
                  finalLevel === 'danger' ? (zh ? '🚨 高风险' : '🚨 HIGH RISK')
                  : finalLevel === 'warning' ? (zh ? '⚠️ 可疑' : '⚠️ SUSPICIOUS')
                  : (zh ? '✅ 安全' : '✅ SAFE')
                } (${Math.round(finalScore * 100)}/100) ━━`,
              ]);
            }
          })
          .catch(() => { /* 静默失败 */ })
          .finally(() => setGptLoading(false));
      }
    } catch (error) {
      setIsAnalyzing(false);
      setAnalysisLog(prev => [...prev, zh ? '❌ 检测异常' : '❌ Detection error']);
      showToast(t(lang, 'uploadError'), 'error');
    }
  };

  const handleRemove = () => {
    if (fileUrl) URL.revokeObjectURL(fileUrl);
    setFile(null);
    setFileUrl(null);
    setResult(null);
    setGptResult(null);
    setGptLoading(false);
    setProgress(0);
    setAnalysisLog([]);
    setScanProgress(0);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const getMethodLabel = (method?: string) => {
    if (!method) return lang === 'zh' ? '未知' : 'Unknown';
    const map: Record<string, [string, string]> = {
      ai_video_gpt_factcheck: ['🧠 AI全链路 (BERT+TF-IDF+GPT核查)', '🧠 Full AI Pipeline (BERT+TF-IDF+GPT)'],
      ai_video_upload: ['🤖 AI视频分析 (BERT+TF-IDF)', '🤖 AI Video (BERT+TF-IDF)'],
      ai_multimodal: ['🤖 AI多模态融合 (BERT + TF-IDF + Rules)', '🤖 AI Multimodal (BERT + TF-IDF + Rules)'],
      ai_bert: ['🧠 BERT 深度语义分析', '🧠 BERT Deep Semantic'],
      ai_tfidf: ['📊 TF-IDF 统计模型', '📊 TF-IDF Statistical'],
      hybrid: ['🤖+📋 AI + 规则混合', '🤖+📋 AI + Rule Hybrid'],
      rule_engine_video_upload: ['📋 规则引擎 (视频)', '📋 Rule Engine (Video)'],
      local_rule_engine: ['📋 本地规则引擎', '📋 Local Rule Engine'],
      video_fallback_text: ['⚠️ 降级文本检测', '⚠️ Fallback Text Detection'],
      error_fallback: ['⚠️ 降级检测', '⚠️ Fallback'],
    };
    const pair = map[method];
    return pair ? pair[lang === 'zh' ? 0 : 1] : method;
  };

  const getVerdictLabel = (verdict?: string) => {
    const map: Record<string, [string, string]> = {
      true: ['✅ 信息属实', '✅ Verified True'],
      false: ['❌ 虚假信息', '❌ False'],
      misleading: ['⚠️ 误导性信息', '⚠️ Misleading'],
      unverifiable: ['❓ 暂无法核实', '❓ Unverifiable'],
    };
    const pair = verdict ? map[verdict] : undefined;
    return pair ? pair[lang === 'zh' ? 0 : 1] : (lang === 'zh' ? '未核查' : 'Not checked');
  };

  const scorePct = Math.round((result?.score ?? 0) * 100);
  const pct = Math.round(progress);
  const isVideo = file?.type.startsWith('video/');

  return (
    <div className="file-upload-container">
      <div className="upload-header">
        <h3>{t(lang, 'uploadTitle')}</h3>
        <p>{t(lang, 'uploadDesc')}</p>
      </div>

      {!file ? (
        <div
          className={`upload-dragger ${dragOver ? 'drag-over' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <span className="upload-icon">📤</span>
          <p className="upload-text">{t(lang, 'uploadDragger')}</p>
          <p className="upload-hint">{t(lang, 'uploadHint')}</p>
          <input
            ref={fileInputRef}
            type="file"
            accept={acceptedTypes.join(',')}
            onChange={handleInputChange}
            style={{ display: 'none' }}
          />
        </div>
      ) : (
        <div className="file-preview">
          {/* === 媒体播放器 === */}
          {fileUrl && (
            <div className="media-player-wrap">
              {isVideo ? (
                <video className="media-player" src={fileUrl} controls playsInline preload="metadata" />
              ) : (
                <div className="audio-player-wrap">
                  <div className="audio-visual">🎵</div>
                  <audio className="media-player-audio" src={fileUrl} controls preload="metadata" />
                </div>
              )}
            </div>
          )}

          {/* === 文件信息 === */}
          <div className="file-info-card">
            <div className="file-icon-wrap">
              <span className={`file-type-icon ${isVideo ? 'video' : 'audio'}`}>
                {isVideo ? '🎬' : '🎵'}
              </span>
            </div>
            <div className="file-details">
              <div className="file-name">{file.name}</div>
              <div className="file-meta">
                {formatFileSize(file.size)} · {file.type.split('/')[1]?.toUpperCase() || 'FILE'}
              </div>
            </div>
            <button className="remove-btn" onClick={handleRemove} title="Remove">🗑️</button>
          </div>

          {/* === 实时 AI 分析面板 === */}
          {(isAnalyzing || analysisLog.length > 0) && (
            <div className="fu-live-panel">
              <div className="fu-live-header">
                <span className={`fu-live-dot ${isAnalyzing ? 'scanning' : 'done'}`} />
                <span>{isAnalyzing
                  ? (lang === 'zh' ? '🛡️ AI 实时检测中' : '🛡️ AI Real-time Detection')
                  : (lang === 'zh' ? '✅ 检测完成' : '✅ Detection Complete')
                }</span>
                {isAnalyzing && <span className="fu-live-badge">{lang === 'zh' ? '分析中' : 'Analyzing'}</span>}
              </div>

              {/* 进度条 */}
              <div className="fu-scan-progress">
                <div className="fu-scan-bar">
                  <div className="fu-scan-fill" style={{ width: `${scanProgress}%` }} />
                </div>
                <span className="fu-scan-pct">{scanProgress}%</span>
              </div>

              {/* 分析日志 */}
              <div className="fu-live-log" ref={logBoxRef}>
                {analysisLog.map((log, i) => (
                  <div key={i} className={`fu-log-line ${i === analysisLog.length - 1 && isAnalyzing ? 'active' : 'done'}`}>
                    <span className="fu-log-check">{(i < analysisLog.length - 1 || !isAnalyzing) ? '✓' : '⏳'}</span>
                    <span>{log}</span>
                  </div>
                ))}
                {isAnalyzing && <div className="fu-log-cursor">▊</div>}
              </div>

              {/* === 识别出的内容（ASR + OCR） === */}
              {result && (result.transcript || result.ocr_text) && (
                <div className="fu-recognized-content">
                  <div className="fu-recognized-title">📋 {lang === 'zh' ? '识别出的内容' : 'Recognized Content'}</div>
                  {result.transcript && (
                    <div className="fu-recognized-block">
                      <span className="fu-recognized-label">🎙️ ASR</span>
                      <span className="fu-recognized-text">{result.transcript}</span>
                    </div>
                  )}
                  {result.ocr_text && (
                    <div className="fu-recognized-block">
                      <span className="fu-recognized-label">📝 OCR</span>
                      <span className="fu-recognized-text">{result.ocr_text}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {!isAnalyzing && !result && (
            <button className="analyze-btn" onClick={handleAnalyze}>
              🔍 {t(lang, 'uploadAnalyze')}
            </button>
          )}

          {/* ============ AI 检测结果（第一阶段，秒出） ============ */}
          {result && (
            <div className={`upload-result ${result.level}`}>
              {/* 头部 */}
              <div className="upload-result-header">
                <span className="upload-result-icon">
                  {result.level === 'danger' && '🚨'}
                  {result.level === 'warning' && '⚠️'}
                  {result.level === 'safe' && '✅'}
                </span>
                <span className="upload-result-title">
                  {result.level === 'danger' && (lang === 'zh' ? '高风险内容' : 'High Risk Content')}
                  {result.level === 'warning' && (lang === 'zh' ? '可疑内容' : 'Suspicious Content')}
                  {result.level === 'safe' && (lang === 'zh' ? '内容安全' : 'Content Safe')}
                </span>
                <span className="upload-result-score">{scorePct}/100</span>
              </div>

              {/* 分数条 */}
              <div className="result-score-bar-wrap">
                <div className="result-score-bar">
                  <div className={`result-score-fill ${result.level}`} style={{ width: `${scorePct}%` }} />
                </div>
                <div className="result-score-labels">
                  <span>{lang === 'zh' ? '安全' : 'Safe'}</span>
                  <span>{lang === 'zh' ? '注意' : 'Caution'}</span>
                  <span>{lang === 'zh' ? '危险' : 'Danger'}</span>
                </div>
              </div>

              {/* 检测方法 + 置信度 + 帧数 + 时间 */}
              <div className="result-meta-row">
                <span className="result-meta-tag method">
                  {getMethodLabel(gptResult ? 'ai_video_gpt_factcheck' : result.detection_method)}
                </span>
                {result.confidence != null && (
                  <span className="result-meta-tag confidence">
                    {lang === 'zh' ? '置信度' : 'Conf'}: {Math.round(result.confidence * 100)}%
                  </span>
                )}
                {result.frames_used != null && result.frames_used > 0 && (
                  <span className="result-meta-tag time">
                    🎞️ {result.frames_used} {lang === 'zh' ? '帧' : 'frames'}
                  </span>
                )}
                <span className="result-meta-tag time">
                  ⏱️ {result.timestamp ? new Date(result.timestamp).toLocaleTimeString(lang === 'zh' ? 'zh-CN' : 'en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--'}
                </span>
              </div>

              {/* === BERT + TF-IDF 各模型独立结果 === */}
              {(result.bert_score != null || result.tfidf_score != null) && (
                <div className="fu-model-scores">
                  {result.bert_score != null && (
                    <div className={`fu-model-card ${result.bert_score > 0.5 ? 'risky' : 'safe'}`}>
                      <div className="fu-model-name">🤖 BERT</div>
                      <div className="fu-model-verdict">
                        {result.bert_score > 0.5
                          ? (lang === 'zh' ? '⚠️ 风险' : '⚠️ Risky')
                          : (lang === 'zh' ? '✅ 安全' : '✅ Safe')}
                      </div>
                      <div className="fu-model-bar">
                        <div className={`fu-model-fill ${result.bert_score > 0.5 ? 'risky' : 'safe'}`}
                          style={{ width: `${Math.round(result.bert_score * 100)}%` }} />
                      </div>
                      <div className="fu-model-pct">{Math.round(result.bert_score * 100)}%</div>
                    </div>
                  )}
                  {result.tfidf_score != null && (
                    <div className={`fu-model-card ${result.tfidf_score > 0.5 ? 'risky' : 'safe'}`}>
                      <div className="fu-model-name">📊 TF-IDF</div>
                      <div className="fu-model-verdict">
                        {result.tfidf_score > 0.5
                          ? (lang === 'zh' ? '⚠️ 风险' : '⚠️ Risky')
                          : (lang === 'zh' ? '✅ 安全' : '✅ Safe')}
                      </div>
                      <div className="fu-model-bar">
                        <div className={`fu-model-fill ${result.tfidf_score > 0.5 ? 'risky' : 'safe'}`}
                          style={{ width: `${Math.round(result.tfidf_score * 100)}%` }} />
                      </div>
                      <div className="fu-model-pct">{Math.round(result.tfidf_score * 100)}%</div>
                    </div>
                  )}
                </div>
              )}

              {/* === 识别出的内容（在结果卡片内） === */}
              {(result.transcript || result.ocr_text || result.merged_text) && (
                <div className="fu-result-recognized">
                  <div className="result-section-title">📋 {lang === 'zh' ? '识别出的视频内容' : 'Recognized Video Content'}</div>
                  {result.ocr_text && (
                    <div className="fu-recog-row">
                      <span className="fu-recog-tag ocr">📝 OCR</span>
                      <span className="fu-recog-text">{result.ocr_text}</span>
                    </div>
                  )}
                  {result.transcript && (
                    <div className="fu-recog-row">
                      <span className="fu-recog-tag asr">🎙️ ASR</span>
                      <span className="fu-recog-text">{result.transcript}</span>
                    </div>
                  )}
                  {!result.transcript && !result.ocr_text && result.merged_text && (
                    <div className="fu-recog-row">
                      <span className="fu-recog-tag">📄</span>
                      <span className="fu-recog-text">{result.merged_text.slice(0, 200)}</span>
                    </div>
                  )}
                  {!result.transcript && !result.ocr_text && !result.merged_text && (
                    <div className="fu-recog-empty">{lang === 'zh' ? '未识别到视频中的文字或语音内容' : 'No text or speech detected in this video'}</div>
                  )}
                </div>
              )}

              {/* AI 结论 */}
              {result.message && (
                <div className="result-conclusion">
                  <div className="result-section-title">🧠 {lang === 'zh' ? 'AI 综合分析' : 'AI Analysis'}</div>
                  <div className="result-conclusion-text">{result.message}</div>
                </div>
              )}

              {/* 风险因素 */}
              {(result.reasons || []).length > 0 && (
                <div className="result-reasons-section">
                  <div className="result-section-title">⚡ {lang === 'zh' ? '风险因素' : 'Risk Factors'}</div>
                  <div className="upload-result-reasons">
                    {(result.reasons || []).map((r, i) => (
                      <div key={i} className="reason-item-row">
                        <span className="reason-bullet">•</span>
                        <span>{r}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 建议 */}
              {(result.suggestions || []).length > 0 && (
                <div className="result-suggestions-section">
                  <div className="result-section-title">💡 {lang === 'zh' ? '安全建议' : 'Safety Suggestions'}</div>
                  <div className="upload-result-suggestions">
                    {(result.suggestions || []).map((s, i) => (
                      <div key={i} className="suggestion-item-row">
                        <span className="suggestion-icon">💡</span>
                        <span>{s}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ============ GPT 事实核查（第二阶段，异步追加） ============ */}
              {gptLoading && (
                <div className="result-gpt-section gpt-loading">
                  <div className="result-section-title">🔍 {lang === 'zh' ? 'GPT 事实核查中...' : 'GPT Fact-Checking...'}</div>
                  <div className="gpt-loading-bar">
                    <div className="gpt-loading-fill" />
                  </div>
                  <div className="gpt-loading-hint">
                    {lang === 'zh' ? 'AI 正在深度分析内容真实性，请稍候...' : 'AI is analyzing content authenticity...'}
                  </div>
                </div>
              )}

              {gptResult && (
                <div className="result-gpt-section gpt-loaded">
                  <div className="result-section-title">🔍 {lang === 'zh' ? 'GPT 事实核查' : 'GPT Fact Check'}</div>
                  <div className="gpt-verdict-row">
                    <span className={`gpt-verdict-badge ${gptResult.verdict}`}>
                      {getVerdictLabel(gptResult.verdict)}
                    </span>
                    {gptResult.related_scam_type && gptResult.related_scam_type !== '无' && (
                      <span className="gpt-scam-type">🏷️ {gptResult.related_scam_type}</span>
                    )}
                    {gptResult.gpt_latency != null && (
                      <span className="gpt-latency">⏱ {gptResult.gpt_latency}s</span>
                    )}
                  </div>
                  {gptResult.summary && (
                    <div className="gpt-summary-text">{gptResult.summary}</div>
                  )}
                  {gptResult.analysis && (
                    <div className="gpt-analysis-text">{gptResult.analysis}</div>
                  )}

                  {/* === 虚假信息 vs 正确信息 对比 === */}
                  {gptResult.false_claims && gptResult.false_claims.length > 0 && (
                    <div className="gpt-false-claims-section">
                      <div className="result-section-title">🚨 {lang === 'zh' ? '虚假信息核查' : 'False Claims Identified'}</div>
                      {gptResult.false_claims.map((claim, i) => (
                        <div key={i} className={`false-claim-card severity-${claim.severity || 'medium'}`}>
                          <div className="false-claim-original">
                            <span className="claim-label claim-false">❌ {lang === 'zh' ? '虚假' : 'False'}</span>
                            <span className="claim-text">{claim.original}</span>
                          </div>
                          <div className="false-claim-arrow">↓</div>
                          <div className="false-claim-correction">
                            <span className="claim-label claim-correct">✅ {lang === 'zh' ? '正确' : 'Correct'}</span>
                            <span className="claim-text">{claim.correction}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {gptResult.fact_points && gptResult.fact_points.length > 0 && (
                    <div className="gpt-fact-points">
                      {gptResult.fact_points.map((p, i) => (
                        <div key={i} className="gpt-fact-point-row">
                          <span className="fact-check-icon">📋</span>
                          <span>{p}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {gptResult.safety_advice && gptResult.safety_advice.length > 0 && (
                    <div className="gpt-advice-section">
                      {gptResult.safety_advice.map((a, i) => (
                        <div key={i} className="gpt-advice-row">
                          <span className="gpt-advice-icon">💡</span>
                          <span>{a}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <button className="reupload-btn" onClick={handleRemove}>
                🔄 {lang === 'zh' ? '重新上传' : 'Upload Another'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FileUpload;
