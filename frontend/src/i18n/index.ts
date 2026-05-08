export type Language = 'zh' | 'yue' | 'en';

export const translations = {
  zh: {
    // Header
    appName: 'AI守护',
    appDesc: '老人短视频虚假信息检测系统',
    detected: '已检测',
    riskBlocked: '风险拦截',
    aiOnline: 'AI在线',
    settings: '设置',

    // Mobile Simulator
    follow: '关注',
    recommend: '推荐',
    home: '首页',
    discover: '发现',
    messages: '消息',
    me: '我',
    swipeHint: '↕️ 上下滑动或按方向键切换视频',
    aiScanning: '🤖 AI 检测中...',
    detectFailed: '检测失败',

    // Detection Panel
    aiRealTimeDetection: '🛡️ AI实时检测',
    highRisk: '🚨 高风险',
    caution: '⚠️ 注意',
    safe: '✅ 安全',
    detecting: '🔍 正在检测当前视频...',
    waitingDetection: '等待视频检测...',
    detectionStats: '📊 检测统计',
    totalVideos: '视频总数',
    highRiskCount: '高风险',
    suspiciousCount: '可疑',
    safeCount: '安全',
    antiScamTips: '🛡️ 防骗提醒',
    tip1: '💰 保证高收益的都是骗局',
    tip2: '💊 包治百病的产品不存在',
    tip3: '📞 遇到可疑内容请联系家人',
    tip4: '🚫 不要轻易转账或加好友',

    // Detection Floater
    dangerTitle: '高风险警告',
    dangerDesc: '检测到可能的诈骗或虚假信息',
    dangerAction: '建议立即停止观看',
    warningTitle: '注意风险',
    warningDesc: '内容存在可疑信息',
    warningAction: '建议谨慎对待',
    safeTitle: '内容安全',
    safeDesc: '未发现明显风险',
    safeAction: '可以正常观看',
    riskScore: '风险评分',
    riskFactors: '⚡ 风险因素',
    safetySuggestions: '💡 安全建议',
    safetyReminder: '🛡️ 遇到可疑内容请立即联系家人或拨打110',
    iKnow: '我知道了',
    details: '详情',
    close: '关闭',

    // Upload
    uploadTitle: '📁 文件上传检测',
    uploadDesc: '上传视频或音频文件进行虚假信息检测',
    uploadDragger: '点击或拖拽文件到此区域上传',
    uploadHint: '支持 MP4, AVI, MOV, MP3, WAV 等格式，单个文件不超过 100MB',
    uploadAnalyze: '开始分析',
    uploadAnalyzing: '正在分析...',
    uploadResult: '检测结果',
    uploadNoFile: '请先上传文件',
    uploadSuccess: '文件上传成功',
    uploadError: '文件上传失败',

    // Settings
    settingsTitle: '个人设置',
    displaySettings: '📱 显示设置',
    fontSize: '字体大小',
    fontSizeDesc: '选择适合的字体大小',
    fontNormal: '标准',
    fontLarge: '大字体 (推荐)',
    fontExtraLarge: '超大字体',
    highContrast: '高对比度',
    highContrastDesc: '提高文字和背景的对比度',
    themeMode: '主题模式',
    themeModeDesc: '切换明亮或暗色主题',
    themeDark: '暗色',
    themeLight: '明亮',
    language: '语言',
    languageDesc: '切换界面语言',
    
    detectionSettings: '🔍 检测设置',
    sensitivity: '检测敏感度',
    sensitivityDesc: '调整虚假信息检测的敏感程度',
    sensitivityLow: '宽松',
    sensitivityLowDesc: '只检测明显的诈骗信息',
    sensitivityMedium: '适中 (推荐)',
    sensitivityMediumDesc: '平衡检测准确性和误报率',
    sensitivityHigh: '严格',
    sensitivityHighDesc: '检测所有可疑内容',
    soundAlert: '声音提醒',
    soundAlertDesc: '检测到风险时播放提示音',
    testSound: '测试音效',
    on: '开启',
    off: '关闭',

    familySettings: '👨‍👩‍👧‍👦 家人设置',
    familyPhone: '家人电话',
    familyPhoneDesc: '紧急情况下联系的家人电话',
    familyPhonePlaceholder: '请输入家人电话号码',
    riskNotify: '风险通知',
    riskNotifyDesc: '检测到高风险内容时通知家人',

    openclawSettings: '🤖 OpenClaw 智能通知',
    openclawDesc: '配置 OpenClaw Skill 将风险告警推送到企业微信或QQ',
    openclawEnable: '启用 OpenClaw',
    openclawEnableDesc: '开启后，检测到危险内容将自动发送告警',
    openclawWebhook: 'Webhook 地址',
    openclawWebhookPlaceholder: '输入企业微信/QQ机器人 Webhook URL',
    openclawChannel: '通知渠道',
    openclawWecom: '企业微信',
    openclawQQ: 'QQ',
    openclawBoth: '全部',
    openclawThreshold: '告警阈值',
    openclawThresholdDesc: '风险分数达到此值时触发告警',
    openclawTest: '发送测试通知',
    openclawTestSuccess: '测试通知已发送',

    helpTitle: '❓ 使用帮助',
    privacyTitle: '🔒 隐私保护',
    save: '保存设置',
    cancel: '取消',
    resetDefault: '恢复默认',
    settingsSaved: '设置已保存',
    settingsReset: '设置已重置为推荐配置',
    clearData: '清除所有本地数据',
    dataCleared: '本地数据已清除',
  },

  yue: {
    // Header
    appName: 'AI 守護',
    appDesc: '長者短片虛假資訊偵測系統',
    detected: '已檢查',
    riskBlocked: '風險攔截',
    aiOnline: 'AI 在線',
    settings: '設定',

    // Mobile Simulator
    follow: '關注',
    recommend: '推薦',
    home: '首頁',
    discover: '發現',
    messages: '訊息',
    me: '我',
    swipeHint: '↕️ 上下滑動或按方向鍵切換短片',
    aiScanning: '🤖 AI 檢查緊...',
    detectFailed: '檢查失敗',

    // Detection Panel
    aiRealTimeDetection: '🛡️ AI 即時檢查',
    highRisk: '🚨 高風險',
    caution: '⚠️ 小心',
    safe: '✅ 安全',
    detecting: '🔍 正在檢查目前短片...',
    waitingDetection: '等待短片檢查...',
    detectionStats: '📊 檢查統計',
    totalVideos: '短片總數',
    highRiskCount: '高風險',
    suspiciousCount: '可疑',
    safeCount: '安全',
    antiScamTips: '🛡️ 防騙提醒',
    tip1: '💰 保證高回報通常都係騙局',
    tip2: '💊 包醫百病嘅產品唔可信',
    tip3: '📞 見到可疑內容請即刻聯絡屋企人',
    tip4: '🚫 唔好輕易轉賬或者加陌生人',

    // Detection Floater
    dangerTitle: '高風險警告',
    dangerDesc: '偵測到可能係騙局或虛假資訊',
    dangerAction: '建議即刻停止觀看',
    warningTitle: '注意風險',
    warningDesc: '內容存在可疑資訊',
    warningAction: '建議小心處理',
    safeTitle: '內容安全',
    safeDesc: '暫時未發現明顯風險',
    safeAction: '可以繼續觀看',
    riskScore: '風險評分',
    riskFactors: '⚡ 風險因素',
    safetySuggestions: '💡 安全建議',
    safetyReminder: '🛡️ 遇到可疑內容請即刻聯絡屋企人或報警',
    iKnow: '我知道',
    details: '詳情',
    close: '關閉',

    // Upload
    uploadTitle: '📁 上載檔案檢查',
    uploadDesc: '上載短片或音訊檔案進行虛假資訊檢查',
    uploadDragger: '點擊或拖放檔案到呢度上載',
    uploadHint: '支援 MP4, AVI, MOV, MP3, WAV 等格式，單個檔案不超過 100MB',
    uploadAnalyze: '開始分析',
    uploadAnalyzing: '分析緊...',
    uploadResult: '檢查結果',
    uploadNoFile: '請先上載檔案',
    uploadSuccess: '檔案上載成功',
    uploadError: '檔案上載失敗',

    // Settings
    settingsTitle: '個人設定',
    displaySettings: '📱 顯示設定',
    fontSize: '字體大小',
    fontSizeDesc: '選擇舒服易睇嘅字體大小',
    fontNormal: '標準',
    fontLarge: '大字體（推薦）',
    fontExtraLarge: '特大字體',
    highContrast: '高對比度',
    highContrastDesc: '提高文字同背景對比度',
    themeMode: '主題模式',
    themeModeDesc: '切換明亮或深色主題',
    themeDark: '深色',
    themeLight: '明亮',
    language: '語言',
    languageDesc: '切換介面語言',
    
    detectionSettings: '🔍 檢查設定',
    sensitivity: '檢查敏感度',
    sensitivityDesc: '調整偵測虛假資訊嘅敏感程度',
    sensitivityLow: '寬鬆',
    sensitivityLowDesc: '只檢查明顯騙局',
    sensitivityMedium: '適中（推薦）',
    sensitivityMediumDesc: '平衡準確度同誤報率',
    sensitivityHigh: '嚴格',
    sensitivityHighDesc: '檢查所有可疑內容',
    soundAlert: '聲音提醒',
    soundAlertDesc: '偵測到風險時播放提示音',
    testSound: '測試聲效',
    on: '開啟',
    off: '關閉',

    familySettings: '👨‍👩‍👧‍👦 家人設定',
    familyPhone: '家人電話',
    familyPhoneDesc: '緊急情況下聯絡嘅家人電話',
    familyPhonePlaceholder: '請輸入家人電話號碼',
    riskNotify: '風險通知',
    riskNotifyDesc: '偵測到高風險內容時通知家人',

    openclawSettings: '🤖 OpenClaw 智能通知',
    openclawDesc: '設定 OpenClaw Skill，將風險警報推送到企業微信或 QQ',
    openclawEnable: '啟用 OpenClaw',
    openclawEnableDesc: '開啟後，偵測到危險內容會自動發送警報',
    openclawWebhook: 'Webhook 地址',
    openclawWebhookPlaceholder: '輸入企業微信/QQ 機械人 Webhook URL',
    openclawChannel: '通知渠道',
    openclawWecom: '企業微信',
    openclawQQ: 'QQ',
    openclawBoth: '全部',
    openclawThreshold: '警報門檻',
    openclawThresholdDesc: '風險分數達到此值時觸發警報',
    openclawTest: '發送測試通知',
    openclawTestSuccess: '測試通知已發送',

    helpTitle: '❓ 使用幫助',
    privacyTitle: '🔒 私隱保護',
    save: '儲存設定',
    cancel: '取消',
    resetDefault: '恢復預設',
    settingsSaved: '設定已儲存',
    settingsReset: '設定已重置為推薦配置',
    clearData: '清除所有本地資料',
    dataCleared: '本地資料已清除',
  },

  en: {
    // Header
    appName: 'AI Guard',
    appDesc: 'Elder Video Misinformation Detection',
    detected: 'Detected',
    riskBlocked: 'Blocked',
    aiOnline: 'AI Online',
    settings: 'Settings',

    // Mobile Simulator
    follow: 'Following',
    recommend: 'For You',
    home: 'Home',
    discover: 'Discover',
    messages: 'Inbox',
    me: 'Me',
    swipeHint: '↕️ Swipe or press arrow keys to switch videos',
    aiScanning: '🤖 AI Scanning...',
    detectFailed: 'Detection failed',

    // Detection Panel
    aiRealTimeDetection: '🛡️ AI Real-time Detection',
    highRisk: '🚨 High Risk',
    caution: '⚠️ Caution',
    safe: '✅ Safe',
    detecting: '🔍 Detecting current video...',
    waitingDetection: 'Waiting for detection...',
    detectionStats: '📊 Detection Statistics',
    totalVideos: 'Total',
    highRiskCount: 'Danger',
    suspiciousCount: 'Warning',
    safeCount: 'Safe',
    antiScamTips: '🛡️ Safety Tips',
    tip1: '💰 Guaranteed returns = scam',
    tip2: '💊 Miracle cures don\'t exist',
    tip3: '📞 Contact family for suspicious content',
    tip4: '🚫 Never transfer money to strangers',

    // Detection Floater
    dangerTitle: 'High Risk Warning',
    dangerDesc: 'Potential scam or misinformation detected',
    dangerAction: 'Stop watching immediately',
    warningTitle: 'Caution',
    warningDesc: 'Suspicious content found',
    warningAction: 'Proceed with caution',
    safeTitle: 'Content Safe',
    safeDesc: 'No obvious risks found',
    safeAction: 'Safe to watch',
    riskScore: 'Risk Score',
    riskFactors: '⚡ Risk Factors',
    safetySuggestions: '💡 Safety Suggestions',
    safetyReminder: '🛡️ Contact family or call police for suspicious content',
    iKnow: 'I Understand',
    details: 'Details',
    close: 'Close',

    // Upload
    uploadTitle: '📁 File Upload Detection',
    uploadDesc: 'Upload video or audio files for misinformation detection',
    uploadDragger: 'Click or drag files here to upload',
    uploadHint: 'Supports MP4, AVI, MOV, MP3, WAV. Max 100MB per file',
    uploadAnalyze: 'Analyze',
    uploadAnalyzing: 'Analyzing...',
    uploadResult: 'Detection Result',
    uploadNoFile: 'Please upload a file first',
    uploadSuccess: 'File uploaded successfully',
    uploadError: 'Upload failed',

    // Settings
    settingsTitle: 'Settings',
    displaySettings: '📱 Display',
    fontSize: 'Font Size',
    fontSizeDesc: 'Choose a comfortable font size',
    fontNormal: 'Standard',
    fontLarge: 'Large (Recommended)',
    fontExtraLarge: 'Extra Large',
    highContrast: 'High Contrast',
    highContrastDesc: 'Increase text and background contrast',
    themeMode: 'Theme',
    themeModeDesc: 'Switch between light and dark theme',
    themeDark: 'Dark',
    themeLight: 'Light',
    language: 'Language',
    languageDesc: 'Switch interface language',

    detectionSettings: '🔍 Detection',
    sensitivity: 'Sensitivity',
    sensitivityDesc: 'Adjust detection sensitivity level',
    sensitivityLow: 'Low',
    sensitivityLowDesc: 'Only detect obvious scams',
    sensitivityMedium: 'Medium (Recommended)',
    sensitivityMediumDesc: 'Balance accuracy and false positives',
    sensitivityHigh: 'High',
    sensitivityHighDesc: 'Detect all suspicious content',
    soundAlert: 'Sound Alert',
    soundAlertDesc: 'Play alert sound when risks detected',
    testSound: 'Test Sound',
    on: 'On',
    off: 'Off',

    familySettings: '👨‍👩‍👧‍👦 Family',
    familyPhone: 'Family Phone',
    familyPhoneDesc: 'Emergency contact number',
    familyPhonePlaceholder: 'Enter family phone number',
    riskNotify: 'Risk Notification',
    riskNotifyDesc: 'Notify family when high risk detected',

    openclawSettings: '🤖 OpenClaw Notifications',
    openclawDesc: 'Configure OpenClaw Skill to push alerts to WeCom or QQ',
    openclawEnable: 'Enable OpenClaw',
    openclawEnableDesc: 'Auto-send alerts when danger content detected',
    openclawWebhook: 'Webhook URL',
    openclawWebhookPlaceholder: 'Enter WeCom/QQ bot Webhook URL',
    openclawChannel: 'Notification Channel',
    openclawWecom: 'WeCom',
    openclawQQ: 'QQ',
    openclawBoth: 'Both',
    openclawThreshold: 'Alert Threshold',
    openclawThresholdDesc: 'Trigger alert when risk score reaches this value',
    openclawTest: 'Send Test Notification',
    openclawTestSuccess: 'Test notification sent',

    helpTitle: '❓ Help',
    privacyTitle: '🔒 Privacy',
    save: 'Save',
    cancel: 'Cancel',
    resetDefault: 'Reset',
    settingsSaved: 'Settings saved',
    settingsReset: 'Settings reset to defaults',
    clearData: 'Clear all local data',
    dataCleared: 'Local data cleared',
  },
};

export type TranslationKey = keyof typeof translations.zh;

export const t = (lang: Language, key: TranslationKey): string => {
  return translations[lang]?.[key] || translations.zh[key] || key;
};

/**
 * 翻译后端返回的中文 reasons / suggestions 为英文（lang=en 时）
 */
const reasonMap: Record<string, string> = {
  '建议谨慎对待该内容': 'Proceed with caution',
  '如遇可疑情况请拨打96110反诈热线': 'Call 96110 anti-fraud hotline if suspicious',
  '投资需谨慎，高收益往往伴随高风险': 'Be cautious with investments — high returns mean high risk',
  '不要轻易相信保证收益的投资项目': 'Do not trust guaranteed-return investment schemes',
  '有病请找正规医院，不要轻信偏方': 'See a real doctor — do not trust folk remedies',
  '保健品不能替代药物治疗': 'Supplements cannot replace medical treatment',
  '冷静思考，不要被紧急性语言误导': 'Stay calm — do not be misled by urgency language',
  '不要轻易添加陌生人联系方式或转账': 'Do not add strangers or transfer money',
  'AI模型和规则引擎均未发现风险': 'AI models and rule engine found no risk',
  '综合分析发现潜在风险': 'Comprehensive analysis found potential risk',
  '如有疑问，请咨询家人或专业人士': 'Consult family or professionals if in doubt',
  '遇到要求转账的情况请立即警惕': 'Be immediately alert to any money transfer requests',
};

const yueReasonMap: Record<string, string> = {
  '建议谨慎对待该内容': '建議小心處理呢段內容',
  '如遇可疑情况请拨打96110反诈热线': '遇到可疑情況請即刻聯絡屋企人或報警',
  '投资需谨慎，高收益往往伴随高风险': '投資要小心，高回報通常伴隨高風險',
  '不要轻易相信保证收益的投资项目': '唔好輕易相信保證回報嘅投資項目',
  '有病请找正规医院，不要轻信偏方': '有病請搵正規醫院，唔好輕信偏方',
  '保健品不能替代药物治疗': '保健品唔可以代替藥物治療',
  '冷静思考，不要被紧急性语言误导': '冷靜諗清楚，唔好畀緊急話術誤導',
  '不要轻易添加陌生人联系方式或转账': '唔好輕易加陌生人聯絡方式或者轉賬',
  'AI模型和规则引擎均未发现风险': 'AI 模型同規則引擎暫時未發現風險',
  '综合分析发现潜在风险': '綜合分析發現潛在風險',
  '如有疑问，请咨询家人或专业人士': '有疑問請問屋企人或專業人士',
  '遇到要求转账的情况请立即警惕': '遇到要求轉賬要即刻警惕',
};

export const translateReason = (lang: Language, text: string): string => {
  if (lang === 'zh') return text;
  if (lang === 'yue') {
    if (yueReasonMap[text]) return yueReasonMap[text];
    for (const [zh, yue] of Object.entries(yueReasonMap)) {
      if (text.includes(zh)) return text.replace(zh, yue);
    }
    return text
      .replace(/检测到/g, '偵測到')
      .replace(/风险/g, '風險')
      .replace(/关键词/g, '關鍵詞')
      .replace(/紧急性诱导词汇/g, '緊急性誘導詞')
      .replace(/视频内容/g, '短片內容')
      .replace(/内容摘要/g, '內容摘要')
      .replace(/主要风险/g, '主要風險')
      .replace(/识别来源/g, '識別來源')
      .replace(/语音转写/g, '語音轉寫')
      .replace(/画面文字/g, '畫面文字');
  }
  // 精确匹配
  if (reasonMap[text]) return reasonMap[text];
  // 模式匹配
  for (const [zh, en] of Object.entries(reasonMap)) {
    if (text.includes(zh)) return text.replace(zh, en);
  }
  // BERT/TF-IDF 模式
  const bertMatch = text.match(/BERT AI模型判定为风险内容（置信度 (\d+%)）/);
  if (bertMatch) return `BERT AI model flagged as risky (confidence ${bertMatch[1]})`;
  const tfidfMatch = text.match(/TF-IDF AI模型判定为风险内容（置信度 (\d+%)）/);
  if (tfidfMatch) return `TF-IDF AI model flagged as risky (confidence ${tfidfMatch[1]})`;
  // 关键词检测模式
  const kwMatch = text.match(/检测到(\d+)个(.+?)关键词/);
  if (kwMatch) return `Detected ${kwMatch[1]} ${kwMatch[2]} risk keywords`;
  const urgMatch = text.match(/检测到(\d+)个紧急性诱导词汇/);
  if (urgMatch) return `Detected ${urgMatch[1]} urgency manipulation keywords`;
  if (text.includes('含有联系方式且存在其他风险因素')) return 'Contains contact info with other risk factors';
  if (text.includes('ASR/OCR 冲突')) return text.replace('ASR/OCR 冲突', 'ASR/OCR conflict');
  // _build_content_summary 翻译
  if (text.includes('注意：视频内容存在可疑信息')) return '⚠️ Warning: Suspicious content detected in video';
  if (text.includes('高风险警告：视频内容存在严重安全隐患')) return '🚨 High Risk: Serious security threat detected';
  if (text.includes('视频内容相对安全')) return '✅ Video content appears safe';
  if (text.includes('识别来源：')) return text.replace('识别来源：', 'Source: ').replace('语音转写(ASR)', 'Speech (ASR)').replace('画面文字(OCR)', 'Screen text (OCR)');
  if (text.includes('内容摘要：')) return text.replace('内容摘要：', 'Summary: ');
  if (text.includes('主要风险：')) return text.replace('主要风险：', 'Main risk: ');
  // 无法翻译时返回原文
  return text;
};
