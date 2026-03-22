import React, { useState, useRef } from 'react';
import DetectionService from '../../services/DetectionService';
import { DetectionResult } from '../../types/detection';
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
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const detectionService = useRef(new DetectionService());

  const acceptedTypes = [
    'video/mp4', 'video/avi', 'video/quicktime', 'video/x-msvideo', 'video/webm',
    'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp3',
  ];

  const handleFileSelect = (selectedFile: File) => {
    if (selectedFile.size > 100 * 1024 * 1024) {
      showToast(lang === 'zh' ? '文件大小不能超过100MB' : 'File size must be under 100MB', 'error');
      return;
    }
    setFile(selectedFile);
    setResult(null);
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

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => setDragOver(false);

  const handleAnalyze = async () => {
    if (!file) {
      showToast(t(lang, 'uploadNoFile'), 'warning');
      return;
    }

    setIsAnalyzing(true);
    setProgress(0);

    const progressTimer = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) { clearInterval(progressTimer); return 90; }
        return prev + Math.random() * 15;
      });
    }, 300);

    try {
      const simulatedContent = `[视频文件] ${file.name} - 用户上传的视频文件内容分析`;
      const detResult = await detectionService.current.detectContent(simulatedContent);

      clearInterval(progressTimer);
      setProgress(100);
      setResult(detResult);
      onDetectionResult?.(detResult);
    } catch (error) {
      clearInterval(progressTimer);
      showToast(t(lang, 'uploadError'), 'error');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleRemove = () => {
    setFile(null);
    setResult(null);
    setProgress(0);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const pct = Math.round(progress);

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
          <div className="file-info-card">
            <div className="file-icon-wrap">
              <span className={`file-type-icon ${file.type.startsWith('video/') ? 'video' : 'audio'}`}>
                {file.type.startsWith('video/') ? '🎬' : '🎵'}
              </span>
            </div>
            <div className="file-details">
              <div className="file-name">{file.name}</div>
              <div className="file-meta">
                {formatFileSize(file.size)} • {file.type.split('/')[1]?.toUpperCase() || 'FILE'}
              </div>
            </div>
            <button className="remove-btn" onClick={handleRemove} title="Remove">🗑️</button>
          </div>

          {isAnalyzing && (
            <div className="analysis-progress">
              <div className="native-progress">
                <div className="native-progress-bar" style={{ width: `${pct}%` }} />
              </div>
              <span className="progress-text">{pct}% — {t(lang, 'uploadAnalyzing')}</span>
            </div>
          )}

          {!isAnalyzing && !result && (
            <button className="analyze-btn" onClick={handleAnalyze}>
              ▶️ {t(lang, 'uploadAnalyze')}
            </button>
          )}

          {result && (
            <div className={`upload-result ${result.level}`}>
              <div className="upload-result-header">
                <span className="upload-result-icon">
                  {result.level === 'danger' && '🚨'}
                  {result.level === 'warning' && '⚠️'}
                  {result.level === 'safe' && '✅'}
                </span>
                <span className="upload-result-title">
                  {result.level === 'danger' && t(lang, 'dangerTitle')}
                  {result.level === 'warning' && t(lang, 'warningTitle')}
                  {result.level === 'safe' && t(lang, 'safeTitle')}
                </span>
                <span className="upload-result-score">
                  {Math.round((result.score ?? 0) * 100)}/100
                </span>
              </div>
              {(result.reasons || []).length > 0 && (
                <div className="upload-result-reasons">
                  {(result.reasons || []).map((r, i) => <div key={i}>• {r}</div>)}
                </div>
              )}
              {(result.suggestions || []).length > 0 && (
                <div className="upload-result-suggestions">
                  {(result.suggestions || []).map((s, i) => <div key={i}>💡 {s}</div>)}
                </div>
              )}
              <button className="reupload-btn" onClick={handleRemove}>
                {lang === 'zh' ? '重新上传' : 'Upload Another'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FileUpload;
