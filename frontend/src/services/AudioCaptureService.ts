/**
 * 音频捕获服务
 * 负责通过Web Audio API捕获音频并进行语音转文字
 */
export default class AudioCaptureService {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private isRecording = false;
  private recognition: any = null; // SpeechRecognition
  private onTranscriptCallback: ((text: string) => void) | null = null;

  constructor() {
    // 初始化语音识别 (仅在支持的浏览器中)
    this.initSpeechRecognition();
  }

  /**
   * 初始化语音识别
   */
  private initSpeechRecognition() {
    try {
      // 检查浏览器支持
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      
      if (SpeechRecognition) {
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true; // 持续识别
        this.recognition.interimResults = true; // 获取中间结果
        this.recognition.lang = 'zh-CN'; // 设置为中文
        this.recognition.maxAlternatives = 1;

        // 识别结果处理
        this.recognition.onresult = (event: any) => {
          let finalTranscript = '';
          
          // 获取最新的识别结果
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += transcript;
            }
          }
          
          if (finalTranscript && this.onTranscriptCallback) {
            this.onTranscriptCallback(finalTranscript);
          }
        };

        // 错误处理
        this.recognition.onerror = (event: any) => {
          console.error('语音识别错误:', event.error);
          if (event.error === 'no-speech') {
            console.log('没有检测到语音');
          }
        };

        // 识别结束处理
        this.recognition.onend = () => {
          if (this.isRecording) {
            // 如果还在录制中，重新开始识别
            setTimeout(() => {
              if (this.isRecording) {
                this.recognition?.start();
              }
            }, 100);
          }
        };

        console.log('语音识别初始化成功');
      } else {
        console.warn('浏览器不支持语音识别API');
      }
    } catch (error) {
      console.error('语音识别初始化失败:', error);
    }
  }

  /**
   * 开始音频捕获
   */
  async startCapture(onTranscript: (text: string) => void): Promise<void> {
    try {
      this.onTranscriptCallback = onTranscript;

      // 请求麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        } 
      });

      // 创建MediaRecorder
      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm' // 使用webm格式以获得更好的兼容性
      });

      this.audioChunks = [];

      // 设置数据处理
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      // 录制结束处理
      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        // 可以在这里处理录制完成的音频数据
        console.log('音频录制完成，大小:', audioBlob.size, 'bytes');
      };

      // 开始录制
      this.mediaRecorder.start(1000); // 每秒生成一个数据块
      this.isRecording = true;

      // 开始语音识别
      if (this.recognition) {
        this.recognition.start();
      }

      console.log('音频捕获已开始');
    } catch (error) {
      console.error('启动音频捕获失败:', error);
      throw new Error('无法访问麦克风，请检查浏览器权限设置');
    }
  }

  /**
   * 停止音频捕获
   */
  stopCapture(): void {
    try {
      this.isRecording = false;

      // 停止MediaRecorder
      if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
        this.mediaRecorder.stop();
        
        // 停止所有音频轨道
        this.mediaRecorder.stream.getTracks().forEach(track => {
          track.stop();
        });
      }

      // 停止语音识别
      if (this.recognition) {
        this.recognition.stop();
      }

      this.onTranscriptCallback = null;
      console.log('音频捕获已停止');
    } catch (error) {
      console.error('停止音频捕获时出错:', error);
    }
  }

  /**
   * 检查浏览器是否支持音频捕获
   */
  static isSupported(): boolean {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  }

  /**
   * 检查是否支持语音识别
   */
  static isSpeechRecognitionSupported(): boolean {
    return !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
  }

  /**
   * 获取录制状态
   */
  getRecordingState(): boolean {
    return this.isRecording;
  }

  /**
   * 音频格式转换 (如果需要发送到服务器)
   */
  private async convertAudioFormat(audioBlob: Blob): Promise<Blob> {
    return new Promise((resolve) => {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const fileReader = new FileReader();
      
      fileReader.onload = async (e) => {
        try {
          const arrayBuffer = e.target?.result as ArrayBuffer;
          const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
          
          // 这里可以进行音频处理和格式转换
          // 暂时直接返回原始数据
          resolve(audioBlob);
        } catch (error) {
          console.error('音频转换失败:', error);
          resolve(audioBlob);
        }
      };
      
      fileReader.readAsArrayBuffer(audioBlob);
    });
  }

  /**
   * 音频质量分析
   */
  private analyzeAudioQuality(audioData: Float32Array): number {
    // 计算音频的RMS值来评估质量
    let sum = 0;
    for (let i = 0; i < audioData.length; i++) {
      sum += audioData[i] * audioData[i];
    }
    const rms = Math.sqrt(sum / audioData.length);
    
    // 返回0-1的质量分数
    return Math.min(rms * 10, 1);
  }

  /**
   * 获取音频设备列表
   */
  static async getAudioDevices(): Promise<MediaDeviceInfo[]> {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      return devices.filter(device => device.kind === 'audioinput');
    } catch (error) {
      console.error('获取音频设备失败:', error);
      return [];
    }
  }
}
