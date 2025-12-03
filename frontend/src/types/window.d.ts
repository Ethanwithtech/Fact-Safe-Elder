// 扩展Window接口，添加浏览器API类型定义

interface Window {
  SpeechRecognition: any;
  webkitSpeechRecognition: any;
  AudioContext: typeof AudioContext;
  webkitAudioContext: typeof AudioContext;
}





