import React, { useState, useRef, useEffect } from 'react';
import DetectionService from '../../services/DetectionService';
import OpenClawService from '../../services/OpenClawService';
import { DetectionResult, GPTFactCheckResult } from '../../types/detection';
import { Language, t, translateReason } from '../../i18n';
import './FileUpload.css';

interface FileUploadProps {
  onDetectionResult?: (result: DetectionResult) => void;
  onVideoUpload?: (fileUrl: string | null, fileName: string) => void;
  onUploadWarning?: (result: DetectionResult) => void;
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

const FileUpload: React.FC<FileUploadProps> = ({ onDetectionResult, onVideoUpload, onUploadWarning, lang }) => {
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
  const openClawService = useRef(new OpenClawService());
  const [alertSent, setAlertSent] = useState<string | null>(null);

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
      showToast(lang !== 'en' ? '文件大小不能超过100MB' : 'File size must be under 100MB', 'error');
      return;
    }
    if (fileUrl) URL.revokeObjectURL(fileUrl);
    const url = URL.createObjectURL(selectedFile);
    setFile(selectedFile);
    setFileUrl(url);
    setResult(null);
    setGptResult(null);
    setProgress(0);
    onVideoUpload?.(url, selectedFile.name);
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
    if (!file) { showToast(t(lang, 'uploadNoFile'), 'warning'); return; }

    setIsAnalyzing(true);
    setProgress(0);
    setResult(null);
    setGptResult(null);
    setAnalysisLog([]);
    setScanProgress(0);
    setAlertSent(null);

    const zh = lang !== 'en';
    setAnalysisLog([zh ? '📤 上传视频...' : '📤 Uploading video...']);

    // 保存最新的检测结果（用于 GPT 阶段引用）
    const latest = { result: null as DetectionResult | null };

    try {
      await detectionService.current.detectVideoStream(file, '', (event, data) => {
        switch (event) {
          case 'frame':
            setScanProgress(10);
            setAnalysisLog(prev => [...prev,
              `🎞️ ${zh ? '抽取' : 'Extracted'} ${data.frames} ${zh ? '帧' : 'frames'} (${data.time}s)`,
            ]);
            break;

          case 'ocr':
            if (data.duplicate) break;
            setScanProgress(prev => Math.min(prev + 15, 60));
            if (data.text) {
              setAnalysisLog(prev => [...prev,
                `📝 OCR #${data.frame_idx + 1}: "${(data.text as string).slice(0, 80)}${(data.text as string).length > 80 ? '...' : ''}"`,
              ]);
            } else {
              setAnalysisLog(prev => [...prev,
                `⬚ OCR #${data.frame_idx + 1}: ${zh ? '无文字' : 'no text'}`,
              ]);
            }
            break;

          case 'asr':
            if (data.status === 'started') {
              setAnalysisLog(prev => [...prev, zh ? '🎙️ ASR 语音转写中...' : '🎙️ ASR transcribing...']);
            } else if (data.status === 'done') {
              setScanProgress(prev => Math.min(prev + 15, 80));
              if (data.text) {
                setAnalysisLog(prev => [...prev,
                  `✅ ASR: "${(data.text as string).slice(0, 100)}${(data.text as string).length > 100 ? '...' : ''}"`,
                ]);
              } else {
                setAnalysisLog(prev => [...prev, zh ? '⬚ ASR: 未识别到语音' : '⬚ ASR: No speech found']);
              }
            }
            break;

          case 'ai': {
            const stage = data.stage || '';
            setScanProgress(prev => Math.min(prev + 10, 95));
            if (stage.startsWith('ocr_frame_')) {
              // OCR 帧的快速 AI 分析 — 立即展示初步结果
              const lbl = data.level === 'danger' ? '🚨' : data.level === 'warning' ? '⚠️' : '✅';
              const bPct = data.bert_score != null ? Math.round(data.bert_score * 100) : '?';
              const tPct = data.tfidf_score != null ? Math.round(data.tfidf_score * 100) : '?';
              setAnalysisLog(prev => [...prev,
                `${lbl} AI: BERT ${bPct}% | TF-IDF ${tPct}% → ${data.level} (${Math.round((data.score || 0) * 100)}/100)`,
              ]);
              // 更新初步结果到 UI
              const partialResult: DetectionResult = {
                level: data.level || 'safe',
                score: data.score || 0,
                confidence: data.confidence || 0.5,
                message: '',
                reasons: data.reasons || [],
                suggestions: data.suggestions || [],
                timestamp: new Date(),
                detection_method: 'ai_video_upload',
                bert_score: data.bert_score,
                tfidf_score: data.tfidf_score,
                ocr_text: data.text_analyzed || '',
              };
              setResult(partialResult);
              latest.result = partialResult;
              // 如果已经检测到 danger，立即通知
              if (data.level === 'danger') {
                onUploadWarning?.(partialResult);
              }
            } else if (stage === 'final') {
              // 最终完整结果
              const finalResult: DetectionResult = {
                level: data.level || 'safe',
                score: data.score || 0,
                confidence: data.confidence || 0.5,
                message: data.message || '',
                reasons: data.reasons || [],
                suggestions: data.suggestions || [],
                timestamp: new Date(),
                detection_method: data.detection_method || 'ai_video_upload',
                transcript: data.transcript || '',
                ocr_text: data.ocr_text || '',
                frames_used: data.frames_used || 0,
                merged_text: data.merged_text || '',
                bert_score: data.bert_score,
                tfidf_score: data.tfidf_score,
              };
              setResult(finalResult);
              latest.result = finalResult;
              onDetectionResult?.(finalResult);
              if (data.level !== 'safe') {
                onUploadWarning?.(finalResult);
              }
            }
            break;
          }

          case 'conflict':
            setAnalysisLog(prev => [...prev,
              `⚠️ ${zh ? 'ASR/OCR 冲突' : 'ASR/OCR conflict'}: ${data.reason || data.reason_en || ''}`,
            ]);
            break;

          case 'done':
            setScanProgress(100);
            setProgress(100);
            setAnalysisLog(prev => [...prev,
              `━━ ${zh ? 'AI 检测完成' : 'AI detection complete'} ━━`,
            ]);
            break;

          case 'error':
            setAnalysisLog(prev => [...prev, `❌ ${data.message || 'Error'}`]);
            break;
        }
      });

      setIsAnalyzing(false);

      // GPT 异步深度事实核查
      const dr = latest.result;
      if (dr) {
        const textForGpt = dr.merged_text || dr.transcript || dr.ocr_text || '';
        const gptContext = [
          `视频: ${file.name}`,
          dr.transcript ? `ASR: ${dr.transcript.slice(0, 300)}` : '',
          dr.ocr_text ? `OCR: ${dr.ocr_text.slice(0, 300)}` : '',
        ].filter(Boolean).join('\n');

        if (textForGpt.trim().length > 10) {
          setGptLoading(true);
          setAnalysisLog(prev => [...prev, zh ? '🔍 GPT 深度事实核查中...' : '🔍 GPT deep fact-checking...']);
          try {
            const gpt = await detectionService.current.factCheck(textForGpt, gptContext, dr);
            if (gpt && !gpt.fallback) {
              setGptResult(gpt);
              const gptVerdict = gpt.verdict;
              let finalLevel = dr.level;
              let finalScore = dr.score ?? 0;
              if (gptVerdict === 'false' || gpt.risk_level === 'danger') { finalLevel = 'danger'; finalScore = Math.max(finalScore, 0.75); }
              else if (gptVerdict === 'misleading' || gpt.risk_level === 'warning') { if (finalLevel === 'safe') finalLevel = 'warning'; finalScore = Math.max(finalScore, 0.5); }

              const verdictMap: Record<string, string> = { 'false': zh ? '❌ 虚假' : '❌ False', 'misleading': zh ? '⚠️ 误导' : '⚠️ Misleading', 'true': zh ? '✅ 属实' : '✅ True', 'unverifiable': zh ? '❓ 待核实' : '❓ Unverifiable' };
              const verdictText = verdictMap[gptVerdict] || gptVerdict;

              const gptReasons: string[] = [];
              if (gpt.summary) gptReasons.push(`GPT: ${gpt.summary}`);
              if (gpt.false_claims?.length) gpt.false_claims.forEach(c => gptReasons.push(`❌ ${c.original} → ✅ ${c.correction}`));
              if (gpt.related_scam_type && gpt.related_scam_type !== '无') gptReasons.push(`${zh ? '诈骗类型' : 'Scam'}: ${gpt.related_scam_type}`);

              const fusedResult: DetectionResult = { ...dr, level: finalLevel as any, score: finalScore, reasons: [...gptReasons, ...(dr.reasons || [])], suggestions: [...(gpt.safety_advice || []), ...(dr.suggestions || [])] };
              setResult(fusedResult);
              if (finalLevel !== 'safe') { onUploadWarning?.(fusedResult); openClawService.current.reloadConfig(); if (openClawService.current.shouldAlert(fusedResult)) { setAlertSent('sending'); openClawService.current.sendAlert(fusedResult, file.name).then(ok => { setAlertSent(ok ? 'sent' : 'failed'); setTimeout(() => setAlertSent(null), 6000); }).catch(() => { setAlertSent('failed'); }); } }
              setAnalysisLog(prev => [...prev, `✅ GPT: ${verdictText} (${gpt.gpt_latency || '?'}s)`, `━━ ${zh ? '最终判定' : 'Final'}: ${finalLevel === 'danger' ? '🚨' : finalLevel === 'warning' ? '⚠️' : '✅'} ${Math.round(finalScore * 100)}/100 ━━`]);
            }
          } catch { /* GPT 失败静默 */ }
          finally { setGptLoading(false); }
        }
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
    setAlertSent(null);
    onVideoUpload?.(null, '');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const getMethodLabel = (method?: string) => {
    if (!method) return lang !== 'en' ? '未知' : 'Unknown';
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
    return pair ? pair[lang !== 'en' ? 0 : 1] : method;
  };

  const getVerdictLabel = (verdict?: string) => {
    const map: Record<string, [string, string]> = {
      true: ['✅ 信息属实', '✅ Verified True'],
      false: ['❌ 虚假信息', '❌ False'],
      misleading: ['⚠️ 误导性信息', '⚠️ Misleading'],
      unverifiable: ['❓ 暂无法核实', '❓ Unverifiable'],
    };
    const pair = verdict ? map[verdict] : undefined;
    return pair ? pair[lang !== 'en' ? 0 : 1] : (lang !== 'en' ? '未核查' : 'Not checked');
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
                  ? (lang !== 'en' ? '🛡️ AI 实时检测中' : '🛡️ AI Real-time Detection')
                  : (lang !== 'en' ? '✅ 检测完成' : '✅ Detection Complete')
                }</span>
                {isAnalyzing && <span className="fu-live-badge">{lang !== 'en' ? '分析中' : 'Analyzing'}</span>}
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
                  <div className="fu-recognized-title">📋 {lang !== 'en' ? '识别出的内容' : 'Recognized Content'}</div>
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
                  {result.level === 'danger' && (lang !== 'en' ? '高风险内容' : 'High Risk Content')}
                  {result.level === 'warning' && (lang !== 'en' ? '可疑内容' : 'Suspicious Content')}
                  {result.level === 'safe' && (lang !== 'en' ? '内容安全' : 'Content Safe')}
                </span>
                <span className="upload-result-score">{scorePct}/100</span>
              </div>

              {/* 分数条 */}
              <div className="result-score-bar-wrap">
                <div className="result-score-bar">
                  <div className={`result-score-fill ${result.level}`} style={{ width: `${scorePct}%` }} />
                </div>
                <div className="result-score-labels">
                  <span>{lang !== 'en' ? '安全' : 'Safe'}</span>
                  <span>{lang !== 'en' ? '注意' : 'Caution'}</span>
                  <span>{lang !== 'en' ? '危险' : 'Danger'}</span>
                </div>
              </div>

              {/* 检测方法 + 置信度 + 帧数 + 时间 */}
              <div className="result-meta-row">
                <span className="result-meta-tag method">
                  {getMethodLabel(gptResult ? 'ai_video_gpt_factcheck' : result.detection_method)}
                </span>
                {result.confidence != null && (
                  <span className="result-meta-tag confidence">
                    {lang !== 'en' ? '置信度' : 'Conf'}: {Math.round(result.confidence * 100)}%
                  </span>
                )}
                {result.frames_used != null && result.frames_used > 0 && (
                  <span className="result-meta-tag time">
                    🎞️ {result.frames_used} {lang !== 'en' ? '帧' : 'frames'}
                  </span>
                )}
                <span className="result-meta-tag time">
                  ⏱️ {result.timestamp ? new Date(result.timestamp).toLocaleTimeString(lang !== 'en' ? 'zh-CN' : 'en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--'}
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
                          ? (lang !== 'en' ? '⚠️ 风险' : '⚠️ Risky')
                          : (lang !== 'en' ? '✅ 安全' : '✅ Safe')}
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
                          ? (lang !== 'en' ? '⚠️ 风险' : '⚠️ Risky')
                          : (lang !== 'en' ? '✅ 安全' : '✅ Safe')}
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
                  <div className="result-section-title">📋 {lang !== 'en' ? '识别出的视频内容' : 'Recognized Video Content'}</div>
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
                    <div className="fu-recog-empty">{lang !== 'en' ? '未识别到视频中的文字或语音内容' : 'No text or speech detected in this video'}</div>
                  )}
                </div>
              )}

              {/* AI 结论 */}
              {result.message && (
                <div className="result-conclusion">
                  <div className="result-section-title">🧠 {lang !== 'en' ? 'AI 综合分析' : 'AI Analysis'}</div>
                  <div className="result-conclusion-text">{
                    result.message.split('\n').map(line => translateReason(lang, line)).join('\n')
                  }</div>
                </div>
              )}

              {/* 风险因素 */}
              {(result.reasons || []).length > 0 && (
                <div className="result-reasons-section">
                  <div className="result-section-title">⚡ {lang !== 'en' ? '风险因素' : 'Risk Factors'}</div>
                  <div className="upload-result-reasons">
                    {(result.reasons || []).map((r, i) => (
                      <div key={i} className="reason-item-row">
                        <span className="reason-bullet">•</span>
                        <span>{translateReason(lang, r)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 建议 */}
              {(result.suggestions || []).length > 0 && (
                <div className="result-suggestions-section">
                  <div className="result-section-title">💡 {lang !== 'en' ? '安全建议' : 'Safety Suggestions'}</div>
                  <div className="upload-result-suggestions">
                    {(result.suggestions || []).map((s, i) => (
                      <div key={i} className="suggestion-item-row">
                        <span className="suggestion-icon">💡</span>
                        <span>{translateReason(lang, s)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ============ GPT 事实核查（第二阶段，异步追加） ============ */}
              {gptLoading && (
                <div className="result-gpt-section gpt-loading">
                  <div className="result-section-title">🔍 {lang !== 'en' ? 'GPT 事实核查中...' : 'GPT Fact-Checking...'}</div>
                  <div className="gpt-loading-bar">
                    <div className="gpt-loading-fill" />
                  </div>
                  <div className="gpt-loading-hint">
                    {lang !== 'en' ? 'AI 正在深度分析内容真实性，请稍候...' : 'AI is analyzing content authenticity...'}
                  </div>
                </div>
              )}

              {gptResult && (
                <div className="result-gpt-section gpt-loaded">
                  <div className="result-section-title">🔍 {lang !== 'en' ? 'GPT 事实核查' : 'GPT Fact Check'}</div>
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
                      <div className="result-section-title">🚨 {lang !== 'en' ? '虚假信息核查' : 'False Claims Identified'}</div>
                      {gptResult.false_claims.map((claim, i) => (
                        <div key={i} className={`false-claim-card severity-${claim.severity || 'medium'}`}>
                          <div className="false-claim-original">
                            <span className="claim-label claim-false">❌ {lang !== 'en' ? '虚假' : 'False'}</span>
                            <span className="claim-text">{claim.original}</span>
                          </div>
                          <div className="false-claim-arrow">↓</div>
                          <div className="false-claim-correction">
                            <span className="claim-label claim-correct">✅ {lang !== 'en' ? '正确' : 'Correct'}</span>
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

              {/* 推送状态 */}
              {alertSent && (
                <div className={`fu-alert-badge ${alertSent}`}>
                  {alertSent === 'sending' && (lang !== 'en' ? '📡 正在推送企业微信...' : '📡 Sending to WeCom...')}
                  {alertSent === 'sent' && (lang !== 'en' ? '✅ 已推送企业微信告警' : '✅ Alert sent to WeCom')}
                  {alertSent === 'failed' && (lang !== 'en' ? '❌ 推送失败' : '❌ Push failed')}
                </div>
              )}

              <button className="reupload-btn" onClick={handleRemove}>
                🔄 {lang !== 'en' ? '重新上传' : 'Upload Another'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FileUpload;
