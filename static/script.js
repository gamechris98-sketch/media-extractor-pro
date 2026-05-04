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
    
    // CORS 문제를 해결하기 위한 프록시 서버 경유
    const PROXY_URL = 'https://corsproxy.io/?';
    const TARGET_API = 'https://api.cobalt.tools/api/json';

    function addLog(message, isDownload = false, downloadUrl = '', filename = '') {
        const now = new Date();
        const timeStr = now.getHours().toString().padStart(2, '0') + ':' + 
                        now.getMinutes().toString().padStart(2, '0') + ':' + 
                        now.getSeconds().toString().padStart(2, '0');
        
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
        if (isDownload) {
            entry.innerHTML = `<span class="log-time">${timeStr}</span> 
                               <span>${message}</span>
                               <a href="${downloadUrl}" target="_blank" class="download-link">
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

    async function downloadMedia(url, isAudio) {
        try {
            addLog(`분석 중: ${url}`);
            
            // 프록시 서버를 통해 요청 전송
            const response = await fetch(PROXY_URL + encodeURIComponent(TARGET_API), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    url: url,
                    isAudioOnly: isAudio,
                    vQuality: '1080',
                    filenameStyle: 'pretty'
                })
            });

            if (!response.ok) {
                throw new Error(`API 응답 오류 (${response.status})`);
            }

            const result = await response.json();

            if (result.status === 'error') {
                addLog(`실패: ${result.text || '알 수 없는 오류'}`);
            } else if (result.status === 'stream' || result.status === 'redirect') {
                addLog(`추출 성공!`, true, result.url, 'media_file');
            } else if (result.status === 'picker') {
                addLog(`추출 성공!`, true, result.picker[0].url, 'media_file');
            }
        } catch (error) {
            addLog(`오류 발생: ${error.message}`);
            console.error(error);
        }
    }

    startBtn.addEventListener('click', async () => {
        const urls = urlTextarea.value.trim().split('\n').filter(u => u.trim() !== '');
        if (urls.length === 0) {
            alert('URL을 하나 이상 입력해 주세요.');
            return;
        }

        const isAudio = document.querySelector('input[name="format"]:checked').value === 'audio';

        startBtn.disabled = true;
        startBtn.querySelector('span').innerText = '처리 중...';
        statusBadge.innerText = '추출 중';
        
        logsContainer.innerHTML = ''; 
        
        for (const url of urls) {
            await downloadMedia(url, isAudio);
        }

        statusBadge.innerText = '완료';
        statusBadge.style.color = '#34C759';
        startBtn.disabled = false;
        startBtn.querySelector('span').innerText = '추출 시작';
        addLog('--- 모든 작업이 종료되었습니다 ---');
    });

    addLog('시스템 준비 완료 (프록시 모드)');
});
