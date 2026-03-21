import React, { useState, useRef, useEffect } from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { EffectCards, Pagination, Navigation } from 'swiper/modules';
import { HeartOutlined, HeartFilled, MessageOutlined, ShareAltOutlined, PlusOutlined } from '@ant-design/icons';
import { message } from 'antd';
import DetectionFloater from '../DetectionFloater/DetectionFloater';
import AIDetectionService from '../../services/AIDetectionService';
import { DetectionResult, VideoContent } from '../../types/detection';
import 'swiper/css';
import 'swiper/css/effect-cards';
import 'swiper/css/pagination';
import './MobileSimulator.css';

interface MobileSimulatorProps {
  onDetectionResult?: (result: DetectionResult) => void;
}

const MobileSimulator: React.FC<MobileSimulatorProps> = ({ onDetectionResult }) => {
  const [currentVideo, setCurrentVideo] = useState<VideoContent | null>(null);
  const [detectionResult, setDetectionResult] = useState<DetectionResult | null>(null);
  const [isDetecting, setIsDetecting] = useState(false);
  const [likedVideos, setLikedVideos] = useState<Set<number>>(new Set());
  const [currentTime, setCurrentTime] = useState(new Date());
  const [batteryLevel] = useState(85);
  const [signalStrength] = useState(4);
  const aiService = useRef(new AIDetectionService());

  // 更新时间
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // 模拟视频数据 - 更真实的内容
  const mockVideos: VideoContent[] = [
    {
      id: 1,
      username: '@理财导师王老师',
      avatar: '👨‍💼',
      title: '💰 月入10万的投资秘诀，错过后悔一辈子！',
      description: '#投资理财 #财富自由 #赚钱秘诀 保证收益，无风险投资，限时优惠！添加微信：wxid_xxx 立即开始',
      likes: '2.3万',
      comments: '895',
      shares: '1.2k',
      music: '♪ 励志背景音乐',
      verified: false,
      tags: ['投资理财', '高收益', '无风险'],
      riskLevel: 'danger',
      content: `各位朋友大家好！我是你们的理财导师王老师。
      今天给大家分享一个独家投资秘诀，保证月收益30%以上！
      我的学员小李，上个月投入5万，这个月已经赚了15万！
      现在加入还有限时优惠，原价9980的课程，现在只要998！
      机会难得，仅限今天！扫描屏幕二维码立即加入！`,
      videoUrl: '/videos/fake_investment.mp4',
      duration: 45,
      thumbnail: '📊',
      danmus: [
        { time: 2, text: '真的假的？', risk: false },
        { time: 5, text: '我上个月赚了20万！', risk: true },
        { time: 8, text: '大家小心诈骗', risk: false },
        { time: 12, text: '已加微信，靠谱！', risk: true }
      ]
    },
    {
      id: 2,
      username: '@神医张大师',
      avatar: '👨‍⚕️',
      title: '🏥 祖传秘方，三天治愈糖尿病！医院不想让你知道的秘密',
      description: '#中医养生 #祖传秘方 #包治百病 这个方子传了五代人，效果神奇！',
      likes: '5.6万',
      comments: '3.2k',
      shares: '892',
      music: '♪ 古筝养生音乐',
      verified: false,
      tags: ['中医', '偏方', '糖尿病'],
      riskLevel: 'danger',
      content: `我家祖传的秘方，专治各种疑难杂症！
      糖尿病、高血压、癌症，都能治好！
      医院治不好的，我这里三天见效，七天痊愈！
      纯中药制作，无任何副作用，已治愈上万患者！
      现在下单买三送一，仅限今天！`,
      videoUrl: '/videos/fake_medicine.mp4',
      duration: 60,
      thumbnail: '💊'
    },
    {
      id: 3,
      username: '@央视新闻',
      avatar: '📺',
      title: '📰 今日要闻：国家发布养老金调整方案',
      description: '#新闻 #养老金 #民生 权威发布，关注民生',
      likes: '12.3万',
      comments: '8.5k',
      shares: '2.1k',
      music: '♪ 新闻联播片头曲',
      verified: true,
      tags: ['新闻', '养老金', '政策'],
      riskLevel: 'safe',
      content: `根据国家相关部门最新通知，
      2025年养老金将继续上调，预计涨幅3.5%。
      具体调整方案将于下月正式公布。
      请关注官方渠道获取准确信息。`,
      videoUrl: '/videos/news.mp4',
      duration: 30,
      thumbnail: '📺'
    },
    {
      id: 4,
      username: '@健康科普医生',
      avatar: '👩‍⚕️',
      title: '🏃 科学运动，健康生活',
      description: '#健康科普 #运动养生 #医学知识 三甲医院医生科普',
      likes: '8.9万',
      comments: '2.1k',
      shares: '5.6k',
      music: '♪ 轻松背景音乐',
      verified: true,
      tags: ['健康', '运动', '科普'],
      riskLevel: 'safe',
      content: `大家好，我是某三甲医院的李医生。
      今天给大家科普一下老年人运动注意事项。
      适量运动有益健康，但要注意运动强度。
      建议每天步行30分钟，循序渐进。
      如有不适，请及时就医。`,
      videoUrl: '/videos/health.mp4',
      duration: 45,
      thumbnail: '🏥'
    },
    {
      id: 5,
      username: '@免费送手机',
      avatar: '📱',
      title: '📱 0元领取iPhone15！仅限今天！',
      description: '#免费领取 #iPhone #限时活动 点赞+关注即可参与',
      likes: '18.5k',
      comments: '9.8k',
      shares: '3.2k',
      music: '♪ 动感音乐',
      verified: false,
      tags: ['抽奖', '免费', 'iPhone'],
      riskLevel: 'warning',
      content: `超级福利来啦！
      为庆祝粉丝突破100万，免费送出10台iPhone15！
      参与方式：1.关注 2.点赞 3.评论 4.分享
      添加客服微信：xxx_kefu 领取！`,
      videoUrl: '/videos/giveaway.mp4',
      duration: 20,
      thumbnail: '🎁'
    }
  ];

  // 处理视频切换
  const handleSlideChange = (swiper: any) => {
    const video = mockVideos[swiper.activeIndex];
    setCurrentVideo(video);
    
    // 触发AI检测
    detectContent(video);
  };

  // AI检测内容
  const detectContent = async (video: VideoContent) => {
    setIsDetecting(true);
    
    try {
      // 准备多模态数据
      const multiModalData = {
        text: `${video.title} ${video.description} ${video.content}`,
        username: video.username,
        tags: video.tags,
        verified: video.verified,
        engagement: {
          likes: video.likes,
          comments: video.comments,
          shares: video.shares
        }
      };

      // 调用AI检测服务
      const result = await aiService.current.detectMultiModal(multiModalData);
      
      setDetectionResult(result);
      onDetectionResult?.(result);
      
      // 高风险内容警告
      if (result.level === 'danger') {
        message.warning('⚠️ 检测到高风险内容，请谨慎观看！', 3);
      }
    } catch (error) {
      console.error('AI检测失败:', error);
    } finally {
      setIsDetecting(false);
    }
  };

  // 处理点赞
  const handleLike = (videoId: number) => {
    setLikedVideos(prev => {
      const newSet = new Set(prev);
      if (newSet.has(videoId)) {
        newSet.delete(videoId);
      } else {
        newSet.add(videoId);
      }
      return newSet;
    });
  };

  // 格式化时间
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className="mobile-simulator-container">
      {/* 手机外框 */}
      <div className="phone-frame">
        {/* 手机顶部刘海屏 */}
        <div className="phone-notch">
          <div className="camera"></div>
          <div className="speaker"></div>
        </div>

        {/* 状态栏 */}
        <div className="status-bar">
          <div className="status-left">
            <span className="time">{formatTime(currentTime)}</span>
          </div>
          <div className="status-center">
            <div className="dynamic-island"></div>
          </div>
          <div className="status-right">
            <span className="signal">{'▂'.repeat(signalStrength)}</span>
            <span className="wifi">📶</span>
            <span className="battery">{batteryLevel}% 🔋</span>
          </div>
        </div>

        {/* 视频内容区 */}
        <div className="phone-screen">
          <Swiper
            direction="vertical"
            effect="cards"
            grabCursor={true}
            modules={[EffectCards, Pagination, Navigation]}
            className="video-swiper"
            onSlideChange={handleSlideChange}
            cardsEffect={{
              slideShadows: true,
              rotate: false
            }}
          >
            {mockVideos.map((video, index) => (
              <SwiperSlide key={video.id}>
                <div className="video-container">
                  {/* 视频背景 */}
                  <div className="video-background">
                    <div className="video-thumbnail">{video.thumbnail}</div>
                    
                    {/* 模拟弹幕 */}
                    {video.danmus?.map((danmu, i) => (
                      <div 
                        key={i} 
                        className={`danmu ${danmu.risk ? 'risk' : ''}`}
                        style={{
                          animationDelay: `${danmu.time}s`,
                          top: `${20 + i * 30}px`
                        }}
                      >
                        {danmu.text}
                      </div>
                    ))}
                  </div>

                  {/* 视频信息叠加层 */}
                  <div className="video-overlay">
                    {/* 用户信息 */}
                    <div className="user-info">
                      <div className="avatar">{video.avatar}</div>
                      <div className="username">
                        {video.username}
                        {video.verified && <span className="verified">✓</span>}
                      </div>
                      <button className="follow-btn">
                        <PlusOutlined /> 关注
                      </button>
                    </div>

                    {/* 视频描述 */}
                    <div className="video-info">
                      <h3 className="video-title">{video.title}</h3>
                      <p className="video-description">{video.description}</p>
                      <div className="video-tags">
                        {video.tags.map((tag, i) => (
                          <span key={i} className="tag">#{tag}</span>
                        ))}
                      </div>
                      <div className="music-info">
                        <span className="music-icon">🎵</span>
                        <div className="music-text">{video.music}</div>
                      </div>
                    </div>

                    {/* 互动按钮 */}
                    <div className="interaction-panel">
                      <div 
                        className="interaction-item"
                        onClick={() => handleLike(video.id)}
                      >
                        {likedVideos.has(video.id) ? (
                          <HeartFilled className="icon liked" />
                        ) : (
                          <HeartOutlined className="icon" />
                        )}
                        <span className="count">{video.likes}</span>
                      </div>

                      <div className="interaction-item">
                        <MessageOutlined className="icon" />
                        <span className="count">{video.comments}</span>
                      </div>

                      <div className="interaction-item">
                        <ShareAltOutlined className="icon" />
                        <span className="count">{video.shares}</span>
                      </div>

                      <div className="interaction-item">
                        <div className="music-disc">
                          <img src="/images/disc.png" alt="音乐" />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 进度条 */}
                  <div className="video-progress">
                    <div className="progress-bar"></div>
                  </div>
                </div>
              </SwiperSlide>
            ))}
          </Swiper>

          {/* 底部导航栏 */}
          <div className="bottom-nav">
            <div className="nav-item active">
              <span className="nav-icon">🏠</span>
              <span className="nav-text">首页</span>
            </div>
            <div className="nav-item">
              <span className="nav-icon">🔍</span>
              <span className="nav-text">发现</span>
            </div>
            <div className="nav-item add">
              <span className="nav-icon">➕</span>
            </div>
            <div className="nav-item">
              <span className="nav-icon">💬</span>
              <span className="nav-text">消息</span>
            </div>
            <div className="nav-item">
              <span className="nav-icon">👤</span>
              <span className="nav-text">我</span>
            </div>
          </div>
        </div>

        {/* AI检测状态指示器 */}
        {isDetecting && (
          <div className="ai-detecting">
            <div className="detecting-animation"></div>
            <span>AI分析中...</span>
          </div>
        )}

        {/* 检测结果浮窗 */}
        {detectionResult && (
          <DetectionFloater 
            result={detectionResult}
            onClose={() => setDetectionResult(null)}
          />
        )}
      </div>

      {/* 手机侧边按钮 */}
      <div className="phone-buttons">
        <div className="power-button"></div>
        <div className="volume-up"></div>
        <div className="volume-down"></div>
      </div>
    </div>
  );
};

export default MobileSimulator;
