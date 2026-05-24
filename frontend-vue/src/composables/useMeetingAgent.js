import { ref } from 'vue';

export function useMeetingAgent() {
  const summaryMarkdown = ref('');
  const summaryLoading = ref(false);
  const summaryError = ref('');
  const summaryMeta = ref(null);

  const generateSummary = async (transcriptText) => {
    if (!transcriptText) return;
    
    summaryLoading.value = true;
    summaryError.value = '';
    summaryMarkdown.value = '';
    summaryMeta.value = null;

    try {
      const response = await fetch('http://localhost:8000/ai/meeting-summary', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          transcript: transcriptText,
          mode: 'minutes',
          include_original: true
        })
      });

      // Network error but returned 5xx/4xx without CORS blocking
      if (!response.ok && response.status >= 500) {
        throw new Error('SERVER_ERROR');
      }

      let data;
      try {
        data = await response.json();
      } catch (err) {
        throw new Error('INVALID_JSON');
      }

      if (!data.success) {
        if (data.error && data.error.code === 'CONFIG_ERROR') {
          summaryError.value = '会议纪要 Agent 未启用，请在后端配置 API key。';
        } else {
          summaryError.value = data.error ? data.error.message : '生成失败，请重试。';
        }
        summaryLoading.value = false;
        return;
      }

      summaryMarkdown.value = data.data.summary_markdown || '';
      summaryMeta.value = {
        provider: data.data.provider,
        model: data.data.model,
        latency_ms: data.meta ? data.meta.latency_ms : null
      };
      
    } catch (err) {
      console.error('Meeting Agent Error:', err);
      if (err.message === 'SERVER_ERROR' || err.message === 'INVALID_JSON' || err.message === 'Failed to fetch') {
        summaryError.value = '会议纪要服务不可用，请确认后端已启动。';
      } else {
        summaryError.value = '生成会议纪要时发生未知错误。';
      }
    } finally {
      summaryLoading.value = false;
    }
  };

  const copySummary = async () => {
    if (!summaryMarkdown.value) return false;
    try {
      await navigator.clipboard.writeText(summaryMarkdown.value);
      return true;
    } catch (err) {
      console.error('Copy failed:', err);
      return false;
    }
  };

  const downloadSummary = () => {
    if (!summaryMarkdown.value) return;
    
    const now = new Date();
    const yyyy = now.getFullYear();
    const MM = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    const HH = String(now.getHours()).padStart(2, '0');
    const mm = String(now.getMinutes()).padStart(2, '0');
    
    const filename = `voiceflow-meeting-summary-${yyyy}${MM}${dd}-${HH}${mm}.md`;
    
    const blob = new Blob([summaryMarkdown.value], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return {
    summaryMarkdown,
    summaryLoading,
    summaryError,
    summaryMeta,
    generateSummary,
    copySummary,
    downloadSummary
  };
}
