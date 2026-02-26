// Konfigurasi DOM Elements
const DOMElements = {
    chatBox: document.getElementById('chat-box'),
    chatInput: document.getElementById('chat-input'),
    btnSend: document.getElementById('btn-send'),
    themeToggle: document.getElementById('theme-toggle'),
    dropZone: document.getElementById('drop-zone'),
    fileInput: document.getElementById('file-input'),
    btnIngest: document.getElementById('btn-ingest'),
    docList: document.getElementById('document-list'),
    llmSelect: document.getElementById('llm-select'),
    topkSlider: document.getElementById('topk-slider'),
    ingestProgress: document.getElementById('ingest-progress-container'),
    ingestLogs: document.getElementById('ingest-logs'),
    aiStatusIndicator: document.querySelector('.ai-status')
};

// State Aplikasi
const AppState = {
    isChatting: false,
    pollInterval: null
};

// ======= CORE FUNCTIONS =======

// 1. Theme Management
function toggleTheme() {
    const isDark = document.body.classList.toggle('dark-theme');
    DOMElements.themeToggle.innerText = isDark ? '🌓' : '☀️';
}
DOMElements.themeToggle.addEventListener('click', toggleTheme);


// 2. Chat UI Management
function addMessage(text, isAI = false, sources = []) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message');
    msgDiv.classList.add(isAI ? 'ai-msg' : 'user-msg');

    const avatar = document.createElement('div');
    avatar.classList.add('msg-avatar');
    avatar.innerText = isAI ? 'AI' : 'U';

    const bubble = document.createElement('div');
    bubble.classList.add('msg-bubble');

    // Parse Markdown untuk AI
    if (isAI) {
        let msgContent = `<div class="markdown-body">${marked.parse(text)}</div>`;
        if (sources && sources.length > 0) {
            msgContent += `<div class="markdown-body"><hr><p><strong>Sumber Referensi:</strong><br>`;
            sources.forEach(src => {
                msgContent += `<span class="citation">${src}</span> `;
            });
            msgContent += `</p></div>`;
        }
        bubble.innerHTML = msgContent;
    } else {
        bubble.innerText = text; // Keamanan XSS input user
    }

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(bubble);
    DOMElements.chatBox.appendChild(msgDiv);

    // Scroll ke bawah
    DOMElements.chatBox.scrollTop = DOMElements.chatBox.scrollHeight;
}

function showTypingIndicator() {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', 'ai-msg');
    msgDiv.id = 'typing-indicator-msg';

    const avatar = document.createElement('div');
    avatar.classList.add('msg-avatar');
    avatar.innerText = 'AI';

    const bubble = document.createElement('div');
    bubble.classList.add('msg-bubble', 'typing-indicator');
    bubble.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(bubble);
    DOMElements.chatBox.appendChild(msgDiv);
    DOMElements.chatBox.scrollTop = DOMElements.chatBox.scrollHeight;
}

function removeTypingIndicator() {
    const typingMsg = document.getElementById('typing-indicator-msg');
    if (typingMsg) typingMsg.remove();
}


// 3. API Integraction (Chat)
async function sendQuery() {
    const query = DOMElements.chatInput.value.trim();
    if (!query || AppState.isChatting) return;

    // Reset Input
    DOMElements.chatInput.value = '';
    DOMElements.chatInput.style.height = 'auto'; // Reset text area

    // UI Update
    addMessage(query, false);
    showTypingIndicator();
    AppState.isChatting = true;
    DOMElements.btnSend.disabled = true;

    try {
        const payload = {
            query: query,
            k: parseInt(DOMElements.topkSlider.value),
            use_local: DOMElements.llmSelect.value === 'local'
        };

        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (res.ok) {
            removeTypingIndicator();
            addMessage(data.answer, true, data.sources);
        } else {
            throw new Error(data.error || 'Server error occurred');
        }
    } catch (err) {
        removeTypingIndicator();
        addMessage(`Maaf, terjadi kesalahan: ${err.message}`, true);
    } finally {
        AppState.isChatting = false;
        DOMElements.btnSend.disabled = false;
    }
}


// 4. Ingestion & Document Management
async function fetchDocuments() {
    try {
        const res = await fetch('/api/documents');
        const data = await res.json();

        DOMElements.docList.innerHTML = '';
        if (data.documents && data.documents.length > 0) {
            data.documents.forEach(doc => {
                const li = document.createElement('li');
                li.innerText = doc;
                DOMElements.docList.appendChild(li);
            });
        } else {
            DOMElements.docList.innerHTML = '<li class="text-secondary" style="background: none; padding: 0;">Belum ada dokumen.</li>';
        }
    } catch (e) {
        console.error("Gagal mengambil data dokumen:", e);
    }
}

async function uploadFile(file) {
    if (!file || file.type !== 'application/pdf') {
        alert("Mohon unggah file dengan format PDF.");
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        DOMElements.dropZone.querySelector('p').innerText = "Mengunggah...";
        const res = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (res.ok) {
            DOMElements.dropZone.querySelector('p').innerHTML = `Berhasil! Seret PDF lagi atau <span class="highlight">Pilih File</span>`;
            fetchDocuments(); // Refresh list
        } else {
            throw new Error("Gagal upload");
        }
    } catch (error) {
        DOMElements.dropZone.querySelector('p').innerHTML = `Gagal. Coba lagi atau <span class="highlight">Pilih File</span>`;
        alert("Upload gagal: " + error.message);
    }
}

// Ingestion Trigger & Polling
async function pollIngestionStatus() {
    try {
        const res = await fetch('/api/ingest/status');
        const data = await res.json();

        // Render Logs
        DOMElements.ingestLogs.innerHTML = data.progress_logs.map(log =>
            `<div class="log-line">> ${log}</div>`
        ).join('');

        // Auto scroll
        DOMElements.ingestLogs.scrollTop = DOMElements.ingestLogs.scrollHeight;

        if (!data.is_running) {
            clearInterval(AppState.pollInterval);
            DOMElements.btnIngest.disabled = false;
            DOMElements.btnIngest.innerText = "Proses Pemahaman (Ingestion)";
            DOMElements.ingestProgress.querySelector('.loader-spinner').style.display = 'none';
            DOMElements.aiStatusIndicator.classList.remove('busy');
            DOMElements.aiStatusIndicator.innerHTML = '<span class="status-dot"></span> System Ready';
        }
    } catch (e) {
        console.error("Polling error", e);
    }
}

async function startIngestion() {
    try {
        const res = await fetch('/api/ingest', { method: 'POST' });

        if (res.ok) {
            DOMElements.btnIngest.disabled = true;
            DOMElements.btnIngest.innerText = "Membaca Dokumen...";
            DOMElements.ingestProgress.classList.remove('hidden');
            DOMElements.ingestProgress.querySelector('.loader-spinner').style.display = 'block';
            DOMElements.aiStatusIndicator.classList.add('busy');
            DOMElements.aiStatusIndicator.innerHTML = '<span class="status-dot"></span> Ingestion Progress...';

            // Start Polling 
            if (AppState.pollInterval) clearInterval(AppState.pollInterval);
            AppState.pollInterval = setInterval(pollIngestionStatus, 1500);
        } else {
            const err = await res.json();
            alert(err.message || "Gagal memulai Ingestion.");
        }
    } catch (error) {
        alert("Gagal koneksi ke server untuk Ingestion.");
    }
}


// ======= EVENT LISTENERS =======

// Chat Input auto-resize
DOMElements.chatInput.addEventListener('input', function () {
    this.style.height = 'auto';
    let newHeight = this.scrollHeight;
    this.style.height = newHeight > 150 ? '150px' : newHeight + 'px';
});

// Send Chat (Enter or Button)
DOMElements.chatInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendQuery();
    }
});
DOMElements.btnSend.addEventListener('click', sendQuery);

// Drag & Drop Upload Events
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    DOMElements.dropZone.addEventListener(eventName, preventDefaults, false);
});
function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}
['dragenter', 'dragover'].forEach(eventName => {
    DOMElements.dropZone.addEventListener(eventName, () => DOMElements.dropZone.classList.add('dragover'), false);
});
['dragleave', 'drop'].forEach(eventName => {
    DOMElements.dropZone.addEventListener(eventName, () => DOMElements.dropZone.classList.remove('dragover'), false);
});
DOMElements.dropZone.addEventListener('drop', (e) => {
    let dt = e.dataTransfer;
    let files = dt.files;
    if (files.length > 0) uploadFile(files[0]);
});

// Click Upload Zone
DOMElements.dropZone.addEventListener('click', () => DOMElements.fileInput.click());
DOMElements.fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) uploadFile(e.target.files[0]);
});

// Ingestion Button
DOMElements.btnIngest.addEventListener('click', startIngestion);


// Inisialisasi awal
document.addEventListener("DOMContentLoaded", () => {
    fetchDocuments();
});
