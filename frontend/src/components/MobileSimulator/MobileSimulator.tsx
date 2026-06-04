import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import RiskAlertModal from '../RiskAlertModal/RiskAlertModal';
import RiskAlertDetailModal from '../RiskAlertDetailModal/RiskAlertDetailModal';
import AiGuardianIsland from '../AiGuardianIsland/AiGuardianIsland';
import AndroidGuardianFloat from '../AndroidGuardianFloat/AndroidGuardianFloat';
import { getRiskTier, triggerElderHaptic, VideoContext } from '../../utils/elderAlert';
import { SimulatorPlatform } from '../../utils/simulatorPlatform';
import FileUpload from '../FileUpload/FileUpload';
import DetectionService from '../../services/DetectionService';
import OpenClawService from '../../services/OpenClawService';
import { DetectionResult, VideoContent } from '../../types/detection';
import { Language, t, translateReason } from '../../i18n';
import DouyinPhoneUI from '../DouyinPhoneUI/DouyinPhoneUI';
import './MobileSimulator.css';

interface MobileSimulatorProps {
  onDetectionResult?: (result: DetectionResult) => void;
  lang: Language;
  competitionDemo?: boolean;
  simulatorPlatform?: SimulatorPlatform;
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
    // 粤语 / 香港常见诈骗话术
    '保證回報','冇風險','無風險','即刻','而家','限時','加我微信','加我WhatsApp',
    '轉數快','FPS','入數','匯款','包醫百病','祖傳秘方','唔好錯過','長者優惠',
];

async function demoVideoUrlToFile(url: string, videoId: number): Promise<File> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`demo video fetch ${res.status}`);
  const blob = await res.blob();
  return new File([blob], `factsafe-demo-${videoId}.mp4`, { type: blob.type || 'video/mp4' });
}

const MobileSimulator: React.FC<MobileSimulatorProps> = ({
  onDetectionResult,
  lang,
  competitionDemo = false,
  simulatorPlatform = 'ios',
}) => {
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

  // 上传视频在手机模拟器中播放
  const [uploadedVideoUrl, setUploadedVideoUrl] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [uploadWarning, setUploadWarning] = useState<DetectionResult | null>(null);
  const [showSimpleAlert, setShowSimpleAlert] = useState(false);
  const [showDetailAlert, setShowDetailAlert] = useState(false);
  const [alertSourceTitle, setAlertSourceTitle] = useState('');
  const [videoMuted, setVideoMuted] = useState(true);
  const [videoPaused, setVideoPaused] = useState(false);
  const [extractedAsr, setExtractedAsr] = useState('');
  const [extractedOcr, setExtractedOcr] = useState('');
  const isIOS = simulatorPlatform === 'ios';
  const demoVideoRef = useRef<HTMLVideoElement | null>(null);
  const uploadVideoRef = useRef<HTMLVideoElement | null>(null);
  const touchMovedRef = useRef(false);
  const [uploadAnalyzing, setUploadAnalyzing] = useState(false);
  const [uploadScanProgress, setUploadScanProgress] = useState(0);

  const detectionService = useRef(new DetectionService());
  const openClawService = useRef(new OpenClawService());
  const subtitleTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const liveLogRef = useRef<HTMLDivElement | null>(null);
  const lastDetectedIndex = useRef<number>(-1);
  const currentIndexRef = useRef(0);
  const mainAlertShownForIndex = useRef(-1);
  const userDismissedMainAlert = useRef(false);
  const notifySentForIndex = useRef(-1);

  useEffect(() => {
    if (competitionDemo) {
      setActiveTab('phone');
      setCurrentIndex(0);
    }
    lastDetectedIndex.current = -1;
  }, [competitionDemo]);

  const toggleVideoPlayPause = useCallback(() => {
    setVideoPaused((p) => !p);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const playDemoVideo = useCallback((index: number) => {
    lastDetectedIndex.current = -1;
    setCurrentIndex(index);
    setActiveTab('phone');
    setShowSimpleAlert(false);
    setShowDetailAlert(false);
    setUploadWarning(null);
  }, []);

  useEffect(() => {
    setProgress(0);
    const timer = setInterval(() => {
      setProgress(prev => prev >= 100 ? 0 : prev + 0.5);
    }, 150);
    return () => clearInterval(timer);
  }, [currentIndex]);

  const mockVideos: VideoContent[] = useMemo(() => [
    { id:1, username:lang==='zh'?'康健优选':'Health Select', avatar:'💊', title:lang==='zh'?'保健品微信私域推广':'Supplement WeChat Promotion', description:lang==='zh'?'声称调理慢病、限时优惠、引导加微信咨询':'Health supplement claims with WeChat contact', likes:'4.5万', comments:'6.7k', shares:'3.4k', music:lang==='zh'?'养生推广原声':'Wellness Promo Audio', verified:false, tags:lang==='zh'?['保健品','加微信','限时优惠']:['Supplement','WeChat','Limited Offer'], riskLevel:'danger' as const, content:'这个保健品专门适合中老年人，调理血糖血压，改善睡眠。名额有限，今天添加微信可以领取优惠，老师会一对一指导使用。不要再等医院排队，先加微信咨询，越早调理越好。', duration:35, thumbnail:'💊', videoUrl:'/demo-videos/health_supplement_wechat.mp4' },
    { id:2, username:lang==='zh'?'退休理财导师':'Retirement Finance Coach', avatar:'👨‍💼', title:lang==='zh'?'老人高收益理财项目':'High-return Investment for Seniors', description:lang==='zh'?'承诺保本高收益，制造紧迫感并诱导私下联系':'Guaranteed returns and private contact pressure', likes:'2.3万', comments:'895', shares:'1.2k', music:lang==='zh'?'财富自由原声':'Wealth Freedom Audio', verified:false, tags:lang==='zh'?['投资理财','保证收益','无风险']:['Investment','Guaranteed','No Risk'], riskLevel:'danger' as const, content:'各位叔叔阿姨，这是专门给退休人士的稳健项目，保证收益，无风险，月收益可以达到百分之三十。现在名额有限，今天加入还有内部福利，添加微信马上开始，错过就没有了。', duration:45, thumbnail:'📊', videoUrl:'/demo-videos/finance_scam_elder.mp4' },
    { id:3, username:lang==='zh'?'营养科普小站':'Nutrition Guide', avatar:'🥗', title:lang==='zh'?'正常营养科普视频':'Normal Nutrition Education', description:lang==='zh'?'均衡饮食、适量运动、建议咨询正规医生':'Balanced diet and evidence-based health advice', likes:'8.9万', comments:'2.1k', shares:'5.6k', music:lang==='zh'?'轻松科普原声':'Light Education Audio', verified:true, tags:lang==='zh'?['营养','科普','健康饮食']:['Nutrition','Education','Healthy Diet'], riskLevel:'safe' as const, content:'中老年朋友要注意饮食均衡，主食、蔬菜、蛋白质都要适量。保健品不能代替药物治疗，如果有糖尿病、高血压等慢性病，应该按医生建议定期复诊，不要轻信夸大宣传。', duration:40, thumbnail:'🥗', videoUrl:'/demo-videos/normal_nutrition.mp4' },
    { id:13, username:lang==='zh'?'官方旗舰店':'Official Flagship', avatar:'🛒', title:lang==='zh'?'直播间好物分享 小黄车下单':'Live shopping · cart link', description:lang==='zh'?'正品包邮、7天无理由，平台内购买':'Official store · platform checkout', likes:'12.6万', comments:'3.2k', shares:'8.1k', music:lang==='zh'?'带货 BGM':'Shopping BGM', verified:true, tags:lang==='zh'?['直播','小黄车','正品']:['Live','Cart','Official'], riskLevel:'safe' as const, content:'家人们好，今天直播间给大家带来的是官方旗舰店现货。限时优惠，点击小黄车或购物车链接下单，包邮到家，支持7天无理由。正品保障，有问题联系店铺客服，不要在私信里转账。', duration:38, thumbnail:'🛒', videoUrl:'/demo-videos/normal_nutrition.mp4' },
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

  const feedVideos = useMemo(() => {
    if (!competitionDemo) return mockVideos;
    const byId = (id: number) => mockVideos.find((v) => v.id === id)!;
    return [byId(1), byId(2), byId(13), byId(3)];
  }, [competitionDemo, mockVideos]);

  const safeIndex = competitionDemo
    ? Math.min(currentIndex, feedVideos.length - 1)
    : currentIndex;

  const currentVideo = feedVideos[safeIndex] ?? feedVideos[0];
  const subtitles = useMemo(() => splitSubtitles(currentVideo.content), [currentVideo.content]);

  useEffect(() => {
    setVideoPaused(false);
  }, [safeIndex, currentVideo.id]);

  useEffect(() => {
    const el = activeTab === 'upload' ? uploadVideoRef.current : demoVideoRef.current;
    if (!el) return;
    if (videoPaused) {
      el.pause();
    } else {
      void el.play().catch(() => { /* autoplay policy */ });
    }
  }, [videoPaused, currentVideo.id, currentVideo.videoUrl, activeTab, uploadedVideoUrl]);

  useEffect(() => {
    currentIndexRef.current = safeIndex;
  }, [safeIndex]);

  useEffect(() => {
    userDismissedMainAlert.current = false;
    mainAlertShownForIndex.current = -1;
    notifySentForIndex.current = -1;
    lastDetectedIndex.current = -1;
    setShowSimpleAlert(false);
    setShowDetailAlert(false);
    setExtractedAsr('');
    setExtractedOcr('');
  }, [safeIndex]);

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

  const pushFamilyAlert = useCallback(async (result: DetectionResult, title: string) => {
    const idx = currentIndexRef.current;
    if (notifySentForIndex.current === idx) return;
    openClawService.current.reloadConfig();
    if (!openClawService.current.shouldAlert(result)) return;
    notifySentForIndex.current = idx;
    setAlertSent('sending');
    try {
      const ok = await openClawService.current.sendAlert(result, title);
      setAlertSent(ok ? 'sent' : 'failed');
    } catch {
      setAlertSent('failed');
    }
    setTimeout(() => setAlertSent(null), 6000);
  }, []);

  const openRiskAlert = useCallback((result: DetectionResult, title: string, opts?: { allowReshow?: boolean }) => {
    if (result.level === 'safe') return;
    const idx = currentIndexRef.current;
    setDetectionResult(result);
    setAlertSourceTitle(title);
    setShowDetailAlert(false);

    const tier = getRiskTier(result);
    const alreadyShown = mainAlertShownForIndex.current === idx;

    if (tier === 'high' && !userDismissedMainAlert.current && (!alreadyShown || opts?.allowReshow)) {
      mainAlertShownForIndex.current = idx;
      setShowSimpleAlert(true);
      triggerElderHaptic();
    } else if (!alreadyShown) {
      setShowSimpleAlert(false);
    }

    void pushFamilyAlert(result, title);
  }, [pushFamilyAlert]);

  const applyFusedResult = useCallback((fused: DetectionResult, title: string) => {
    setDetectionResult(fused);
    const tier = getRiskTier(fused);
    const idx = currentIndexRef.current;
    const alreadyShown = mainAlertShownForIndex.current === idx;
    if (
      tier === 'high'
      && !userDismissedMainAlert.current
      && !alreadyShown
      && (fused.level === 'danger' || fused.level === 'warning')
    ) {
      mainAlertShownForIndex.current = idx;
      setShowSimpleAlert(true);
      triggerElderHaptic();
      void pushFamilyAlert(fused, title);
    }
  }, [pushFamilyAlert]);

  const openMainElderAlert = useCallback(() => {
    if (!detectionResult || isDetecting) return;
    userDismissedMainAlert.current = false;
    if (detectionResult.level === 'safe') {
      setShowSimpleAlert(false);
      setShowDetailAlert(true);
      return;
    }
    setShowDetailAlert(false);
    setShowSimpleAlert(true);
    triggerElderHaptic();
  }, [detectionResult, isDetecting]);

  const openUploadElderAlert = useCallback(() => {
    if (!uploadWarning || uploadAnalyzing) return;
    userDismissedMainAlert.current = false;
    setDetectionResult(uploadWarning);
    setAlertSourceTitle(uploadedFileName || (lang === 'en' ? 'Uploaded Video' : '上传视频'));
    if (uploadWarning.level === 'safe') {
      setShowSimpleAlert(false);
      setShowDetailAlert(true);
      return;
    }
    setShowDetailAlert(false);
    setShowSimpleAlert(true);
    triggerElderHaptic();
  }, [uploadWarning, uploadAnalyzing, uploadedFileName, lang]);

  const openGuardianAlert = useCallback(() => {
    if (activeTab === 'upload') openUploadElderAlert();
    else openMainElderAlert();
  }, [activeTab, openUploadElderAlert, openMainElderAlert]);

  const detectContent = useCallback(async (video: VideoContent) => {
    setIsDetecting(true);
    setDetectionResult(null);
    setAlertSent(null);
    setShowFullWarning(false);
    setAnalysisLog([]);
    setLiveExtractedLines([]);
    setLiveHighlightIdx(-1);
    setScanProgress(0);

    const phases = lang !== 'en'
      ? [
          { text: '📡 连接AI检测引擎...', delay: 400 },
          { text: '📝 提取视频语音字幕...', delay: 200 },
          { text: '🤖 MacBERT 中文语义编码...', delay: 500 },
          { text: '🔍 OCR 画面文案 + ASR 口播对齐...', delay: 400 },
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

    const showPhases = async (subtitleSource: string) => {
      const phaseSubs = splitSubtitles(subtitleSource);
      setLiveExtractedLines([]);
      setAnalysisLog([phases[0].text]);
      await new Promise(r => setTimeout(r, phases[0].delay));
      setAnalysisLog(prev => [...prev, phases[1].text]);
      const lineDelay = Math.max(150, 1200 / Math.max(phaseSubs.length, 1));
      for (let i = 0; i < phaseSubs.length; i++) {
        setLiveExtractedLines((prev) => [...prev, phaseSubs[i]]);
        setLiveHighlightIdx(i);
        setScanProgress(Math.round(((i + 1) / phaseSubs.length) * 30));
        await new Promise(r => setTimeout(r, lineDelay));
      }
      for (let i = 2; i < phases.length; i++) {
        setAnalysisLog(prev => [...prev, phases[i].text]);
        setScanProgress(30 + Math.round(((i - 1) / (phases.length - 2)) * 70));
        await new Promise(r => setTimeout(r, phases[i].delay));
      }
      setScanProgress(100);
    };

    const fallbackOcr = `${video.title} ${video.description}`.trim();

    try {
      let result: DetectionResult;
      let asrForCtx = video.content;
      let ocrForCtx = fallbackOcr;

      if (video.videoUrl) {
        setAnalysisLog([phases[0].text]);
        await new Promise(r => setTimeout(r, phases[0].delay));
        setAnalysisLog(prev => [
          ...prev,
          lang !== 'en'
            ? '🎬 上传演示视频 · Whisper 语音转写 + EasyOCR 画面文字...'
            : '🎬 Uploading demo · Whisper ASR + EasyOCR...',
        ]);
        setScanProgress(8);
        try {
          const file = await demoVideoUrlToFile(video.videoUrl, video.id);
          result = await detectionService.current.detectVideo(
            file,
            fallbackOcr,
          );
          asrForCtx = (result.transcript || '').trim() || video.content;
          ocrForCtx = (result.ocr_text || '').trim() || fallbackOcr;
          setExtractedAsr(asrForCtx);
          setExtractedOcr(ocrForCtx);
          if (asrForCtx) {
            setAnalysisLog(prev => [
              ...prev,
              lang !== 'en'
                ? `📝 ASR 口播（${asrForCtx.length} 字）`
                : `📝 ASR transcript (${asrForCtx.length} chars)`,
            ]);
          }
          if (result.ocr_text) {
            setAnalysisLog(prev => [
              ...prev,
              lang !== 'en'
                ? `🔍 OCR 画面（${ocrForCtx.length} 字）`
                : `🔍 OCR on-screen (${ocrForCtx.length} chars)`,
            ]);
          }
          await showPhases(asrForCtx);
        } catch (mediaErr) {
          console.warn('[MobileSimulator] 视频 ASR/OCR 失败，回退脚本文案:', mediaErr);
          setAnalysisLog(prev => [
            ...prev,
            lang !== 'en' ? '⚠️ 视频提取失败，使用演示脚本继续检测' : '⚠️ Media extract failed, using script',
          ]);
          const [textResult] = await Promise.all([
            detectionService.current.detectVideoContent({
              asrText: video.content,
              ocrText: fallbackOcr,
              title: video.title,
            }),
            showPhases(video.content),
          ]);
          result = textResult;
          asrForCtx = video.content;
          ocrForCtx = fallbackOcr;
        }
      } else {
        const [textResult] = await Promise.all([
          detectionService.current.detectVideoContent({
            asrText: video.content,
            ocrText: fallbackOcr,
            title: video.title,
          }),
          showPhases(video.content),
        ]);
        result = textResult;
      }

      const videoCtx: VideoContext = {
        title: video.title,
        description: video.description,
        content: asrForCtx,
        ocrText: ocrForCtx,
      };
      const fullText = `${ocrForCtx} ${asrForCtx}`.trim();

      setAnalysisLog(prev => [...prev, lang !== 'en' ? '✅ 检测完成' : '✅ Detection complete']);
      onDetectionResult?.(result);
      setShowFullWarning(false);

      if (result.level === 'danger' || result.level === 'warning') {
        openRiskAlert(result, video.title);
      } else {
        setDetectionResult(result);
        setShowSimpleAlert(false);
        setShowDetailAlert(false);
      }

      console.log('[MobileSimulator] 检测结果:', { level: result.level, score: result.score });

      // ★ 异步 GPT 事实核查（后台进行，不阻塞 UI）
      if (fullText.trim().length > 10) {
        setAnalysisLog(prev => [...prev, lang !== 'en' ? '🔍 GPT 深度事实核查中...' : '🔍 GPT deep fact-checking...']);
        detectionService.current
          .factCheck(fullText, `视频: ${video.title}`, result)
          .then((gpt) => {
            if (gpt && !(gpt as any).fallback) {
              const zh = lang !== 'en';
              const gptVerdict = gpt.verdict;
              let fusedLevel = result.level;
              let fusedScore = result.score ?? 0;

              if (gptVerdict === 'false' || gpt.risk_level === 'danger') {
                fusedLevel = 'danger';
                fusedScore = Math.max(fusedScore, 0.75);
              } else if (gptVerdict === 'misleading' || gpt.risk_level === 'warning') {
                if (fusedLevel === 'safe') fusedLevel = 'warning';
                fusedScore = Math.max(fusedScore, 0.5);
              }

              // 融合 GPT reasons
              const gptReasons: string[] = [];
              if (gpt.summary) gptReasons.push(`GPT: ${gpt.summary}`);
              if (gpt.false_claims && gpt.false_claims.length > 0) {
                gpt.false_claims.forEach((c: any) => gptReasons.push(`❌ ${c.original} → ✅ ${c.correction}`));
              }
              if (gpt.related_scam_type && gpt.related_scam_type !== '无') {
                gptReasons.push(`${zh ? '诈骗类型' : 'Scam type'}: ${gpt.related_scam_type}`);
              }

              const fusedResult: DetectionResult = {
                ...result,
                level: fusedLevel as 'safe' | 'warning' | 'danger',
                score: fusedScore,
                reasons: [...gptReasons, ...(result.reasons || [])],
                suggestions: [...(gpt.safety_advice || []), ...(result.suggestions || [])],
              };

              if (fusedLevel === 'danger' || fusedLevel === 'warning') {
                applyFusedResult(fusedResult, video.title);
              } else {
                setDetectionResult(fusedResult);
              }

              const verdictLabel = gptVerdict === 'false' ? (zh ? '❌ 虚假' : '❌ False')
                : gptVerdict === 'misleading' ? (zh ? '⚠️ 误导' : '⚠️ Misleading')
                : gptVerdict === 'true' ? (zh ? '✅ 属实' : '✅ True')
                : (zh ? '❓ 待核实' : '❓ Unverifiable');

              setAnalysisLog(prev => [
                ...prev,
                `✅ GPT: ${verdictLabel} (${gpt.gpt_latency || '?'}s)`,
                `━━ ${zh ? '最终综合判定' : 'Final verdict'}: ${
                  fusedLevel === 'danger' ? '🚨' : fusedLevel === 'warning' ? '⚠️' : '✅'
                } ${Math.round(fusedScore * 100)}/100 ━━`,
              ]);
            }
          })
          .catch(() => { /* 静默失败 */ });
      }
    } catch (error) {
      console.error('Detection failed:', error);
      setAnalysisLog(prev => [...prev, lang !== 'en' ? '❌ 检测异常' : '❌ Detection error']);
    } finally {
      setIsDetecting(false);
    }
  }, [onDetectionResult, lang, openRiskAlert, applyFusedResult]);

  useEffect(() => {
    // 只在切换到新视频时触发检测，当前视频不重复检测
    if (lastDetectedIndex.current === safeIndex) return;
    lastDetectedIndex.current = safeIndex;
    const timer = setTimeout(() => detectContent(currentVideo), 600);
    return () => clearTimeout(timer);
  }, [safeIndex, currentVideo, detectContent, competitionDemo]);

  useEffect(() => {
    if (liveLogRef.current) liveLogRef.current.scrollTop = liveLogRef.current.scrollHeight;
  }, [liveExtractedLines, analysisLog]);

  const handleTouchStart = (e: React.TouchEvent | React.MouseEvent) => {
    touchMovedRef.current = false;
    const y = 'touches' in e ? e.touches[0].clientY : e.clientY;
    setTouchStart(y);
    setTranslateY(0);
  };
  const handleTouchMove = (e: React.TouchEvent | React.MouseEvent) => {
    if (!touchStart) return;
    const y = 'touches' in e ? e.touches[0].clientY : e.clientY;
    const delta = touchStart - y;
    if (Math.abs(delta) > 8) touchMovedRef.current = true;
    setTranslateY(Math.max(-100, Math.min(100, delta)));
  };
  const goToVideo = useCallback((n: number) => {
    if (n < 0 || n >= feedVideos.length) return;
    setIsTransitioning(true);
    setTimeout(() => {
      setCurrentIndex(n);
      setIsTransitioning(false);
    }, 200);
  }, [feedVideos.length]);

  const handleTouchEnd = () => {
    if (activeTab === 'phone' && !competitionDemo && Math.abs(translateY) > 50) {
      const d = translateY > 0 ? 1 : -1;
      goToVideo(safeIndex + d);
    } else if (!touchMovedRef.current) {
      if (activeTab === 'upload' && uploadedVideoUrl) toggleVideoPlayPause();
      else if (activeTab === 'phone' && currentVideo.videoUrl) toggleVideoPlayPause();
    }
    setTranslateY(0);
    setTouchStart(0);
    touchMovedRef.current = false;
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') goToVideo(safeIndex + 1);
      if (e.key === 'ArrowUp') goToVideo(safeIndex - 1);
      if (e.key === ' ') {
        const hasVideo = (activeTab === 'upload' && uploadedVideoUrl)
          || (activeTab === 'phone' && currentVideo.videoUrl);
        if (hasVideo) {
          e.preventDefault();
          toggleVideoPlayPause();
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [safeIndex, goToVideo, competitionDemo, currentVideo.videoUrl, activeTab, uploadedVideoUrl, toggleVideoPlayPause]);

  const handleLike = (id: number) => { setLikedVideos(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; }); };
  const formatTime = (d: Date) => d.toLocaleTimeString(lang !== 'en' ? 'zh-CN' : 'en-US', { hour: '2-digit', minute: '2-digit' });
  const ui = (zh: string, en: string) => (lang === 'en' ? en : zh);

  const stopWatchingAndNext = () => {
    document.querySelectorAll<HTMLVideoElement>('.phone-frame video').forEach((video) => {
      video.pause();
      video.currentTime = 0;
    });
    setShowFullWarning(false);
    setShowSimpleAlert(false);
    setShowDetailAlert(false);
    setUploadWarning(null);
    setDetectionResult(null);
    setActiveTab('phone');
    setIsTransitioning(true);
    setTimeout(() => {
      goToVideo((safeIndex + 1) % feedVideos.length);
      setIsTransitioning(false);
    }, 180);
  };

  const guardianResult = activeTab === 'upload' ? uploadWarning : detectionResult;
  const guardianDetecting = activeTab === 'upload' ? uploadAnalyzing : isDetecting;
  const guardianScanProgress = activeTab === 'upload' ? uploadScanProgress : scanProgress;
  const islandMode = guardianDetecting ? 'scanning' as const : guardianResult ? 'result' as const : 'idle' as const;
  const currentRiskTier = guardianResult ? getRiskTier(guardianResult) : 'low';

  const phoneVideoContext: VideoContext = {
    title: currentVideo.title,
    description: currentVideo.description,
    content: extractedAsr || currentVideo.content,
    ocrText: extractedOcr || `${currentVideo.title} ${currentVideo.description}`.trim(),
  };

  const elderAlertLayer = (source: 'phone' | 'upload') => {
    const activeResult = source === 'upload' ? uploadWarning : detectionResult;
    if (!activeResult) return null;
    const showMain = activeResult.level !== 'safe' && (
      source === 'upload'
        ? (showSimpleAlert && !!uploadWarning)
        : (showSimpleAlert && activeTab !== 'upload')
    );
    const showDetail = source === 'upload'
      ? showDetailAlert && !!uploadWarning
      : (showDetailAlert && activeTab !== 'upload');
    if (!showMain && !showDetail) return null;

    return (
      <>
        <RiskAlertModal
          visible={showMain}
          level={activeResult.level === 'danger' ? 'danger' : 'warning'}
          lang={lang}
          onStopWatching={stopWatchingAndNext}
          onDismiss={() => {
            userDismissedMainAlert.current = true;
            setShowSimpleAlert(false);
          }}
          onViewDetails={() => {
            setShowSimpleAlert(false);
            setShowDetailAlert(true);
            if (source === 'upload') setDetectionResult(uploadWarning);
          }}
        />
        <RiskAlertDetailModal
          visible={showDetail}
          result={activeResult}
          lang={lang}
          videoContext={
            source === 'upload'
              ? {
                  title: uploadedFileName || '上传视频',
                  description: '',
                  content: uploadWarning?.merged_text || uploadWarning?.transcript || '',
                  ocrText: uploadWarning?.ocr_text || uploadedFileName,
                }
              : phoneVideoContext
          }
          onTellFamily={() => {
            void pushFamilyAlert(activeResult, alertSourceTitle || uploadedFileName);
          }}
          onGotIt={() => setShowDetailAlert(false)}
          onBack={() => {
            setShowDetailAlert(false);
            setShowSimpleAlert(true);
          }}
        />
      </>
    );
  };

  const displayTime = competitionDemo
    ? currentTime.toLocaleTimeString(lang === 'en' ? 'en-GB' : 'zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      })
    : formatTime(currentTime);

  const douyinTabbar = (
    <nav className="douyin-tabbar" aria-label="main">
      <div className="tb-item active"><span className="tb-icon">🏠</span><span>{lang === 'en' ? 'Home' : '首页'}</span></div>
      <div className="tb-item"><span className="tb-icon">👥</span><span>{lang === 'en' ? 'Friends' : '朋友'}</span><em className="tb-badge">3</em></div>
      <div className="tb-add">+</div>
      <div className="tb-item"><span className="tb-icon">💬</span><span>{lang === 'en' ? 'Inbox' : '消息'}</span><em className="tb-badge">4</em></div>
      <div className="tb-item"><span className="tb-icon">👤</span><span>{lang === 'en' ? 'Me' : '我'}</span></div>
    </nav>
  );

  const islandNode = isIOS ? (
    <AiGuardianIsland
      mode={islandMode}
      result={guardianResult}
      riskTier={currentRiskTier}
      isDetecting={guardianDetecting}
      scanProgress={guardianScanProgress}
      lang={lang}
      onOpenMainAlert={openGuardianAlert}
    />
  ) : null;

  const gradients = [
    'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
    'linear-gradient(135deg, #2d1b3d 0%, #1a1a2e 50%, #16213e 100%)',
    'linear-gradient(135deg, #0f3460 0%, #16213e 50%, #1a1a2e 100%)',
    'linear-gradient(135deg, #1b2a4a 0%, #12243a 50%, #0a1628 100%)',
    'linear-gradient(135deg, #2a1a3e 0%, #1a1a2e 50%, #0f2460 100%)',
    'linear-gradient(135deg, #1e3a2f 0%, #162e20 50%, #0f2018 100%)',
  ];

  return (
    <div className={`simulator-page ${competitionDemo ? 'competition-demo douyin-feed' : ''}`}>
      <div className="phone-stage">
        <div className={`phone-wrapper ${competitionDemo ? 'competition-phone-only' : ''}`}>
        {!competitionDemo && (
          <div className="phone-model-label">
            {isIOS ? 'iPhone · FactSafe' : 'Android · FactSafe'}
          </div>
        )}
        <div className={`${isIOS ? 'iphone-chassis' : 'android-chassis'} ${competitionDemo ? 'competition-chassis black-frame' : ''}`}>
          {isIOS && (
            <>
              <div className="iphone-side-btn iphone-side-l1" aria-hidden />
              <div className="iphone-side-btn iphone-side-l2" aria-hidden />
              <div className="iphone-side-btn iphone-side-r" aria-hidden />
            </>
          )}
        <div className={`phone-frame ${isIOS ? '' : 'android-inner'} ${competitionDemo ? 'douyin-screen' : ''}`}>
          {(() => {
            const feedViewport = (
          <div
            className={`video-viewport ${competitionDemo ? 'douyin-feed-viewport' : ''}`}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
            onMouseDown={handleTouchStart}
            onMouseMove={(e) => touchStart && handleTouchMove(e)}
            onMouseUp={handleTouchEnd}
            onMouseLeave={handleTouchEnd}
          >

            {/* ===== 上传视频播放模式 ===== */}
            {activeTab === 'upload' && uploadedVideoUrl ? (
              <div className="video-slide" style={{ background: '#000' }}>
                <video
                  ref={uploadVideoRef}
                  className="uploaded-video-player"
                  src={uploadedVideoUrl}
                  playsInline
                  autoPlay={!videoPaused}
                  muted={videoMuted}
                  loop
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                />
                <button
                  type="button"
                  className={`video-play-pause-btn ${videoPaused ? 'paused' : ''}`}
                  aria-label={videoPaused ? (lang === 'en' ? 'Play' : '播放') : (lang === 'en' ? 'Pause' : '暂停')}
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleVideoPlayPause();
                  }}
                >
                  {videoPaused ? '▶' : '⏸'}
                </button>
                <button
                  type="button"
                  className={`sound-btn-mini ${videoMuted ? 'muted' : 'on'}`}
                  aria-label={videoMuted ? (lang === 'en' ? 'Unmute' : '开启声音') : (lang === 'en' ? 'Mute' : '关闭声音')}
                  onClick={(e) => {
                    e.stopPropagation();
                    const video = uploadVideoRef.current;
                    if (video) {
                      video.muted = !video.muted;
                      setVideoMuted(video.muted);
                    }
                  }}
                >
                  {videoMuted ? '🔇' : '🔊'}
                </button>

                <div className="video-top-bar">
                  <span className="top-tab">{t(lang, 'follow')}</span>
                  <span className="top-tab active">{t(lang, 'recommend')}</span>
                </div>

                <div className="video-bottom">
                  <div className="vb-username">@{ui('上传视频', 'Uploaded Video')}</div>
                  <div className="vb-desc">{uploadedFileName}</div>
                </div>

                {!isIOS && (
                  <AndroidGuardianFloat
                    mode={uploadAnalyzing ? 'scanning' : uploadWarning ? 'result' : 'idle'}
                    result={uploadWarning}
                    riskTier={uploadWarning ? getRiskTier(uploadWarning) : 'low'}
                    isDetecting={uploadAnalyzing}
                    lang={lang}
                    onOpenAlert={openUploadElderAlert}
                  />
                )}
                {elderAlertLayer('upload')}
              </div>
            ) : activeTab === 'upload' && !uploadedVideoUrl ? (
              <div className="video-slide" style={{ background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'rgba(255,255,255,0.4)' }}>
                  <span style={{ fontSize: 48 }}>📤</span>
                  <p style={{ fontSize: 14, marginTop: 12 }}>{ui('请在右侧上传视频', 'Upload a video on the right')}</p>
                </div>
              </div>
            ) : (
            /* ===== 原有模拟视频播放模式 / 真实视频 Demo ===== */
            <div className={`video-slide ${isTransitioning ? 'transitioning' : ''}`} style={{ background: gradients[currentIndex % gradients.length] }}>
              {currentVideo.videoUrl ? (
                <>
                  <video
                    key={currentVideo.id}
                    ref={demoVideoRef}
                    className="demo-video-player"
                    src={currentVideo.videoUrl}
                    playsInline
                    autoPlay={!videoPaused}
                    muted={videoMuted}
                    loop
                    preload="metadata"
                  />
                  <div className="demo-video-shade" />
                  {currentVideo.videoUrl && (
                    <button
                      type="button"
                      className={`video-play-pause-btn ${videoPaused ? 'paused' : ''}`}
                      aria-label={videoPaused ? (lang === 'en' ? 'Play' : '播放') : (lang === 'en' ? 'Pause' : '暂停')}
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleVideoPlayPause();
                      }}
                    >
                      {videoPaused ? '▶' : '⏸'}
                    </button>
                  )}
                  <button
                    type="button"
                    className={`sound-btn-mini ${videoMuted ? 'muted' : 'on'}`}
                    aria-label={videoMuted ? (lang === 'en' ? 'Unmute' : '开启声音') : (lang === 'en' ? 'Mute' : '关闭声音')}
                    onClick={(e) => {
                      e.stopPropagation();
                      const video = e.currentTarget.parentElement?.querySelector('video.demo-video-player') as HTMLVideoElement | null;
                      if (video) {
                        video.muted = !video.muted;
                        setVideoMuted(video.muted);
                      }
                    }}
                  >
                    {videoMuted ? '🔇' : '🔊'}
                  </button>
                </>
              ) : (
                <div className="video-center-icon">{currentVideo.thumbnail}</div>
              )}

              {/* ===== 动态字幕 ===== */}
              <div className="video-subtitle-area">
                <div className={`video-subtitle ${subtitleVisible ? 'show' : 'hide'}`}>
                  {subtitles[currentSubtitleIdx]}
                </div>
              </div>

              {!competitionDemo && (
                <div className="video-top-bar">
                  <span className="top-tab">{t(lang, 'follow')}</span>
                  <span className="top-tab active">{t(lang, 'recommend')}</span>
                </div>
              )}

              <div className="side-actions">
                <div className="side-avatar">
                  <div className="avatar-circle">{currentVideo.avatar}</div>
                  {!currentVideo.verified && <div className="follow-badge">+</div>}
                </div>
                <div className="side-btn" onClick={() => handleLike(currentVideo.id)}>
                  <span style={{ fontSize: 28 }}>{likedVideos.has(currentVideo.id) ? '❤️' : '🤍'}</span>
                  <span>{currentVideo.likes}</span>
                </div>
                <div className="side-btn"><span style={{ fontSize: 26 }}>💬</span><span>{currentVideo.comments}</span></div>
                {competitionDemo ? (
                  <div className="side-btn"><span style={{ fontSize: 26 }}>⭐</span><span>1.5万</span></div>
                ) : null}
                <div className="side-btn"><span style={{ fontSize: 26 }}>↗️</span><span>{currentVideo.shares}</span></div>
                <div className="music-disc-wrapper">
                  <div className="music-disc-spin">{competitionDemo ? '🎵' : '🎵'}</div>
                  {competitionDemo && <span className="same-style-label">{lang === 'en' ? 'Use sound' : '拍同款'}</span>}
                </div>
              </div>

              {competitionDemo ? (
                <div className="douyin-meta-bottom">
                  <div className="dm-user">
                    <span className="douyin-danmu">弹</span>
                    @{currentVideo.username}
                    {currentVideo.verified && <span className="v-badge"> ✓</span>}
                  </div>
                  <div className="dm-desc">
                    {currentVideo.description}
                    {' '}
                    <span className="dm-expand">{lang === 'en' ? 'more' : '展开'}</span>
                  </div>
                </div>
              ) : (
                <div className="video-bottom">
                  <div className="vb-username">@{currentVideo.username}{currentVideo.verified && <span className="v-badge">✓</span>}</div>
                  <div className="vb-desc">{currentVideo.description}</div>
                  <div className="vb-tags">{currentVideo.tags.map((tag, i) => <span key={i}>#{tag} </span>)}</div>
                  <div className="vb-music"><span className="music-note">♪</span><span className="music-scroll">{currentVideo.music}</span></div>
                </div>
              )}

              <div className="video-progress-bar"><div className="video-progress-fill" style={{ width: `${progress}%` }}></div></div>

              {guardianDetecting && activeTab === 'phone' && (
                <div className="ai-check-island competition-scan-hud" aria-live="polite">
                  <div className="ai-check-dot" />
                  <div className="ai-check-copy">
                    <div className="ai-check-title">{ui('AI 正在检查', 'AI checking')}</div>
                    <div className="ai-check-stage">
                      {analysisLog[analysisLog.length - 1]?.replace(/^[^\w\u4e00-\u9fff]+\s*/, '') || t(lang, 'aiScanning')}
                    </div>
                  </div>
                  <div className="ai-check-percent">{scanProgress}%</div>
                </div>
              )}

              {guardianDetecting && activeTab === 'upload' && (
                <div className="ai-check-island competition-scan-hud" aria-live="polite">
                  <div className="ai-check-dot" />
                  <div className="ai-check-copy">
                    <div className="ai-check-title">{ui('AI 正在检查', 'AI checking')}</div>
                    <div className="ai-check-stage">
                      {lang === 'en' ? 'Upload · ASR + OCR' : '上传视频 · 语音+画面识别'}
                    </div>
                  </div>
                  <div className="ai-check-percent">{uploadScanProgress}%</div>
                </div>
              )}

              {!guardianDetecting && guardianResult && activeTab === 'phone' && (
                <div className={`competition-result-chip ${guardianResult.level}`} aria-live="polite">
                  {guardianResult.level === 'danger' && ui('高风险', 'High risk')}
                  {guardianResult.level === 'warning' && ui('需注意', 'Caution')}
                  {guardianResult.level === 'safe' && ui('暂未发现风险', 'Looks safe')}
                  {' · '}
                  {Math.round((guardianResult.score ?? 0) * 100)}
                  {lang === 'en' ? ' pts' : '分'}
                  {guardianResult.detection_method && (
                    <span className="chip-method">
                      {' · '}
                      {guardianResult.detection_method.includes('video') ? 'ASR+OCR+AI' : 'AI'}
                    </span>
                  )}
                </div>
              )}

              {!isIOS && activeTab === 'phone' && (
                <AndroidGuardianFloat
                  mode={islandMode}
                  result={detectionResult}
                  riskTier={detectionResult ? getRiskTier(detectionResult) : 'low'}
                  isDetecting={isDetecting}
                  lang={lang}
                  onOpenAlert={openMainElderAlert}
                />
              )}

              {competitionDemo && alertSent && (
                <div className={`feishu-toast-inphone ${alertSent}`}>
                  {alertSent === 'sent' && `✅ ${t(lang, 'alertSentFeishu')}`}
                  {alertSent === 'sending' && `📡 ${t(lang, 'alertSending')}`}
                  {alertSent === 'failed' && `❌ ${t(lang, 'alertFailed')}`}
                </div>
              )}

              {alertSent && !competitionDemo && (
                <div className={`openclaw-badge ${alertSent}`}>
                  {alertSent === 'sent' && `✅ ${t(lang, 'alertSentFeishu')}`}
                  {alertSent === 'sending' && `📡 ${t(lang, 'alertSending')}`}
                  {alertSent === 'failed' && `❌ ${t(lang, 'alertFailed')}`}
                </div>
              )}

              {elderAlertLayer('phone')}

              {competitionDemo && (
                <div className="douyin-key-hint" aria-hidden>
                  ↑↓ {lang === 'en' ? 'switch' : '切视频'}
                  {' · '}
                  {lang === 'en' ? 'Space tap ⏸' : '空格/点按 ⏸'}
                </div>
              )}
            </div>
            )}
          </div>
            );
            if (competitionDemo && isIOS) {
              return (
                <DouyinPhoneUI
                  lang={lang}
                  timeLabel={displayTime}
                  islandSlot={islandNode}
                  bottomBar={douyinTabbar}
                >
                  {feedViewport}
                </DouyinPhoneUI>
              );
            }
            return (
              <>
                {!competitionDemo && (
                  <div className="status-bar">
                    <span className="sb-time">{formatTime(currentTime)}</span>
                    {isIOS ? islandNode : <div className="sb-island sb-island-android" />}
                    <div className="sb-right">
                      <span>{isIOS ? '📶' : '4G'}</span>
                      <span>{isIOS ? 'WiFi' : '🔋'}</span>
                      <span>{isIOS ? '85%' : '78%'}</span>
                    </div>
                  </div>
                )}
                {feedViewport}
                {!competitionDemo && (
                  <div className="bottom-nav">
                    <div className="nav-item active"><span className="nav-icon">🏠</span><span className="nav-label">{t(lang, 'home')}</span></div>
                    <div className="nav-item"><span className="nav-icon">🔍</span><span className="nav-label">{t(lang, 'discover')}</span></div>
                    <div className="nav-item add-btn"><span>➕</span></div>
                    <div className="nav-item"><span className="nav-icon">💬</span><span className="nav-label">{t(lang, 'messages')}</span></div>
                    <div className="nav-item"><span className="nav-icon">👤</span><span className="nav-label">{t(lang, 'me')}</span></div>
                  </div>
                )}
                {competitionDemo && !isIOS && (
                  <div className="douyin-tabbar-android-wrap">{douyinTabbar}</div>
                )}
              </>
            );
          })()}
        </div>
        </div>
        </div>
        {!competitionDemo && (
          <div className="swipe-hint">{t(lang, 'swipeHint')} ({currentIndex + 1}/{mockVideos.length})</div>
        )}
        {!competitionDemo && (
          <div className="demo-video-switcher">
            <button className={currentIndex === 0 ? 'active danger' : ''} onClick={() => playDemoVideo(0)}>{t(lang, 'demoHealth')}</button>
            <button className={currentIndex === 1 ? 'active danger' : ''} onClick={() => playDemoVideo(1)}>{t(lang, 'demoFinance')}</button>
            <button className={currentIndex === 2 ? 'active safe' : ''} onClick={() => playDemoVideo(2)}>{t(lang, 'demoSafe')}</button>
          </div>
        )}
      </div>

      {!competitionDemo && (
      <div className="detection-panel">
        {!competitionDemo && (
          <div className="panel-tabs">
            <button className={`panel-tab ${activeTab === 'phone' ? 'active' : ''}`} onClick={() => setActiveTab('phone')}>📱 {t(lang, 'panelLiveDetection')}</button>
            <button className={`panel-tab ${activeTab === 'upload' ? 'active' : ''}`} onClick={() => setActiveTab('upload')}>📁 {t(lang, 'panelUpload')}</button>
          </div>
        )}

        {competitionDemo && (
          <div className="panel-demo-badge">
            <span>🎯 {t(lang, 'competitionDemo')}</span>
            <span className="sensitivity-lock">{lang === 'en' ? 'Precision (low FP)' : '宁漏勿误 · 已锁定'}</span>
          </div>
        )}

        {(competitionDemo || activeTab === 'phone') ? (
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
                    <div className="result-reasons">{(detectionResult.reasons||[]).map((r,i) => <div key={i} className="reason-item">• {translateReason(lang, r)}</div>)}</div>
                    <div className="result-suggestions">{(detectionResult.suggestions||[]).map((s,i) => <div key={i} className="suggestion-item">💡 {translateReason(lang, s)}</div>)}</div>
                    <div className="result-meta">
                      {detectionResult.detection_method && <span className="detection-method-tag">{detectionResult.detection_method === 'ai_multimodal' ? '🤖 AI多模态' : detectionResult.detection_method === 'hybrid' ? '🤖+📋 混合' : detectionResult.detection_method === 'local_rule_engine' ? '📋 本地规则' : '🔍 检测'}</span>}
                      <span className="detection-time-tag">⏱️ {new Date().toLocaleTimeString(lang==='zh'?'zh-CN':'en-US',{hour:'2-digit',minute:'2-digit',second:'2-digit'})}</span>
                      {alertSent === 'sent' && <span className="openclaw-sent-tag">📡 {t(lang, 'alertSentFeishu')}</span>}
                    </div>
                  </div>
                ) : !isDetecting ? (
                  <div className="panel-empty">{t(lang, 'waitingDetection')}</div>
                ) : null}
              </div>
            </div>

            {!competitionDemo && (
              <>
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
            )}
          </>
        ) : !competitionDemo ? (
          <div className="panel-card"><div className="panel-body"><FileUpload
            onDetectionResult={onDetectionResult}
            onAnalyzingChange={setUploadAnalyzing}
            onScanProgressChange={setUploadScanProgress}
            onVideoUpload={(url, name) => {
              setUploadedVideoUrl(url);
              setUploadedFileName(name);
              setShowSimpleAlert(false);
              setShowDetailAlert(false);
              setUploadWarning(null);
              setUploadAnalyzing(false);
              setActiveTab('upload');
            }}
            onUploadWarning={(res) => {
              setUploadWarning(res);
              if (res.level !== 'safe') {
                setDetectionResult(res);
                setAlertSourceTitle(uploadedFileName || 'Uploaded Video');
                const tier = getRiskTier(res);
                setShowSimpleAlert(tier === 'high');
                setShowDetailAlert(false);
                if (tier === 'high') triggerElderHaptic();
                void pushFamilyAlert(res, uploadedFileName || 'Uploaded Video');
              }
            }}
            lang={lang}
          /></div></div>
        ) : null}
      </div>
      )}
    </div>
  );
};

export default MobileSimulator;
