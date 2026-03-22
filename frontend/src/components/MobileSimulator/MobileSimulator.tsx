import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { HeartOutlined, HeartFilled, MessageOutlined, ShareAltOutlined } from '@ant-design/icons';
import DetectionFloater from '../DetectionFloater/DetectionFloater';
import FileUpload from '../FileUpload/FileUpload';
import DetectionService from '../../services/DetectionService';
import OpenClawService from '../../services/OpenClawService';
import { DetectionResult, VideoContent } from '../../types/detection';
import { Language, t } from '../../i18n';
import './MobileSimulator.css';

interface MobileSimulatorProps {
  onDetectionResult?: (result: DetectionResult) => void;
  lang: Language;
}

/** 将一段长文本拆分成短句字幕 */
function splitSubtitles(text: string): string[] {
  const raw = text.split(/(?<=[。！？；\n])|(?<=[.!?;]\s)/g).map(s => s.trim()).filter(Boolean);
  const result: string[] = [];
  for (const s of raw) {
    if (s.length > 22) {
      const sub = s.split(/(?<=[，,、])/g).map(x => x.trim()).filter(Boolean);
      result.push(...sub);
    } else {
      result.push(s);
    }
  }
  return result.length > 0 ? result : [text];
}

const RISK_KEYWORDS = [
  '保证收益','无风险投资','月入万元','投资理财','高收益','稳赚不赔',
  '内幕消息','股票推荐','虚拟货币','挖矿','传销','贷款','借钱',
  '包治百病','神奇疗效','祖传秘方','一次根治','医院不告诉你',
  '癌症克星','延年益寿','偏方','特效药','保健品','三无产品',
  '限时优惠','马上行动','不要错过','机会难得','免费领取','0元购',
  '中奖','扫码','加微信','转账','汇款','紧急','赶紧','立即',
  '身份证','银行卡','验证更新','点击链接','失效',
  '月收益','财务自由','下载','扫描二维码','订购热线',
  '央视推荐','买三送一','特惠价',
];

const MobileSimulator: React.FC<MobileSimulatorProps> = ({ onDetectionResult, lang }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [detectionResult, setDetectionResult] = useState<DetectionResult | null>(null);
  const [isDetecting, setIsDetecting] = useState(false);
  const [likedVideos, setLikedVideos] = useState<Set<number>>(new Set());
  const [currentTime, setCurrentTime] = useState(new Date());
  const [progress, setProgress] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [touchStart, setTouchStart] = useState(0);
  const [translateY, setTranslateY] = useState(0);
  const [activeTab, setActiveTab] = useState<'phone' | 'upload'>('phone');
  const [alertSent, setAlertSent] = useState<string | null>(null);
  const [showFullWarning, setShowFullWarning] = useState(false);
  const [analysisLog, setAnalysisLog] = useState<string[]>([]);
  const [currentSubtitleIdx, setCurrentSubtitleIdx] = useState(0);
  const [subtitleVisible, setSubtitleVisible] = useState(true);
  const [liveExtractedLines, setLiveExtractedLines] = useState<string[]>([]);
  const [liveHighlightIdx, setLiveHighlightIdx] = useState(-1);
  const [scanProgress, setScanProgress] = useState(0);

  const detectionService = useRef(new DetectionService());
  const openClawService = useRef(new OpenClawService());
  const subtitleTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const liveLogRef = useRef<HTMLDivElement | null>(null);
  const lastDetectedIndex = useRef<number>(-1);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    setProgress(0);
    const timer = setInterval(() => {
      setProgress(prev => prev >= 100 ? 0 : prev + 0.5);
    }, 150);
    return () => clearInterval(timer);
  }, [currentIndex]);

  const mockVideos: VideoContent[] = useMemo(() => [
    { id:1, username:lang==='zh'?'理财导师王老师':'Finance Guru Wang', avatar:'👨‍💼', title:lang==='zh'?'月入10万的投资秘诀！错过后悔一辈子':'100K Monthly! Investment Secrets', description:lang==='zh'?'保证收益，无风险投资，限时优惠！添加微信立即开始':'Guaranteed returns, risk-free!', likes:'2.3万', comments:'895', shares:'1.2k', music:lang==='zh'?'励志背景音乐 - 原声':'Motivational BGM', verified:false, tags:lang==='zh'?['投资理财','高收益','无风险']:['Investment','High Returns'], riskLevel:'danger' as const, content:'各位朋友大家好！我是你们的理财导师王老师。今天给大家分享一个独家投资秘诀，保证月收益30%以上！我的学员小李，上个月投入5万，这个月已经赚了15万！现在加入还有限时优惠！机会难得，仅限今天！扫描二维码立即加入！', duration:45, thumbnail:'📊' },
    { id:2, username:lang==='zh'?'神医张大师':'Dr. Zhang Healer', avatar:'🧓', title:lang==='zh'?'祖传秘方三天治愈糖尿病！医院不想让你知道':'3-Day Diabetes Cure!', description:lang==='zh'?'五代祖传秘方，效果神奇！包治百病！':'Ancient recipe, cures everything!', likes:'5.6万', comments:'3.2k', shares:'892', music:lang==='zh'?'古筝养生音乐 - 原声':'Traditional Music', verified:false, tags:lang==='zh'?['中医养生','祖传秘方']:['Traditional Medicine'], riskLevel:'danger' as const, content:'我家祖传的秘方，专治各种疑难杂症！糖尿病、高血压、癌症，都能治好！医院治不好的，我这里三天见效，七天痊愈！纯中药制作，无任何副作用，已治愈上万患者！现在下单买三送一！', duration:60, thumbnail:'💊' },
    { id:3, username:lang==='zh'?'央视新闻':'CCTV News', avatar:'📺', title:lang==='zh'?'今日要闻：国家发布养老金调整方案':'Breaking: Pension Adjustment', description:lang==='zh'?'权威发布，关注民生':'Official release', likes:'12.3万', comments:'8.5k', shares:'2.1万', music:lang==='zh'?'新闻联播片头曲 - 原声':'News Theme', verified:true, tags:lang==='zh'?['新闻','养老金','政策']:['News','Pension'], riskLevel:'safe' as const, content:'根据国家相关部门最新通知，2025年养老金将继续上调，预计涨幅3.5%。具体调整方案将于下月正式公布。请关注官方渠道获取准确信息。', duration:30, thumbnail:'📰' },
    { id:4, username:lang==='zh'?'李医生科普':'Dr. Li Health', avatar:'👩‍⚕️', title:lang==='zh'?'科学运动 健康生活 | 三甲医院医生教你':'Healthy Exercise Guide', description:lang==='zh'?'三甲医院主任医师，专业科普':'Chief physician advice', likes:'8.9万', comments:'2.1k', shares:'5.6k', music:lang==='zh'?'轻松背景音乐 - 原声':'Relaxing BGM', verified:true, tags:lang==='zh'?['健康科普','运动养生']:['Health Tips'], riskLevel:'safe' as const, content:'大家好，我是某三甲医院的李医生。今天给大家科普一下老年人运动注意事项。适量运动有益健康，但要注意运动强度。建议每天步行30分钟，循序渐进。如有不适，请及时就医。', duration:45, thumbnail:'🏥' },
    { id:5, username:lang==='zh'?'幸运大转盘':'Lucky Wheel', avatar:'🎁', title:lang==='zh'?'0元领取iPhone15！转发就有机会！':'Free iPhone15!', description:lang==='zh'?'点赞+关注即可参与抽奖，100%中奖！':'Like + Follow for 100% win!', likes:'18.5k', comments:'9.8k', shares:'3.2k', music:lang==='zh'?'动感音乐 - 原声':'Upbeat Music', verified:false, tags:lang==='zh'?['抽奖','免费领取']:['Giveaway','Free'], riskLevel:'warning' as const, content:'超级福利来啦！为庆祝粉丝突破100万，免费送出10台iPhone15！参与方式：1.关注 2.点赞 3.评论区留言 4.转发给好友。添加客服微信领取！', duration:20, thumbnail:'📱' },
    { id:6, username:lang==='zh'?'美食家小厨':'Chef Xiao', avatar:'👨‍🍳', title:lang==='zh'?'红烧肉的做法 入口即化 老人孩子都爱吃':'Perfect Braised Pork', description:lang==='zh'?'家常菜教程，简单易学':'Easy home cooking', likes:'6.7万', comments:'1.8k', shares:'4.3k', music:lang==='zh'?'轻快厨房音乐 - 原声':'Kitchen BGM', verified:true, tags:lang==='zh'?['美食','家常菜']:['Food','Cooking'], riskLevel:'safe' as const, content:'今天教大家做一道经典红烧肉。选用五花肉，先焯水去腥，再加入老抽、生抽、冰糖和八角慢炖一小时。肉质软烂入味，全家都爱吃。注意控制油盐摄入，适量食用。', duration:55, thumbnail:'🍖' },
    { id:7, username:lang==='zh'?'虚拟币挖矿教程':'Crypto Mining', avatar:'💎', title:lang==='zh'?'每天挖矿躺赚1000元！退休后的最佳选择':'Earn $200/Day Mining!', description:lang==='zh'?'只需一台手机，轻松赚钱！加入我们的矿池':'Just need a phone!', likes:'3.1万', comments:'2.4k', shares:'1.8k', music:lang==='zh'?'科技感背景音乐 - 原声':'Tech BGM', verified:false, tags:lang==='zh'?['虚拟货币','挖矿','被动收入']:['Crypto','Mining'], riskLevel:'danger' as const, content:'各位叔叔阿姨好！我来教大家用手机挖矿赚钱，每天轻松赚1000块！不需要任何投资，只要下载我们的APP就可以开始！已经有上万人通过这个方法实现了财务自由！赶紧扫码下载！虚拟货币是未来趋势！', duration:40, thumbnail:'⛏️' },
    { id:8, username:lang==='zh'?'太极陈师傅':'Master Chen Tai Chi', avatar:'🧘', title:lang==='zh'?'晨练太极养生 每天15分钟精神百倍':'Morning Tai Chi', description:lang==='zh'?'适合中老年人的养生太极，跟着练就对了':'Perfect for seniors', likes:'15.2万', comments:'4.3k', shares:'8.9k', music:lang==='zh'?'太极拳配乐 - 原声':'Tai Chi Music', verified:true, tags:lang==='zh'?['太极','养生','晨练']:['Tai Chi','Wellness'], riskLevel:'safe' as const, content:'早上好！跟着陈师傅一起练太极吧。太极拳讲究以柔克刚，动作缓慢，非常适合中老年朋友。每天坚持15分钟，可以改善平衡力、增强体质。记住量力而行，感觉不适就休息。', duration:90, thumbnail:'☯️' },
    { id:9, username:lang==='zh'?'紧急通知官方号':'Urgent Notice', avatar:'🔔', title:lang==='zh'?'紧急！社保卡即将失效，请立即点击链接更新':'URGENT! Social Card Expiring!', description:lang==='zh'?'不更新将无法享受医保，请马上操作':'Must update now!', likes:'890', comments:'456', shares:'2.3k', music:lang==='zh'?'紧急警报音 - 原声':'Alert Sound', verified:false, tags:lang==='zh'?['紧急通知','社保']:['Urgent','Social Security'], riskLevel:'danger' as const, content:'紧急通知！您的社保卡即将于本月底失效！如不及时更新，将无法享受医疗保险报销！请立即点击以下链接，输入您的身份证号和银行卡信息进行验证更新！限时48小时！赶紧操作！', duration:25, thumbnail:'🚨' },
    { id:10, username:lang==='zh'?'广场舞王阿姨':'Auntie Wang Dance', avatar:'💃', title:lang==='zh'?'最新广场舞教学 今年最火的舞曲':'Latest Square Dance', description:lang==='zh'?'简单易学，适合所有人，跟着跳起来！':'Easy to learn!', likes:'23.4万', comments:'5.6k', shares:'12.3k', music:lang==='zh'?'最炫民族风 - 凤凰传奇':'Folk Dance Music', verified:true, tags:lang==='zh'?['广场舞','健身','快乐']:['Dance','Fitness'], riskLevel:'safe' as const, content:'姐妹们好！今天教大家跳今年最流行的广场舞，动作简单，节奏欢快。跳广场舞不仅锻炼身体，还能交到好朋友。记得穿舒适的鞋子，注意安全。我们小区的舞蹈队欢迎大家加入！', duration:120, thumbnail:'💃' },
    { id:11, username:lang==='zh'?'养生堂保健品':'Health Supplements', avatar:'💉', title:lang==='zh'?'央视推荐！这款保健品能延年益寿20年':'TV Endorsed Supplement!', description:lang==='zh'?'冒充央视推荐，实际是三无产品':'Fake TV endorsement', likes:'4.5万', comments:'6.7k', shares:'3.4k', music:lang==='zh'?'高级感背景音乐 - 原声':'Premium BGM', verified:false, tags:lang==='zh'?['保健品','养生','长寿']:['Supplements','Longevity'], riskLevel:'danger' as const, content:'这款神奇的保健品经过央视权威推荐！内含珍贵虫草、灵芝、人参精华！每天两粒，延年益寿20年！原价3980，现在特惠价仅需398！买五送三！限量供应！赶紧拨打订购热线400-xxx-xxxx！', duration:35, thumbnail:'💊' },
    { id:12, username:lang==='zh'?'公安部反诈中心':'Anti-Fraud Center', avatar:'🚔', title:lang==='zh'?'反诈提醒：这些骗局专门针对老年人':'Anti-Scam Alert', description:lang==='zh'?'国家反诈中心权威发布，请转发给家人':'Official anti-fraud tips', likes:'45.6万', comments:'12.3k', shares:'38.7k', music:lang==='zh'?'反诈宣传曲 - 原声':'Anti-Fraud Theme', verified:true, tags:lang==='zh'?['反诈','安全','防骗']:['Anti-Fraud','Safety'], riskLevel:'safe' as const, content:'大家好，这里是公安部反诈中心。提醒广大老年朋友：1.不要相信陌生来电中的投资理财建议 2.不要扫描来路不明的二维码 3.不要向陌生人转账汇款 4.遇到可疑情况请拨打96110反诈专线。守护好自己的钱袋子！', duration:50, thumbnail:'🛡️' },
  ], [lang]);

  const currentVideo = mockVideos[currentIndex];
  const subtitles = useMemo(() => splitSubtitles(currentVideo.content), [currentVideo.content]);

  // 字幕滚动
  useEffect(() => {
    setCurrentSubtitleIdx(0);
    setSubtitleVisible(true);
    if (subtitleTimerRef.current) clearInterval(subtitleTimerRef.current);
    const interval = Math.max(2200, (currentVideo.duration * 1000) / subtitles.length);
    subtitleTimerRef.current = setInterval(() => {
      setSubtitleVisible(false);
      setTimeout(() => {
        setCurrentSubtitleIdx(prev => (prev + 1) % subtitles.length);
        setSubtitleVisible(true);
      }, 300);
    }, interval);
    return () => { if (subtitleTimerRef.current) clearInterval(subtitleTimerRef.current); };
  }, [currentIndex, subtitles, currentVideo.duration]);

  // 关键词高亮渲染
  const renderHighlightedText = useCallback((text: string) => {
    const parts: React.ReactNode[] = [];
    let remaining = text;
    let key = 0;
    while (remaining.length > 0) {
      let earliest = -1;
      let matchedKw = '';
      for (const kw of RISK_KEYWORDS) {
        const idx = remaining.indexOf(kw);
        if (idx !== -1 && (earliest === -1 || idx < earliest)) { earliest = idx; matchedKw = kw; }
      }
      if (earliest === -1) { parts.push(<span key={key++}>{remaining}</span>); break; }
      if (earliest > 0) parts.push(<span key={key++}>{remaining.substring(0, earliest)}</span>);
      parts.push(<span key={key++} className="risk-keyword-hl">{matchedKw}</span>);
      remaining = remaining.substring(earliest + matchedKw.length);
    }
    return parts;
  }, []);

  const detectContent = useCallback(async (video: VideoContent) => {
    setIsDetecting(true);
    setDetectionResult(null);
    setAlertSent(null);
    setShowFullWarning(false);
    setAnalysisLog([]);
    setLiveExtractedLines([]);
    setLiveHighlightIdx(-1);
    setScanProgress(0);

    const subs = splitSubtitles(video.content);
    const phases = lang === 'zh'
      ? [
          { text: '📡 连接AI检测引擎...', delay: 400 },
          { text: '📝 提取视频语音字幕...', delay: 200 },
          { text: '🤖 MacBERT 中文语义编码...', delay: 500 },
          { text: '🔍 金融/医疗/诈骗关键词扫描...', delay: 400 },
          { text: '⚡ 紧急性语言模式分析...', delay: 300 },
          { text: '🧠 三层融合风险评估...', delay: 500 },
          { text: '📊 生成综合检测报告...', delay: 200 },
        ]
      : [
          { text: '📡 Connecting AI engine...', delay: 400 },
          { text: '📝 Extracting subtitles...', delay: 200 },
          { text: '🤖 MacBERT encoding...', delay: 500 },
          { text: '🔍 Keyword scanning...', delay: 400 },
          { text: '⚡ Urgency pattern analysis...', delay: 300 },
          { text: '🧠 3-layer fusion assessment...', delay: 500 },
          { text: '📊 Generating report...', delay: 200 },
        ];

    const showPhases = async () => {
      setAnalysisLog([phases[0].text]);
      await new Promise(r => setTimeout(r, phases[0].delay));
      setAnalysisLog(prev => [...prev, phases[1].text]);
      const lineDelay = Math.max(150, 1200 / subs.length);
      for (let i = 0; i < subs.length; i++) {
        setLiveExtractedLines(prev => [...prev, subs[i]]);
        setLiveHighlightIdx(i);
        setScanProgress(Math.round(((i + 1) / subs.length) * 30));
        await new Promise(r => setTimeout(r, lineDelay));
      }
      for (let i = 2; i < phases.length; i++) {
        setAnalysisLog(prev => [...prev, phases[i].text]);
        setScanProgress(30 + Math.round(((i - 1) / (phases.length - 2)) * 70));
        await new Promise(r => setTimeout(r, phases[i].delay));
      }
      setScanProgress(100);
    };

    try {
      const fullText = `${video.title} ${video.description} ${video.content}`;
      const [result] = await Promise.all([
        detectionService.current.detectContent(fullText),
        showPhases(),
      ]);

      setAnalysisLog(prev => [...prev, lang === 'zh' ? '✅ 检测完成' : '✅ Detection complete']);
      setDetectionResult(result);
      onDetectionResult?.(result);

      if (result.level === 'danger') setShowFullWarning(true);
      else if (result.level === 'warning') { setShowFullWarning(true); setTimeout(() => setShowFullWarning(false), 3000); }

      if (openClawService.current.shouldAlert(result)) {
        setAlertSent('sending');
        try {
          const success = await openClawService.current.sendAlert(result, video.title);
          setAlertSent(success ? 'sent' : 'failed');
          setTimeout(() => setAlertSent(null), 5000);
        } catch { setAlertSent('failed'); setTimeout(() => setAlertSent(null), 5000); }
      }
    } catch (error) {
      console.error('Detection failed:', error);
      setAnalysisLog(prev => [...prev, lang === 'zh' ? '❌ 检测异常' : '❌ Detection error']);
    } finally {
      setIsDetecting(false);
    }
  }, [onDetectionResult, lang]);

  useEffect(() => {
    // 只在切换到新视频时触发检测，当前视频不重复检测
    if (lastDetectedIndex.current === currentIndex) return;
    lastDetectedIndex.current = currentIndex;
    const timer = setTimeout(() => detectContent(currentVideo), 600);
    return () => clearTimeout(timer);
  }, [currentIndex, currentVideo, detectContent]);

  useEffect(() => {
    if (liveLogRef.current) liveLogRef.current.scrollTop = liveLogRef.current.scrollHeight;
  }, [liveExtractedLines, analysisLog]);

  const handleTouchStart = (e: React.TouchEvent | React.MouseEvent) => { const y = 'touches' in e ? e.touches[0].clientY : e.clientY; setTouchStart(y); setTranslateY(0); };
  const handleTouchMove = (e: React.TouchEvent | React.MouseEvent) => { if (!touchStart) return; const y = 'touches' in e ? e.touches[0].clientY : e.clientY; setTranslateY(Math.max(-100, Math.min(100, touchStart - y))); };
  const handleTouchEnd = () => { if (Math.abs(translateY) > 50) { const d = translateY > 0 ? 1 : -1; const n = currentIndex + d; if (n >= 0 && n < mockVideos.length) { setIsTransitioning(true); setTimeout(() => { setCurrentIndex(n); setIsTransitioning(false); }, 200); } } setTranslateY(0); setTouchStart(0); };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown' && currentIndex < mockVideos.length - 1) { setIsTransitioning(true); setTimeout(() => { setCurrentIndex(p => p + 1); setIsTransitioning(false); }, 200); }
      if (e.key === 'ArrowUp' && currentIndex > 0) { setIsTransitioning(true); setTimeout(() => { setCurrentIndex(p => p - 1); setIsTransitioning(false); }, 200); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [currentIndex, mockVideos.length]);

  const handleLike = (id: number) => { setLikedVideos(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; }); };
  const formatTime = (d: Date) => d.toLocaleTimeString(lang === 'zh' ? 'zh-CN' : 'en-US', { hour: '2-digit', minute: '2-digit' });

  const gradients = [
    'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
    'linear-gradient(135deg, #2d1b3d 0%, #1a1a2e 50%, #16213e 100%)',
    'linear-gradient(135deg, #0f3460 0%, #16213e 50%, #1a1a2e 100%)',
    'linear-gradient(135deg, #1b2a4a 0%, #12243a 50%, #0a1628 100%)',
    'linear-gradient(135deg, #2a1a3e 0%, #1a1a2e 50%, #0f2460 100%)',
    'linear-gradient(135deg, #1e3a2f 0%, #162e20 50%, #0f2018 100%)',
  ];

  return (
    <div className="simulator-page">
      <div className="phone-wrapper">
        <div className="phone-frame">
          <div className="status-bar">
            <span className="sb-time">{formatTime(currentTime)}</span>
            <div className="sb-island"></div>
            <div className="sb-right"><span>📶</span><span>WiFi</span><span>85% 🔋</span></div>
          </div>
          <div className="video-viewport" onTouchStart={handleTouchStart} onTouchMove={handleTouchMove} onTouchEnd={handleTouchEnd} onMouseDown={handleTouchStart} onMouseMove={(e) => touchStart && handleTouchMove(e)} onMouseUp={handleTouchEnd} onMouseLeave={handleTouchEnd}>
            <div className={`video-slide ${isTransitioning ? 'transitioning' : ''}`} style={{ background: gradients[currentIndex % gradients.length] }}>
              <div className="video-center-icon">{currentVideo.thumbnail}</div>

              {/* ===== 动态字幕 ===== */}
              <div className="video-subtitle-area">
                <div className={`video-subtitle ${subtitleVisible ? 'show' : 'hide'}`}>
                  {subtitles[currentSubtitleIdx]}
                </div>
              </div>

              <div className="video-top-bar">
                <span className="top-tab">{t(lang, 'follow')}</span>
                <span className="top-tab active">{t(lang, 'recommend')}</span>
              </div>

              <div className="side-actions">
                <div className="side-avatar">
                  <div className="avatar-circle">{currentVideo.avatar}</div>
                  {!currentVideo.verified && <div className="follow-badge">+</div>}
                </div>
                <div className="side-btn" onClick={() => handleLike(currentVideo.id)}>
                  {likedVideos.has(currentVideo.id) ? <HeartFilled style={{ color: '#ff2c55', fontSize: 30 }} /> : <HeartOutlined style={{ color: '#fff', fontSize: 30 }} />}
                  <span>{currentVideo.likes}</span>
                </div>
                <div className="side-btn"><MessageOutlined style={{ color: '#fff', fontSize: 28 }} /><span>{currentVideo.comments}</span></div>
                <div className="side-btn"><ShareAltOutlined style={{ color: '#fff', fontSize: 28 }} /><span>{currentVideo.shares}</span></div>
                <div className="music-disc-wrapper"><div className="music-disc-spin">🎵</div></div>
              </div>

              <div className="video-bottom">
                <div className="vb-username">@{currentVideo.username}{currentVideo.verified && <span className="v-badge">✓</span>}</div>
                <div className="vb-desc">{currentVideo.description}</div>
                <div className="vb-tags">{currentVideo.tags.map((tag, i) => <span key={i}>#{tag} </span>)}</div>
                <div className="vb-music"><span className="music-note">♪</span><span className="music-scroll">{currentVideo.music}</span></div>
              </div>

              <div className="video-progress-bar"><div className="video-progress-fill" style={{ width: `${progress}%` }}></div></div>

              {isDetecting && (
                <div className="ai-scanning">
                  <div className="scan-line"></div>
                  <div className="scan-corners"><div className="scan-corner tl"></div><div className="scan-corner tr"></div><div className="scan-corner bl"></div><div className="scan-corner br"></div></div>
                  <div className="scan-text"><span className="scan-pulse-dot"></span>{t(lang, 'aiScanning')}</div>
                </div>
              )}

              {showFullWarning && detectionResult && detectionResult.level !== 'safe' && (
                <div className={`full-screen-warning ${detectionResult.level}`} onClick={() => detectionResult.level === 'warning' && setShowFullWarning(false)}>
                  <div className="warning-overlay-content">
                    <div className="warning-icon-large">{detectionResult.level === 'danger' ? '🚨' : '⚠️'}</div>
                    <div className="warning-title-large">{detectionResult.level === 'danger' ? (lang==='zh'?'⚠️ 检测到高风险内容！':'⚠️ High Risk Detected!') : (lang==='zh'?'⚡ 内容存在可疑信息':'⚡ Suspicious Content')}</div>
                    <div className="warning-reasons">{(detectionResult.reasons||[]).slice(0,3).map((r,i) => <div key={i} className="warning-reason-item">• {r}</div>)}</div>
                    <div className="warning-suggestion-main">{lang==='zh'?'💡 请勿轻信，谨防诈骗！':'💡 Stay alert! Beware of scams!'}</div>
                    {alertSent === 'sent' && <div className="openclaw-status sent">✅ {lang==='zh'?'已通知家人（企业微信）':'Family notified'}</div>}
                    {alertSent === 'sending' && <div className="openclaw-status sending">📡 {lang==='zh'?'正在通知家人...':'Notifying family...'}</div>}
                    {detectionResult.level === 'danger' && <button className="warning-dismiss-btn" onClick={() => setShowFullWarning(false)}>{lang==='zh'?'我已知晓，继续观看':'I understand, continue'}</button>}
                  </div>
                </div>
              )}

              {alertSent && !showFullWarning && (
                <div className={`openclaw-badge ${alertSent}`}>
                  {alertSent === 'sent' && (lang==='zh'?'✅ 已推送企业微信':'✅ Sent to WeCom')}
                  {alertSent === 'sending' && (lang==='zh'?'📡 推送中...':'📡 Sending...')}
                  {alertSent === 'failed' && (lang==='zh'?'❌ 推送失败':'❌ Send failed')}
                </div>
              )}

              {detectionResult && !isDetecting && !showFullWarning && (
                <DetectionFloater result={detectionResult} onClose={() => setDetectionResult(null)} embedded={true} lang={lang} />
              )}
            </div>
          </div>

          <div className="bottom-nav">
            <div className="nav-item active"><span className="nav-icon">🏠</span><span className="nav-label">{t(lang, 'home')}</span></div>
            <div className="nav-item"><span className="nav-icon">🔍</span><span className="nav-label">{t(lang, 'discover')}</span></div>
            <div className="nav-item add-btn"><span>➕</span></div>
            <div className="nav-item"><span className="nav-icon">💬</span><span className="nav-label">{t(lang, 'messages')}</span></div>
            <div className="nav-item"><span className="nav-icon">👤</span><span className="nav-label">{t(lang, 'me')}</span></div>
          </div>
        </div>
        <div className="swipe-hint">{t(lang, 'swipeHint')} ({currentIndex + 1}/{mockVideos.length})</div>
      </div>

      {/* 右侧 AI 检测面板 */}
      <div className="detection-panel">
        <div className="panel-tabs">
          <button className={`panel-tab ${activeTab === 'phone' ? 'active' : ''}`} onClick={() => setActiveTab('phone')}>📱 {lang==='zh'?'实时检测':'Live Detection'}</button>
          <button className={`panel-tab ${activeTab === 'upload' ? 'active' : ''}`} onClick={() => setActiveTab('upload')}>📁 {lang==='zh'?'上传检测':'Upload'}</button>
        </div>

        {activeTab === 'phone' ? (
          <>
            <div className="panel-card">
              <div className="panel-header">
                <span className={`panel-dot ${isDetecting ? 'scanning' : ''}`}></span>
                {t(lang, 'aiRealTimeDetection')}
                {isDetecting && <span className="header-scan-badge">{lang==='zh'?'扫描中':'Scanning'}</span>}
              </div>
              <div className="panel-body">
                {isDetecting && <div className="scan-progress-bar"><div className="scan-progress-fill" style={{ width: `${scanProgress}%` }}></div><span className="scan-progress-text">{scanProgress}%</span></div>}

                {(isDetecting || liveExtractedLines.length > 0) && (
                  <div className="live-extract-section">
                    <div className="live-extract-header">
                      <span className="live-icon">📝</span>
                      {lang==='zh'?'提取的视频文本':'Extracted Text'}
                      {isDetecting && <span className="live-badge">{lang==='zh'?'实时':'LIVE'}</span>}
                    </div>
                    <div className="live-extract-box" ref={liveLogRef}>
                      {liveExtractedLines.map((line, i) => (
                        <div key={i} className={`extract-line ${i === liveHighlightIdx && isDetecting ? 'active' : 'done'}`}>
                          <span className="extract-idx">{String(i+1).padStart(2,'0')}</span>
                          <span className="extract-text">{renderHighlightedText(line)}</span>
                        </div>
                      ))}
                      {isDetecting && liveExtractedLines.length > 0 && <div className="extract-cursor">▊</div>}
                    </div>
                  </div>
                )}

                {analysisLog.length > 0 && (
                  <div className="analysis-live-log">
                    {analysisLog.map((log, i) => (
                      <div key={i} className={`log-line ${i === analysisLog.length - 1 && isDetecting ? 'active' : 'done'}`}>
                        {(i < analysisLog.length - 1 || !isDetecting) ? '✓' : '⏳'} {log}
                      </div>
                    ))}
                    {isDetecting && <div className="log-cursor">▊</div>}
                  </div>
                )}

                {detectionResult ? (
                  <div className="result-section fade-in">
                    <div className={`result-badge ${detectionResult.level}`}>
                      {detectionResult.level === 'danger' && t(lang, 'highRisk')}
                      {detectionResult.level === 'warning' && t(lang, 'caution')}
                      {detectionResult.level === 'safe' && t(lang, 'safe')}
                    </div>
                    <div className="result-score"><div className="score-bar"><div className={`score-fill ${detectionResult.level}`} style={{ width: `${(detectionResult.score??0)*100}%` }}></div></div><span className="score-num">{Math.round((detectionResult.score??0)*100)}/100</span></div>
                    <div className="result-reasons">{(detectionResult.reasons||[]).map((r,i) => <div key={i} className="reason-item">• {r}</div>)}</div>
                    <div className="result-suggestions">{(detectionResult.suggestions||[]).map((s,i) => <div key={i} className="suggestion-item">💡 {s}</div>)}</div>
                    <div className="result-meta">
                      {detectionResult.detection_method && <span className="detection-method-tag">{detectionResult.detection_method === 'ai_multimodal' ? '🤖 AI多模态' : detectionResult.detection_method === 'hybrid' ? '🤖+📋 混合' : detectionResult.detection_method === 'local_rule_engine' ? '📋 本地规则' : '🔍 检测'}</span>}
                      <span className="detection-time-tag">⏱️ {new Date().toLocaleTimeString(lang==='zh'?'zh-CN':'en-US',{hour:'2-digit',minute:'2-digit',second:'2-digit'})}</span>
                      {alertSent === 'sent' && <span className="openclaw-sent-tag">📡 {lang==='zh'?'OpenClaw已推送':'OpenClaw sent'}</span>}
                    </div>
                  </div>
                ) : !isDetecting ? (
                  <div className="panel-empty">{t(lang, 'waitingDetection')}</div>
                ) : null}
              </div>
            </div>

            <div className="panel-card">
              <div className="panel-header">{t(lang, 'detectionStats')}</div>
              <div className="panel-body">
                <div className="stat-grid">
                  <div className="stat-item"><div className="stat-num">{mockVideos.length}</div><div className="stat-label">{t(lang, 'totalVideos')}</div></div>
                  <div className="stat-item danger"><div className="stat-num">{mockVideos.filter(v => v.riskLevel === 'danger').length}</div><div className="stat-label">{t(lang, 'highRiskCount')}</div></div>
                  <div className="stat-item warning"><div className="stat-num">{mockVideos.filter(v => v.riskLevel === 'warning').length}</div><div className="stat-label">{t(lang, 'suspiciousCount')}</div></div>
                  <div className="stat-item safe"><div className="stat-num">{mockVideos.filter(v => v.riskLevel === 'safe').length}</div><div className="stat-label">{t(lang, 'safeCount')}</div></div>
                </div>
              </div>
            </div>

            <div className="panel-card tips-card">
              <div className="panel-header">{t(lang, 'antiScamTips')}</div>
              <div className="panel-body">
                <div className="tip-row">{t(lang, 'tip1')}</div>
                <div className="tip-row">{t(lang, 'tip2')}</div>
                <div className="tip-row">{t(lang, 'tip3')}</div>
                <div className="tip-row">{t(lang, 'tip4')}</div>
              </div>
            </div>
          </>
        ) : (
          <div className="panel-card"><div className="panel-body"><FileUpload onDetectionResult={onDetectionResult} lang={lang} /></div></div>
        )}
      </div>
    </div>
  );
};

export default MobileSimulator;
