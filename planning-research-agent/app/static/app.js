// Import markdown-it for better client-side rendering
const script = document.createElement('script');
script.src = 'https://cdn.jsdelivr.net/npm/markdown-it@14.1.0/dist/markdown-it.min.js';
document.head.appendChild(script);

const chatContainer = document.getElementById('chat-container');
const chatForm = document.getElementById('chat-form');
const scenarioInput = document.getElementById('scenario-input');
const sendBtn = document.getElementById('send-btn');
const logsDiv = document.getElementById('logs');
const statusBar = document.getElementById('status-bar');
const statusText = document.getElementById('status-text');

const suggestionMap = {
    "🚢 Red Sea Logistics Disruption": "Our primary logistics partner in the Red Sea has suspended operations due to security risks. Rerouting around Africa is adding 14 days to lead times. Build an inventory transshipment strategy for European hubs.",
    "📱 300-Unit Demand Spike": "A sudden social media trend has caused a 300-unit demand spike for iPhones in our London store, but our regional warehouse is stock-out. Research emergency cross-docking and inventory balancing tactics.",
    "🏭 Supplier Bankruptcy in APAC": "Our primary circuit board supplier in Vietnam has filed for bankruptcy. We have a product launch in 45 days. Research emergency dual-sourcing strategies and APAC-based alternative suppliers.",
    "🔋 Lithium Price Surge Mitigation": "Global lithium prices have surged 40% this week affecting our EV battery procurement. Research alternative battery chemistries (LFP vs NMC) and long-term price hedging strategies in the supply chain."
};

function useSuggestion(btn) {
    const key = btn.innerText.trim();
    if (suggestionMap[key]) {
        scenarioInput.value = suggestionMap[key];
        chatForm.dispatchEvent(new Event('submit'));
    }
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const scenario = scenarioInput.value.trim();
    if (!scenario) return;

    // Reset UI
    appendMessage('user', scenario);
    scenarioInput.value = '';
    logsDiv.innerHTML = '';
    statusBar.classList.remove('hidden');
    setLoading(true);

    const eventSource = new EventSource(`/chat?scenario=${encodeURIComponent(scenario)}`);
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'log') {
            appendLog(data.content);
        } else if (data.type === 'final_dashboard') {
            renderDashboard(data.content);
            eventSource.close();
            setLoading(false);
            statusBar.classList.add('hidden');
        } else if (data.type === 'error') {
            appendMessage('error', data.content);
            eventSource.close();
            setLoading(false);
            statusBar.classList.add('hidden');
        }
    };

    eventSource.onerror = () => {
        appendMessage('error', 'Connection lost or server error.');
        eventSource.close();
        setLoading(false);
        statusBar.classList.add('hidden');
    };
});

function renderDashboard(dashboardData) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex items-start gap-4';
    
    // Convert [1] citations to clickable badges based on the sources array
    let summaryHtml = dashboardData.executive_summary;
    if (dashboardData.sources) {
        dashboardData.sources.forEach(src => {
            const regex = new RegExp(`\\[${src.id}\\]`, 'g');
            summaryHtml = summaryHtml.replace(regex, `<a href="${src.url}" target="_blank" class="citation-badge" title="${src.title}">[${src.id}]</a>`);
        });
    }

    let timelineHtml = dashboardData.timeline.map((step, index) => `
        <div class="flex relative pb-6">
            <div class="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 z-10">${index + 1}</div>
            ${index !== dashboardData.timeline.length - 1 ? '<div class="absolute top-6 left-3 w-px h-full bg-blue-200"></div>' : ''}
            <div class="ml-4">
                <h4 class="text-sm font-bold text-slate-800">${step.phase}</h4>
                <p class="text-sm text-slate-700 font-semibold mt-1">${step.action}</p>
                <p class="text-xs text-slate-500 mt-1">${step.rationale}</p>
            </div>
        </div>
    `).join('');

    let riskHtml = dashboardData.risk_matrix.map(risk => {
        const color = risk.severity.toLowerCase() === 'high' ? 'bg-red-100 text-red-700 border-red-200' : 'bg-amber-100 text-amber-700 border-amber-200';
        return `
        <div class="p-3 border rounded-lg bg-slate-50 mb-2 border-slate-200">
            <div class="flex justify-between items-start mb-2">
                <span class="font-bold text-sm text-slate-800">${risk.risk}</span>
                <span class="text-[10px] font-bold px-2 py-1 rounded uppercase border ${color}">${risk.severity}</span>
            </div>
            <p class="text-xs text-slate-600"><span class="font-bold text-slate-700">Mitigation:</span> ${risk.mitigation}</p>
        </div>
        `;
    }).join('');

    let sourcesHtml = dashboardData.sources.map(src => `
        <a href="${src.url}" target="_blank" class="block p-3 bg-white border border-slate-200 rounded-lg hover:border-blue-400 hover:shadow-sm transition-all mb-2">
            <div class="text-xs font-bold text-blue-600 mb-1">Source [${src.id}]</div>
            <div class="text-sm font-semibold text-slate-700 truncate">${src.title}</div>
            <div class="text-[10px] text-slate-400 truncate mt-1">${src.url}</div>
        </a>
    `).join('');

    messageDiv.innerHTML = `
        <div class="bg-blue-600 text-white p-3 rounded-xl flex-shrink-0 shadow-md">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
        </div>
        <div class="w-full max-w-[90%] dashboard-report" id="report-${Date.now()}">
            <div class="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                <!-- Header -->
                <div class="bg-slate-800 p-6 flex justify-between items-center">
                    <div>
                        <div class="text-blue-400 text-xs font-bold tracking-widest uppercase mb-1">Strategic Intelligence Brief</div>
                        <h2 class="text-xl font-black text-white">${dashboardData.title}</h2>
                    </div>
                    <button onclick="downloadReport(this)" class="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-bold transition-colors flex items-center gap-2">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                        Export Report
                    </button>
                </div>
                
                <div class="p-6">
                    <!-- Summary & Impact -->
                    <div class="grid grid-cols-3 gap-6 mb-8">
                        <div class="col-span-2">
                            <h3 class="text-slate-800 font-bold border-b border-slate-100 pb-2 mb-3">Executive Summary</h3>
                            <p class="text-sm text-slate-600 leading-relaxed">${summaryHtml}</p>
                        </div>
                        <div class="bg-blue-50 border border-blue-100 p-4 rounded-xl">
                            <h3 class="text-blue-800 font-bold mb-2 flex items-center gap-2">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                Op-Ex Impact
                            </h3>
                            <p class="text-xs text-blue-700 font-medium">${dashboardData.financial_operational_impact}</p>
                        </div>
                    </div>

                    <!-- Timeline & Risk -->
                    <div class="grid grid-cols-2 gap-8 mb-8">
                        <div>
                            <h3 class="text-slate-800 font-bold border-b border-slate-100 pb-2 mb-4">Strategic Timeline</h3>
                            ${timelineHtml}
                        </div>
                        <div>
                            <h3 class="text-slate-800 font-bold border-b border-slate-100 pb-2 mb-4">Risk Matrix</h3>
                            ${riskHtml}
                        </div>
                    </div>
                </div>
                
                <!-- Footer / Sources -->
                <div class="bg-slate-50 border-t border-slate-200 p-6">
                    <h3 class="text-slate-800 font-bold mb-4 flex items-center gap-2">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
                        Verified Sources
                    </h3>
                    <div class="grid grid-cols-2 gap-3">
                        ${sourcesHtml}
                    </div>
                </div>
            </div>
        </div>
    `;

    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function downloadReport(btn) {
    const reportNode = btn.closest('.dashboard-report');
    // Hide the button for print
    btn.style.display = 'none';
    
    // Create a temporary iframe for clean printing
    const iframe = document.createElement('iframe');
    iframe.style.position = 'fixed';
    iframe.style.right = '0';
    iframe.style.bottom = '0';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = '0';
    document.body.appendChild(iframe);
    
    // Include Tailwind for print styles
    const styles = `<script src="https://cdn.tailwindcss.com"></script><style>body { padding: 20px; } .citation-badge { text-decoration: none; color: #2563eb; font-weight: bold; }</style>`;
    
    iframe.contentWindow.document.open();
    iframe.contentWindow.document.write('<html><head>' + styles + '</head><body>' + reportNode.innerHTML + '</body></html>');
    iframe.contentWindow.document.close();
    
    // Wait for Tailwind to process, then print
    setTimeout(() => {
        iframe.contentWindow.focus();
        iframe.contentWindow.print();
        document.body.removeChild(iframe);
        btn.style.display = 'flex'; // Restore button
    }, 1000);
}

function appendMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex items-start gap-4 ' + (role === 'user' ? 'flex-row-reverse' : '');
    
    let iconColor = 'bg-blue-600 text-white shadow-md';
    let bgColor = 'bg-slate-50 border border-slate-200';
    let roundedClass = 'rounded-tl-none';
    
    if (role === 'user') {
        iconColor = 'bg-slate-800 text-white shadow-md';
        bgColor = 'bg-blue-600 text-white';
        roundedClass = 'rounded-tr-none';
    } else if (role === 'error') {
        iconColor = 'bg-red-600 text-white shadow-md';
        bgColor = 'bg-red-50 text-red-700 border border-red-200';
    }

    const icon = role === 'user' ? 
        `<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>` :
        `<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>`;

    messageDiv.innerHTML = `
        <div class="${iconColor} p-3 rounded-xl flex-shrink-0">
            ${icon}
        </div>
        <div class="relative group max-w-[85%]">
            <div class="${bgColor} p-6 rounded-2xl ${roundedClass} prose prose-slate">
                ${content}
            </div>
            ${role === 'agent' ? `
                <button onclick="copyToClipboard(this)" class="absolute top-2 right-2 p-2 bg-white/80 hover:bg-white rounded-lg opacity-0 group-hover:opacity-100 transition-opacity shadow-sm border border-slate-200" title="Copy to Clipboard">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                </button>
            ` : ''}
        </div>
    `;

function copyToClipboard(btn) {
    const text = btn.parentElement.innerText;
    navigator.clipboard.writeText(text).then(() => {
        const originalIcon = btn.innerHTML;
        btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>`;
        setTimeout(() => btn.innerHTML = originalIcon, 2000);
    });
}
    
    // Make links clickable and open in new tab
    const links = messageDiv.querySelectorAll('a');
    links.forEach(link => {
        link.setAttribute('target', '_blank');
        link.classList.add('text-blue-500', 'hover:underline', 'font-bold');
    });

    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function appendLog(text) {
    const logItem = document.createElement('div');
    logItem.className = 'flex items-center gap-2 text-[10px] font-mono text-slate-500 bg-white p-2 rounded border border-slate-100 shadow-sm';
    logItem.innerHTML = `
        <span class="w-1 h-1 bg-green-500 rounded-full animate-pulse"></span>
        <span>${text}</span>
    `;
    logsDiv.appendChild(logItem);
    logsDiv.scrollTop = logsDiv.scrollHeight;
}

function setLoading(isLoading) {
    if (isLoading) {
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<span class="loading-dots">Thinking</span>';
        sendBtn.classList.add('opacity-75', 'cursor-not-allowed');
        statusText.innerText = 'Agent is researching...';
    } else {
        sendBtn.disabled = false;
        sendBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            <span>Analyze</span>`;
        sendBtn.classList.remove('opacity-75', 'cursor-not-allowed');
    }
}
