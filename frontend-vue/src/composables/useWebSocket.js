import { ref, onUnmounted } from 'vue';

const blobToBase64 = (blob) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onloadend = () => {
    const result = String(reader.result || '');
    resolve(result.includes(',') ? result.split(',')[1] : result);
  };
  reader.onerror = reject;
  reader.readAsDataURL(blob);
});

export function useWebSocket() {
  const state = ref('idle'); // idle | recording | sending | transcribing | done | error
  const statusText = ref('准备就绪');
  const errorText = ref('');
  
  const transcriptText = ref('');
  const finalText = ref('');
  const rawText = ref('');
  const appliedCorrectionsCount = ref(0);
  const warningText = ref('');
  const latencyInfo = ref('');
  const isConnected = ref(false);
  const isConnError = ref(false);
  const recordingTime = ref(0);

  // ASR mode state
  const selectedAsrMode = ref('fast');
  const backendAsrMode = ref('');
  const backendAsrModel = ref('');
  const backendModelCached = ref(null);

  // Segment streaming state
  const segmentStreamingEnabled = ref(false);
  const isSegmentMode = ref(false);
  const segmentIndex = ref(0);
  const partialFailureCount = ref(0);
  
  let mediaRecorder = null; // Used for default full recording
  let socket = null;
  let audioStream = null;
  let timerInterval = null;

  // Short-lived recorder refs
  let segmentRecorder = null;
  let segmentTimer = null;
  let segmentStopping = false;

  const setState = (newState, errorMessage = '') => {
    state.value = newState;
    if (newState === 'error') {
      errorText.value = errorMessage || '发生未知错误';
    }
    
    switch (newState) {
      case 'idle':
        statusText.value = '准备就绪';
        break;
      case 'recording':
        statusText.value = '录音中...';
        break;
      case 'sending':
        statusText.value = '发送中...';
        break;
      case 'transcribing':
        statusText.value = '识别中...';
        break;
      case 'done':
        statusText.value = '识别完成';
        break;
      case 'error':
        statusText.value = '发生错误';
        break;
    }
  };

  const updateConnectionState = (connected, error = false) => {
    isConnected.value = connected;
    isConnError.value = error;
  };

  const cleanup = () => {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
    if (segmentTimer) {
      clearTimeout(segmentTimer);
      segmentTimer = null;
    }
    if (audioStream) {
      audioStream.getTracks().forEach(track => track.stop());
      audioStream = null;
    }
    if (socket) {
      socket.onclose = null;
      socket.close();
      socket = null;
    }
    mediaRecorder = null;
    segmentRecorder = null;
  };

  const startNextSegmentRecorder = () => {
    if (segmentStopping || state.value !== 'recording') return;
    
    segmentRecorder = new MediaRecorder(audioStream, { mimeType: 'audio/webm' });
    let chunks = [];
    segmentRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };
    
    segmentRecorder.onstop = async () => {
      if (chunks.length > 0 && socket && socket.readyState === WebSocket.OPEN) {
        const blob = new Blob(chunks, { type: 'audio/webm' });
        try {
          const base64 = await blobToBase64(blob);
          segmentIndex.value++;
          socket.send(JSON.stringify({
            type: "audio_segment",
            segment_index: segmentIndex.value,
            chunk_base64: base64,
            is_final: false
          }));
        } catch (err) {
          console.error('Blob to base64 error', err);
        }
      }
      
      if (!segmentStopping && state.value === 'recording') {
         startNextSegmentRecorder();
      } else if (segmentStopping && socket && socket.readyState === WebSocket.OPEN) {
         socket.send(JSON.stringify({ type: "end" }));
         setState('transcribing');
      }
    };
    
    segmentRecorder.start();
    
    segmentTimer = setTimeout(() => {
      if (segmentRecorder && segmentRecorder.state === 'recording') {
        segmentRecorder.stop();
      }
    }, 2500);
  };

  const startRecording = async (onDoneCallback, onToastCallback) => {
    transcriptText.value = '';
    finalText.value = '';
    rawText.value = '';
    appliedCorrectionsCount.value = 0;
    warningText.value = '';
    latencyInfo.value = '';
    recordingTime.value = 0;
    segmentStopping = false;
    partialFailureCount.value = 0;
    segmentIndex.value = 0;
    
    // Snapshot the toggle state when recording starts
    isSegmentMode.value = segmentStreamingEnabled.value;
    
    setState('idle');

    try {
      audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      socket = new WebSocket('ws://localhost:8000/ws/transcribe');

      socket.onopen = () => {
        updateConnectionState(true, false);
        
        const startMsg = {
          type: "start",
          session_id: "vue-demo",
          format: "webm",
          sample_rate: 16000,
          channels: 1,
          language: "zh",
          asr_mode: selectedAsrMode.value
        };
        
        if (isSegmentMode.value) {
          startMsg.streaming_mode = "segment";
        }
        
        socket.send(JSON.stringify(startMsg));

        setState('recording');
        
        timerInterval = setInterval(() => {
          recordingTime.value++;
        }, 1000);
        
        if (isSegmentMode.value) {
          startNextSegmentRecorder();
        } else {
          // Default behavior
          mediaRecorder = new MediaRecorder(audioStream, { mimeType: 'audio/webm' });
          mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {
              socket.send(event.data);
            }
          };

          mediaRecorder.onstop = () => {
            if (timerInterval) {
              clearInterval(timerInterval);
              timerInterval = null;
            }
            setState('sending');
            if (socket.readyState === WebSocket.OPEN) {
              socket.send(JSON.stringify({ type: "end" }));
              setState('transcribing');
            }
          };

          mediaRecorder.start(250);
        }
      };

      socket.onmessage = (event) => {
        try {
          const res = JSON.parse(event.data);
          
          if (res.type === 'ack') {
            console.log('Received ack');
          } else if (res.type === 'partial_transcription_result') {
            if (res.result && res.result.data) {
               transcriptText.value = res.result.data.merged_text || '';
               statusText.value = '准流式识别中...';
               if (res.result.data.latency_ms) {
                 latencyInfo.value = `片段延迟: ${res.result.data.latency_ms}ms`;
               }
               
               const meta = res.result.meta || {};
               backendAsrMode.value = meta.asr_mode || selectedAsrMode.value;
               backendAsrModel.value = meta.model || '';
               backendModelCached.value = meta.model_cached ?? null;
            }
          } else if (res.type === 'partial_error') {
            if (onToastCallback) onToastCallback('某个片段识别失败，已继续录音');
            partialFailureCount.value++;
            if (partialFailureCount.value >= 3) {
               if (onToastCallback) onToastCallback('连续失败，已自动关闭实验开关，下次将使用整段识别');
               segmentStreamingEnabled.value = false;
            }
          } else if (res.type === 'transcription_result') {
            if (res.result && res.result.success && res.result.data) {
              transcriptText.value = res.result.data.final_text || res.result.data.raw_text || '';
              finalText.value = res.result.data.final_text || '';
              rawText.value = res.result.data.raw_text || '';
              
              if (res.result.data.applied_corrections) {
                appliedCorrectionsCount.value = res.result.data.applied_corrections.length;
              } else {
                appliedCorrectionsCount.value = 0;
              }
              warningText.value = res.result.data.warning || '';
              
              const meta = res.result.meta || {};
              backendAsrMode.value = meta.asr_mode || selectedAsrMode.value;
              backendAsrModel.value = meta.model || '';
              backendModelCached.value = meta.model_cached ?? null;
              
              const data = res.result.data || {};
              
              let times = [];
              if (meta.decode_ms) times.push(`解码:${meta.decode_ms}ms`);
              if (meta.asr_ms) times.push(`ASR:${meta.asr_ms}ms`);
              if (meta.postprocess_ms) times.push(`处理:${meta.postprocess_ms}ms`);
              if (meta.total_ms || data.latency_ms) times.push(`总计:${meta.total_ms || data.latency_ms}ms`);

              if (times.length > 0) {
                latencyInfo.value = `引擎: ${data.engine || '未知'} | 耗时: ${times.join(' ')}`;
              } else if (data.latency_ms) {
                latencyInfo.value = `引擎: ${data.engine || '未知'} | 延迟: ${data.latency_ms}ms`;
              }
              
              setState('done');
              socket.close();
              if (onDoneCallback) onDoneCallback();
            } else if (res.result && res.result.error) {
              setState('error', res.result.error.message || '识别失败');
              socket.close();
            }
          } else if (res.type === 'error') {
            if (res.result && res.result.error) {
              if (res.result.error.code === 'CONFIG_ERROR') {
                 if (onToastCallback) onToastCallback('后端未启用准流式识别，已切回整段识别');
                 segmentStreamingEnabled.value = false;
                 setState('error', '后端配置不支持准流式');
              } else {
                 setState('error', res.result.error.message || '发生错误');
              }
            } else {
              setState('error', '发生未知错误');
            }
            socket.close();
          }
        } catch (e) {
          console.error('Failed to parse message', e);
        }
      };

      socket.onerror = (err) => {
        console.error('WebSocket error:', err);
        updateConnectionState(false, true);
        setState('error', 'WebSocket 连接失败，请确保后端服务运行');
        cleanup();
      };

      socket.onclose = () => {
        updateConnectionState(false);
        if (state.value === 'recording' || state.value === 'transcribing' || state.value === 'sending') {
          setState('error', '连接意外断开');
        }
        cleanup();
      };

    } catch (err) {
      console.error('Microphone access error:', err);
      if (err.name === 'NotAllowedError') {
        setState('error', '未获得麦克风权限');
      } else if (err.name === 'NotFoundError') {
        setState('error', '未检测到麦克风设备');
      } else {
        setState('error', `麦克风错误: ${err.message}`);
      }
    }
  };

  const stopRecording = (abort = false) => {
    if (abort) {
      cleanup();
      setState('idle');
      return;
    }
    
    if (isSegmentMode.value) {
      segmentStopping = true;
      setState('sending');
      if (segmentTimer) {
        clearTimeout(segmentTimer);
        segmentTimer = null;
      }
      if (segmentRecorder && segmentRecorder.state === 'recording') {
        segmentRecorder.stop();
      } else if (socket && socket.readyState === WebSocket.OPEN) {
        // Fallback if recorder was already stopped and waiting to start next
        socket.send(JSON.stringify({ type: "end" }));
        setState('transcribing');
      }
    } else {
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
      }
    }
  };

  onUnmounted(() => {
    cleanup();
  });

  return {
    state,
    statusText,
    errorText,
    transcriptText,
    finalText,
    rawText,
    appliedCorrectionsCount,
    warningText,
    latencyInfo,
    isConnected,
    isConnError,
    recordingTime,
    selectedAsrMode,
    backendAsrMode,
    backendAsrModel,
    backendModelCached,
    segmentStreamingEnabled,
    startRecording,
    stopRecording
  };
}
