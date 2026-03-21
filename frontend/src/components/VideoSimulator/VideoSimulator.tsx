import React, { useState, useRef, useEffect } from 'react';
import { Button, Card, message } from 'antd';
import { AudioCapture, DetectionResult, VideoInfo } from '../../types/detection';
import AudioCaptureService from '../../services/AudioCaptureService';
import DetectionService from '../../services/DetectionService';
import './VideoSimulator.css';

interface VideoSimulatorProps {
  isListening: boolean;
  onListeningChange: (listening: boolean) => void;
  onDetectionResult: (result: DetectionResult) => void;
}

const VideoSimulator: React.FC<VideoSimulatorProps> = ({
  isListening,
  onListeningChange,
  onDetectionResult
}) => {
  const [currentVideo, setCurrentVideo] = useState<VideoInfo>({
    title: '选择下面的视频开始体验检测功能',
    description: '',
    duration: 0,
    platform: 'douyin'
  });
  
  const [audioCapture, setAudioCapture] = useState<AudioCapture>({
    isRecording: false,
    audioData: null,
    transcript: ''
  });

  const audioServiceRef = useRef<AudioCaptureService>();
  const detectionServiceRef = useRef<DetectionService>();

  useEffect(() => {
    audioServiceRef.current = new AudioCaptureService();
    detectionServiceRef.current = new DetectionService();
    
    return () => {
      audioServiceRef.current?.stopCapture();
    };
  }, []);

  // 模拟视频数据
  const mockVideos = [
    {
      id: 1,
      title: '💰 投资理财新机会！月入3万不是梦',
      description: '专业团队指导，保证收益，无任何风险！联系微信：xxx',
      duration: 60,
      platform: 'douyin' as const,
      riskLevel: 'danger' as const,
      content: '各位朋友大家好，我是你们的理财导师小王。今天要给大家分享一个绝密的投资机会，月入3万，年收益率300%，保证无风险。我们有专业的团队，内部消息，股票期货都能帮你赚钱。现在限时优惠，只要998，就能加入我们的VIP群。'
    },
    {
      id: 2,
      title: '🏥 神奇保健品，包治百病！',
      description: '祖传秘方，三天见效，医院不告诉你的秘密',
      duration: 45,
      platform: 'wechat' as const,
      riskLevel: 'danger' as const,
      content: '这款神奇的保健品是祖传秘方，可以治疗高血压、糖尿病、癌症等各种疾病。医院不告诉你，三天见效，一个疗程彻底根治。现在特价销售，原价3980，现在只要980元。'
    },
    {
      id: 3,
      title: '⚠️ 限时优惠活动',
      description: '商品促销，数量有限',
      duration: 60,
      platform: 'douyin' as const,
      riskLevel: 'warning' as const,
      content: '限时抢购，原价999现在只要99！数量有限，先到先得！点击下方链接立即购买。'
    },
    {
      id: 4,
      title: '🍎 健康饮食小贴士',
      description: '营养专家分享日常饮食建议',
      duration: 120,
      platform: 'douyin' as const,
      riskLevel: 'safe' as const,
      content: '大家好，我是营养师李医生。今天给大家分享一些健康饮食的小贴士。均衡饮食很重要，建议每天摄入足够的蔬菜水果，适量的蛋白质，少油少盐。如有健康问题，建议咨询专业医生。'
    },
    {
      id: 5,
      title: '💳 正规银行理财产品介绍',
      description: '某银行官方发布的理财产品说明',
      duration: 90,
      platform: 'other' as const,
      riskLevel: 'safe' as const,
      content: '我行推出新的理财产品，年化收益率3.5%，风险等级为R2级，适合稳健型投资者。请注意，理财有风险，投资需谨慎。详情请咨询我行各网点。'
    }
  ];

  const startListening = async () => {
    try {
      await audioServiceRef.current?.startCapture((transcript) => {
        setAudioCapture(prev => ({ ...prev, transcript }));
        
        // 检测音频转录的文本
        if (transcript) {
          detectContent(transcript);
        }
      });
      
      onListeningChange(true);
      message.success('开始监听音频，请播放视频内容');
    } catch (error) {
      console.error('启动音频监听失败:', error);
      message.error('无法访问麦克风，请检查浏览器权限设置');
    }
  };

  const stopListening = () => {
    audioServiceRef.current?.stopCapture();
    onListeningChange(false);
    setAudioCapture({
      isRecording: false,
      audioData: null,
      transcript: ''
    });
    message.info('已停止监听');
  };

  const detectContent = async (content: string) => {
    if (!content.trim()) return;
    
    try {
      const result = await detectionServiceRef.current?.detectContent(content);
      if (result) {
        onDetectionResult(result);
      }
    } catch (error) {
      console.error('检测失败:', error);
    }
  };

  const playMockVideo = (video: any) => {
    setCurrentVideo({
      title: video.title,
      description: video.description,
      duration: video.duration,
      platform: video.platform
    });

    // 模拟视频播放，自动检测内容
    setTimeout(() => {
      detectContent(video.content);
    }, 2000); // 2秒后显示检测结果
  };

  return (
    <div className="video-simulator">
      <Card title="📱 短视频模拟器" className="simulator-card">
        {/* 视频播放区域 */}
        <div className="video-player">
          <div className="video-screen">
            <div className="video-content">
              <h3>{currentVideo.title}</h3>
              {currentVideo.description && (
                <p className="video-description">{currentVideo.description}</p>
              )}
              <div className="video-controls">
                <span className="platform-tag">
                  {currentVideo.platform === 'douyin' && '📳 抖音'}
                  {currentVideo.platform === 'wechat' && '💬 微信'}
                  {currentVideo.platform === 'kuaishou' && '🎬 快手'}
                  {currentVideo.platform === 'other' && '📺 其他'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* 控制按钮 */}
        <div className="control-buttons">
          {!isListening ? (
            <Button 
              type="primary" 
              size="large" 
              onClick={startListening}
              className="control-btn start-btn"
            >
              🎤 开始监听
            </Button>
          ) : (
            <Button 
              danger 
              size="large" 
              onClick={stopListening}
              className="control-btn stop-btn"
            >
              🛑 停止监听
            </Button>
          )}
        </div>

        {/* 音频转录显示 */}
        {audioCapture.transcript && (
          <div className="transcript-display">
            <h4>🎵 检测到的音频内容：</h4>
            <p>{audioCapture.transcript}</p>
          </div>
        )}
      </Card>

      {/* 模拟视频列表 */}
      <Card title="🎬 体验视频" className="mock-videos">
        <div className="video-list">
          {mockVideos.map(video => (
            <div 
              key={video.id} 
              className={`video-item ${video.riskLevel}`}
              onClick={() => playMockVideo(video)}
            >
              <div className="video-thumb">
                <span className="risk-indicator">
                  {video.riskLevel === 'danger' && '🔴'}
                  {video.riskLevel === 'warning' && '🟡'}
                  {video.riskLevel === 'safe' && '🟢'}
                </span>
              </div>
              <div className="video-info">
                <h4>{video.title}</h4>
                <p>{video.description}</p>
                <span className="duration">{video.duration}秒</span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

export default VideoSimulator;
