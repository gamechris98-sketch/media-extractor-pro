document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    
    const startBtn = document.getElementById('start-btn');
    const urlTextarea = document.getElementById('urls');
    const logsContainer = document.getElementById('logs');
    const statusBadge = document.getElementById('status-badge');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar-fill');
    const percentText = document.getElementById('percent-text');
    const currentFileText = document.getElementById('current-file');
    
    let socket = null;

    function connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        console.log(`Connecting to ${wsUrl}`);
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            addLog('서버에 연결되었습니다. (안정적인 백엔드 모드)');
            statusBadge.innerText = '준비됨';
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'log') {
                addLog(data.message);
            } else if (data.type === 'progress') {
                progressContainer.classList.remove('hidden');
                progressBar.style.width = `${data.percent}%`;
                percentText.innerText = `${data.percent}%`;
                currentFileText.innerText = data.filename;
                statusBadge.innerText = '진행 중';
            } else if (data.type === 'finished') {
                addLog(`완료: ${data.filename}`, true, data.filename);
            } else if (data.type === 'all_done') {
                statusBadge.innerText = '완료';
                statusBadge.style.color = '#34C759';
                startBtn.disabled = false;
                startBtn.querySelector('span').innerText = '추출 시작';
                addLog('--- 모든 작업이 종료되었습니다 ---');
            }
        };

        socket.onclose = () => {
            addLog('서버와 연결이 끊어졌습니다. 재시도 중...');
            setTimeout(connect, 3000);
        };
        
        socket.onerror = (err) => {
            addLog('WebSocket 연결 오류 발생.');
            console.error(err);
        };
    }

    function addLog(message, isDownload = false, filename = '') {
        const now = new Date();
        const timeStr = now.getHours().toString().padStart(2, '0') + ':' + 
                        now.getMinutes().toString().padStart(2, '0') + ':' + 
                        now.getSeconds().toString().padStart(2, '0');
        
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
        if (isDownload) {
            entry.innerHTML = `<span class="log-time">${timeStr}</span> 
                               <span>${message}</span>
                               <a href="/downloads/${filename}" download class="download-link">
                                  <i data-lucide="download" style="width:14px; height:14px; vertical-align:middle; margin-left:5px;"></i> 기기에 저장
                               </a>`;
            lucide.createIcons();
        } else {
            entry.innerHTML = `<span class="log-time">${timeStr}</span> <span>${message}</span>`;
        }
        
        const emptyMsg = logsContainer.querySelector('.empty-msg');
        if (emptyMsg) emptyMsg.remove();
        
        logsContainer.appendChild(entry);
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }

    startBtn.addEventListener('click', () => {
        const urls = urlTextarea.value.trim().split('\n').filter(u => u.trim() !== '');
        if (urls.length === 0) {
            alert('URL을 하나 이상 입력해 주세요.');
            return;
        }

        const format = document.querySelector('input[name="format"]:checked').value;

        if (socket && socket.readyState === WebSocket.OPEN) {
            startBtn.disabled = true;
            startBtn.querySelector('span').innerText = '처리 중...';
            statusBadge.innerText = '분석 중';
            
            logsContainer.innerHTML = ''; 
            progressContainer.classList.add('hidden');
            progressBar.style.width = '0%';
            
            socket.send(JSON.stringify({
                type: 'start',
                urls: urls,
                format: format
            }));
            
            addLog(`${urls.length}개의 작업을 서버 대기열에 추가했습니다.`);
        } else {
            addLog('서버와 연결되어 있지 않습니다. 잠시 후 다시 시도해 주세요.');
        }
    });

    connect();
});
