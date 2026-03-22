import React, { useState, useRef } from 'react';
import { Button, Progress, message } from 'antd';
import { UploadOutlined, FileOutlined, DeleteOutlined, PlayCircleOutlined } from '@ant-design/icons';
import DetectionService from '../../services/DetectionService';
import { DetectionResult } from '../../types/detection';
import { Language, t } from '../../i18n';
import './FileUpload.css';

interface FileUploadProps {
  onDetectionResult?: (result: DetectionResult) => void;
  lang: Language;
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
      message.error(lang === 'zh' ? '文件大小不能超过100MB' : 'File size must be under 100MB');
      return;
    }
    setFile(selectedFile);
    setResult(null);
    setProgress(0);
    message.success(t(lang, 'uploadSuccess'));
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
      message.warning(t(lang, 'uploadNoFile'));
      return;
    }

    setIsAnalyzing(true);
    setProgress(0);

    // 模拟分析进度
    const progressTimer = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) { clearInterval(progressTimer); return 90; }
        return prev + Math.random() * 15;
      });
    }, 300);

    try {
      // 使用文件名作为检测内容的一部分
      const simulatedContent = `[视频文件] ${file.name} - 用户上传的视频文件内容分析`;
      const detResult = await detectionService.current.detectContent(simulatedContent);

      clearInterval(progressTimer);
      setProgress(100);
      setResult(detResult);
      onDetectionResult?.(detResult);
    } catch (error) {
      clearInterval(progressTimer);
      message.error(t(lang, 'uploadError'));
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
          <UploadOutlined className="upload-icon" />
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
              {file.type.startsWith('video/') ? (
                <PlayCircleOutlined className="file-type-icon video" />
              ) : (
                <FileOutlined className="file-type-icon audio" />
              )}
            </div>
            <div className="file-details">
              <div className="file-name">{file.name}</div>
              <div className="file-meta">
                {formatFileSize(file.size)} • {file.type.split('/')[1]?.toUpperCase() || 'FILE'}
              </div>
            </div>
            <Button
              type="text"
              icon={<DeleteOutlined />}
              onClick={handleRemove}
              className="remove-btn"
              danger
            />
          </div>

          {isAnalyzing && (
            <div className="analysis-progress">
              <Progress
                percent={Math.round(progress)}
                strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
                status="active"
              />
              <span className="progress-text">{t(lang, 'uploadAnalyzing')}</span>
            </div>
          )}

          {!isAnalyzing && !result && (
            <Button
              type="primary"
              size="large"
              onClick={handleAnalyze}
              className="analyze-btn"
              icon={<PlayCircleOutlined />}
            >
              {t(lang, 'uploadAnalyze')}
            </Button>
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
              <Button
                type="primary"
                ghost
                onClick={handleRemove}
                className="reupload-btn"
              >
                {lang === 'zh' ? '重新上传' : 'Upload Another'}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FileUpload;
