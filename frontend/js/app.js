const elements = {
    connIndicator: document.getElementById('conn-indicator'),
    statusBadge: document.getElementById('status-badge'),
    statusText: document.getElementById('status-text'),
    transcriptBox: document.getElementById('transcript-box'),
    latencyLabel: document.getElementById('latency-label'),
    recordBtn: document.getElementById('record-btn'),
    recordBtnText: document.getElementById('record-btn-text'),
    micIcon: document.getElementById('mic-icon'),
    stopIcon: document.getElementById('stop-icon'),
    spinIcon: document.getElementById('spin-icon'),
    copyBtn: document.getElementById('copy-btn'),
    toast: document.getElementById('toast'),
    errorBar: document.getElementById('error-bar'),
    errorText: document.getElementById('error-text')
};

let state = 'idle'; // idle | recording | sending | transcribing | done | error
let mediaRecorder = null;
let socket = null;
let audioStream = null;

function setState(newState, errorMessage = '') {
    // Reset previous styles
    elements.statusBadge.className = 'status-badge';
    elements.recordBtn.className = 'primary-btn';
    elements.errorBar.classList.add('hidden');
    
    state = newState;
    elements.statusBadge.classList.add(state);

    const setIcon = (mic, stop, spin) => {
        mic ? elements.micIcon.classList.remove('hidden') : elements.micIcon.classList.add('hidden');
        stop ? elements.stopIcon.classList.remove('hidden') : elements.stopIcon.classList.add('hidden');
        spin ? elements.spinIcon.classList.remove('hidden') : elements.spinIcon.classList.add('hidden');
    };

    switch (state) {
        case 'idle':
            elements.statusText.textContent = '准备就绪';
            elements.recordBtnText.textContent = '开始录音';
            setIcon(true, false, false);
            break;
            
        case 'recording':
            elements.statusText.textContent = '录音中...';
            elements.recordBtn.classList.add('recording');
            elements.recordBtnText.textContent = '停止录音';
            elements.copyBtn.disabled = true;
            elements.latencyLabel.textContent = '';
            elements.latencyLabel.classList.add('hidden');
            setIcon(false, true, false);
            break;
            
        case 'sending':
            elements.statusText.textContent = '发送中...';
            elements.recordBtn.classList.add('busy');
            elements.recordBtnText.textContent = '处理中';
            setIcon(false, false, true);
            break;
            
        case 'transcribing':
            elements.statusText.textContent = '识别中...';
            elements.recordBtn.classList.add('busy');
            elements.recordBtnText.textContent = '处理中';
            setIcon(false, false, true);
            break;
            
        case 'done':
            elements.statusText.textContent = '识别完成';
            elements.recordBtnText.textContent = '重新录音';
            elements.copyBtn.disabled = false;
            setIcon(true, false, false);
            break;
            
        case 'error':
            elements.statusText.textContent = '发生错误';
            elements.recordBtnText.textContent = '重试';
            elements.errorText.textContent = errorMessage || '发生未知错误';
            elements.errorBar.classList.remove('hidden');
            setIcon(true, false, false);
            break;
    }
}

function updateConnectionState(isConnected, isError = false) {
    elements.connIndicator.className = 'conn-dot';
    if (isError) {
        elements.connIndicator.classList.add('error');
    } else if (isConnected) {
        elements.connIndicator.classList.add('connected');
    } else {
        elements.connIndicator.classList.add('disconnected');
    }
}

async function startRecording() {
    elements.transcriptBox.value = '';
    setState('idle');
    
    try {
        // 1. Get microphone access
        audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // 2. Connect to WebSocket mock
        socket = new WebSocket('ws://localhost:8000/ws/transcribe');
        
        socket.onopen = () => {
            updateConnectionState(true);
            
            // Send start protocol
            socket.send(JSON.stringify({
                type: "start",
                session_id: "local-demo",
                format: "webm"
            }));
            
            setState('recording');
            
            // 3. Setup MediaRecorder
            mediaRecorder = new MediaRecorder(audioStream, { mimeType: 'audio/webm' });
            
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {
                    socket.send(event.data);
                }
            };
            
            mediaRecorder.onstop = () => {
                setState('sending');
                if (socket.readyState === WebSocket.OPEN) {
                    socket.send(JSON.stringify({ type: "end" }));
                    setState('transcribing');
                }
            };

            // Request chunks every 250ms
            mediaRecorder.start(250);
        };

        socket.onmessage = (event) => {
            try {
                const res = JSON.parse(event.data);
                if (res.type === 'ack') {
                    console.log('Received ack');
                } else if (res.type === 'transcription_result') {
                    if (res.result && res.result.success && res.result.data) {
                        elements.transcriptBox.value = res.result.data.final_text || res.result.data.raw_text || '';
                        
                        if (res.result.data.latency_ms) {
                            elements.latencyLabel.textContent = `引擎: ${res.result.data.engine || '未知'} | 延迟: ${res.result.data.latency_ms}ms`;
                            elements.latencyLabel.classList.remove('hidden');
                        }
                        
                        setState('done');
                        socket.close();
                    } else if (res.result && res.result.error) {
                        setState('error', res.result.error.message || '识别失败');
                        socket.close();
                    }
                } else if (res.type === 'error') {
                    if (res.result && res.result.error) {
                        setState('error', res.result.error.message || '发生错误');
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
            setState('error', 'WebSocket 连接失败，请确保后端服务运行于 ws://localhost:8000/ws/transcribe');
            cleanup();
        };

        socket.onclose = () => {
            updateConnectionState(false);
            if (state === 'recording' || state === 'transcribing' || state === 'sending') {
                setState('error', '连接意外断开');
            }
            cleanup();
        };

    } catch (err) {
        console.error('Microphone access error:', err);
        if (err.name === 'NotAllowedError') {
            setState('error', '未获得麦克风权限，请在浏览器中允许麦克风访问');
        } else if (err.name === 'NotFoundError') {
            setState('error', '未检测到麦克风设备');
        } else {
            setState('error', `麦克风错误: ${err.message}`);
        }
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
}

function cleanup() {
    if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
        audioStream = null;
    }
    mediaRecorder = null;
    socket = null;
}

// Event Listeners
elements.recordBtn.addEventListener('click', () => {
    if (state === 'idle' || state === 'done' || state === 'error') {
        startRecording();
    } else if (state === 'recording') {
        stopRecording();
    }
});

elements.copyBtn.addEventListener('click', async () => {
    const text = elements.transcriptBox.value;
    if (!text) return;
    
    try {
        await navigator.clipboard.writeText(text);
        
        elements.toast.classList.remove('hidden');
        setTimeout(() => {
            elements.toast.classList.add('hidden');
        }, 2000);
    } catch (err) {
        console.error('Copy failed:', err);
        setState('error', '复制失败，请手动选择复制');
    }
});
