<script setup>
import { onMounted, ref, watch } from 'vue'
import { useWebSocket } from './composables/useWebSocket'
import { useHistory } from './composables/useHistory'
import { useMeetingAgent } from './composables/useMeetingAgent'

const {
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
  startRecording,
  stopRecording
} = useWebSocket()

const {
  historyItems,
  historyError,
  fetchHistory,
  clearHistory,
  exportMarkdown
} = useHistory()

const {
  summaryMarkdown,
  summaryLoading,
  summaryError,
  summaryMeta,
  generateSummary,
  copySummary,
  downloadSummary
} = useMeetingAgent()

const toastMessage = ref('')
const toastVisible = ref(false)
let toastTimeout = null

const showToast = (msg, duration = 3000) => {
  toastMessage.value = msg
  toastVisible.value = true
  if (toastTimeout) clearTimeout(toastTimeout)
  toastTimeout = setTimeout(() => {
    toastVisible.value = false
  }, duration)
}

const hideErrorHistory = ref(true)

const formatTime = (seconds) => {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

const handleRecordBtnClick = () => {
  if (['idle', 'done', 'error'].includes(state.value)) {
    startRecording(() => {
      fetchHistory()
    })
  } else if (state.value === 'recording') {
    if (recordingTime.value < 1) {
      showToast('录音太短，请至少录制 1 秒')
      stopRecording(true) // abort sending
      return
    }
    stopRecording(false)
  }
}

watch(recordingTime, (newTime) => {
  if (state.value === 'recording') {
    if (newTime === 15) {
      showToast('建议分段输入，单次录音建议在 2-15 秒之间', 4000)
    } else if (newTime >= 30) {
      showToast('已达到最大录音时长（30秒），自动提交识别')
      stopRecording(false)
    }
  }
})

const handleCopyBtnClick = async () => {
  if (!transcriptText.value) return;
  try {
    await navigator.clipboard.writeText(transcriptText.value);
    showToast('复制成功！');
  } catch (err) {
    showToast('复制失败，请手动复制', 3000);
  }
};

const handleGenerateSummary = async () => {
  const textToSummarize = transcriptText.value;
  if (!textToSummarize) return;
  await generateSummary(textToSummarize);
};

const handleCopySummaryBtnClick = async () => {
  const success = await copySummary();
  if (success) {
    showToast('会议纪要复制成功！');
  } else {
    showToast('复制失败，请手动复制');
  }
};

onMounted(() => {
  fetchHistory()
})
</script>

<template>
  <div class="app-container">
    <header>
      <h1>VoiceFlow Input</h1>
      <div class="header-meta">
        <span class="status-badge cost-zero">本地识别，成本 0</span>
        <span 
          class="conn-dot" 
          :class="{ 'connected': isConnected, 'disconnected': !isConnected && !isConnError, 'error': isConnError }"
          title="WebSocket 连接状态"
        ></span>
        <div class="status-badge" :class="state">
          <span class="pulse-dot"></span>
          <span>{{ statusText }}</span>
          <span v-if="state === 'recording'" class="timer-text">{{ formatTime(recordingTime) }}</span>
          <div v-if="state === 'transcribing'" class="decoding-wave" aria-hidden="true">
            <span class="bar"></span>
            <span class="bar"></span>
            <span class="bar"></span>
            <span class="bar"></span>
            <span class="bar"></span>
          </div>
        </div>
      </div>
    </header>

    <main>
      <!-- Transcript Box -->
      <div class="transcript-container">
        <textarea
          :placeholder="['sending', 'transcribing'].includes(state) ? '正在为您处理录音，非实时逐字输出，请稍候...' : '语音识别结果将在此显示…'"
          readonly
          aria-label="转写结果"
          :value="transcriptText"
        ></textarea>

        <div class="transcript-footer">
          <div class="meta-badges">
            <span class="meta-text" v-if="latencyInfo">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
              {{ latencyInfo }}
            </span>
            <span class="meta-badge info" v-if="appliedCorrectionsCount > 0">
              已应用修正: {{ appliedCorrectionsCount }}
            </span>
          </div>
          <div class="actions">
            <button class="secondary-btn" :disabled="!transcriptText" @click="handleCopyBtnClick" aria-label="复制文本">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
              复制
            </button>
          </div>
        </div>
      </div>

      <!-- Meeting Minutes Agent Panel -->
      <div class="meeting-agent-panel">
        <div class="panel-header">
          <h2>会议纪要 Agent</h2>
          <button 
            class="primary-btn sm-btn" 
            :disabled="!transcriptText || summaryLoading"
            @click="handleGenerateSummary"
          >
            <span v-if="summaryLoading" class="spinner"></span>
            {{ summaryLoading ? '正在生成...' : '生成会议纪要' }}
          </button>
        </div>
        
        <div v-if="summaryError" class="agent-error-box">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
          {{ summaryError }}
        </div>

        <div v-if="summaryMarkdown && !summaryLoading" class="summary-result-area">
          <div class="summary-meta" v-if="summaryMeta">
            <span class="meta-badge">提供商: {{ summaryMeta.provider }}</span>
            <span class="meta-badge">模型: {{ summaryMeta.model }}</span>
            <span class="meta-badge" v-if="summaryMeta.latency_ms">耗时: {{ summaryMeta.latency_ms }}ms</span>
          </div>
          <div class="summary-markdown-content">
            <pre>{{ summaryMarkdown }}</pre>
          </div>
          <div class="summary-actions">
            <button class="secondary-btn" @click="handleCopySummaryBtnClick">复制纪要</button>
            <button class="secondary-btn" @click="downloadSummary">下载 Markdown</button>
          </div>
        </div>
      </div>

      <!-- Main Error Bar -->
      <div v-if="state === 'error' && errorText" class="error-bar" role="alert">
        <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
        <span>{{ errorText }}</span>
      </div>

      <!-- Record Control -->
      <div class="controls">
        <button 
          class="primary-btn" 
          :class="{ 'recording': state === 'recording', 'busy': ['sending', 'transcribing'].includes(state) }" 
          @click="handleRecordBtnClick"
        >
          <span class="btn-icon">
            <svg v-if="['idle', 'done', 'error'].includes(state)" xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="22"></line></svg>
            <svg v-else-if="state === 'recording'" xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><rect x="5" y="5" width="14" height="14" rx="2" ry="2"></rect></svg>
            <div v-else-if="state === 'transcribing'" class="decoding-wave" aria-hidden="true">
              <span class="bar"></span>
              <span class="bar"></span>
              <span class="bar"></span>
              <span class="bar"></span>
              <span class="bar"></span>
            </div>
            <svg v-else class="spin" xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-6.22-8.56"></path></svg>
          </span>
          <span>
            {{ state === 'recording' ? '停止录音' : (['sending', 'transcribing'].includes(state) ? '处理中' : (state === 'done' ? '重新录音' : '开始录音')) }}
          </span>
        </button>
      </div>

      <!-- History Section -->
      <div class="history-container">
        <div class="history-header">
          <h2>
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 9l-5 5-4-4-5 5"/></svg>
            历史记录
          </h2>
          <div class="history-actions">
            <label class="history-toggle-label">
              <input type="checkbox" v-model="hideErrorHistory">
              隐藏失败记录
            </label>
            <button class="secondary-btn" @click="fetchHistory" aria-label="刷新历史">刷新</button>
            <button class="secondary-btn danger" @click="clearHistory" aria-label="清空历史">清空</button>
            <button class="secondary-btn" @click="exportMarkdown" aria-label="导出 Markdown">导出 MD</button>
          </div>
        </div>

        <div v-if="historyError" class="error-bar" role="alert">
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
          <span>{{ historyError }}</span>
        </div>

        <div class="history-list">
          <div v-if="!historyItems || historyItems.length === 0" class="history-empty">
            暂无历史记录
          </div>
          <template v-else>
            <div 
              v-for="item in historyItems" 
              :key="item.id" 
              class="history-item" 
              :class="{ 'error': !item.success }"
              v-show="!(!item.success && hideErrorHistory)"
            >
            <div class="history-item-header">
              <span class="hist-time">{{ new Date(item.created_at).toLocaleString('zh-CN') }}</span>
              <span class="hist-stats">
                引擎: {{ item.engine || '未知' }} | 
                <template v-if="item.audio_duration_ms">音频: {{ item.audio_duration_ms }}ms | </template>
                <template v-if="item.latency_ms || item.total_ms">耗时: {{ item.total_ms || item.latency_ms }}ms</template>
              </span>
            </div>
            <div class="history-item-body">
              {{ !item.success ? `[失败] ${item.error_code || '未知错误'}` : (item.final_text || item.raw_text || '') }}
            </div>
            </div>
          </template>
        </div>
      </div>
    </main>
  </div>

  <!-- Global Toast -->
  <div class="toast" :class="{ 'hidden': !toastVisible }" role="status" aria-live="polite">{{ toastMessage }}</div>
</template>
