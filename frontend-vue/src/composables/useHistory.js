import { ref } from 'vue';

export function useHistory() {
  const historyItems = ref([]);
  const historyError = ref('');

  const fetchHistory = async () => {
    historyError.value = '';
    try {
      const res = await fetch('http://localhost:8000/history');
      if (!res.ok) throw new Error('Failed to fetch history');
      
      const data = await res.json();
      let items = [];
      if (data.success && data.data) {
        items = Array.isArray(data.data) ? data.data : (data.data.items || []);
      } else if (Array.isArray(data)) {
        items = data;
      }
      historyItems.value = items.slice(0, 50);
    } catch (err) {
      console.error('fetchHistory error:', err);
      historyError.value = '获取历史记录失败';
    }
  };

  const clearHistory = async () => {
    historyError.value = '';
    try {
      const res = await fetch('http://localhost:8000/history', { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to clear history');
      await fetchHistory();
    } catch (err) {
      console.error('clearHistory error:', err);
      historyError.value = '清空历史记录失败';
    }
  };

  const exportMarkdown = async () => {
    historyError.value = '';
    try {
      const url = 'http://localhost:8000/export/markdown?limit=50&success_only=true';
      const res = await fetch(url);
      if (!res.ok) throw new Error('Export failed');
      
      const text = await res.text();
      const blob = new Blob([text], { type: 'text/markdown' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'voiceflow_export.md';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(a.href);
    } catch (err) {
      console.error('exportMarkdown error:', err);
      historyError.value = '导出 Markdown 失败';
    }
  };

  return {
    historyItems,
    historyError,
    fetchHistory,
    clearHistory,
    exportMarkdown
  };
}
