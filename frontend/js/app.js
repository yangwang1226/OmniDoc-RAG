
let currentMode = 'search';
let currentMainTopic = '';
let currentDisplayType = 'opensource';

// 动态文案字典
const UI_TEXTS = {
    'opensource': {
        pageTitle: "OmniDoc-RAG - AI Writer",
        navBrand: '<i class="bi bi-robot"></i> OmniDoc-RAG',
        tabSearch: '<i class="bi bi-search"></i> 知识检索 (RAG)',
        tabWrite: '<i class="bi bi-pencil-square"></i> AI Writer',
        placeholderSearch: "输入需要检索的知识……",
        placeholderWrite: "输入想起草的文档主题（支持标书、合同、报告等）...",
        outlineTitle: "<i class=\"bi bi-list-nested\"></i> 根据知识库自动生成的起草大纲"
    },
    'company': {
        pageTitle: "大模型全域知识智写引擎",
        navBrand: '<i class="bi bi-diagram-3-fill"></i> 大模型全域知识智写引擎',
        tabSearch: '<i class="bi bi-search"></i> 全域知识查阅',
        tabWrite: '<i class="bi bi-pencil-square"></i> 知识增强智能伴写',
        placeholderSearch: "输入您想查阅的业务问题，例如：设备巡检的安全红线是什么？",
        placeholderWrite: "输入想起草的公文、标书或规章制度名称，例如：弱电系统运行管理规范",
        outlineTitle: "<i class=\"bi bi-list-nested\"></i> 基于历史档案生成的场景起草大纲"
    }
};

// 页面加载时初始化主题
async function initSysConfig() {
    try {
        const res = await fetch('/api/copilot/sys_config');
        const data = await res.json();
        if(data.code === 200) {
            currentDisplayType = data.data.display_type || 'opensource';
        }
    } catch (e) {
        console.error('获取配置失败，使用默认配置');
    }
    
    // 容错处理
    if(!UI_TEXTS[currentDisplayType]) currentDisplayType = 'opensource';
    const texts = UI_TEXTS[currentDisplayType];

    // 渲染文案
    document.getElementById('page-title').textContent = texts.pageTitle;
    document.getElementById('nav-brand').innerHTML = texts.navBrand;
    document.getElementById('btn-mode-search').innerHTML = texts.tabSearch;
    document.getElementById('btn-mode-write').innerHTML = texts.tabWrite;
    
    const outlineTitleEl = document.querySelector('#outline-editor-card .card-header span:first-child');
    if(outlineTitleEl) outlineTitleEl.innerHTML = texts.outlineTitle;

    // 刷新输入框 placeholder
    switchMode(currentMode);
}

// 清理章节编号的函数
function cleanChapterNumbers(text) {
    if (!text) return text;
    return text.split('\n').map(line => {
        // 移除各种格式的编号：3.1、3.2.1、2.1 等
        let cleaned = line
            .replace(/^[\s]*\d+(\.\d+)*[\s.]*/, '')     // 移除 2.1  3.2.1  等（包括末尾可能的点和空格）
            .replace(/^[\s]*\(\d+\)[\s]*/, '')         // 移除 (1) (2) 等
            .replace(/^[\s]*\d+、[\s]*/, '')            // 移除 1、2、等
            .replace(/^[\s]*[①-⑳][\s]*/, '');          // 移除 ① ② 等圆圈数字
        return cleaned;
    }).join('\n').trim();
}

// === 新增：批量文件上传逻辑 ===
let globalSelectedFiles = [];
const MAX_FILES = 5;

window.triggerFileInput = function() {
    document.getElementById('file-input').click();
}

window.handleFileInputChange = function(event) {
    if (event.target.files.length > 0) {
        window.handleFilesSelect(Array.from(event.target.files));
    }
    // 清空 input value，允许重复选同一个文件
    event.target.value = '';
}

window.handleFilesSelect = function(files) {
    const remainingSlots = MAX_FILES - globalSelectedFiles.length;
    if (remainingSlots <= 0) {
        alert(`最多只能同时上传 ${MAX_FILES} 个文件！`);
        return;
    }

    const filesToAdd = files.slice(0, remainingSlots);
    if (files.length > remainingSlots) {
        alert(`您选择了 ${files.length} 个文件，但只能再添加 ${remainingSlots} 个。已自动截断。`);
    }

    globalSelectedFiles.push(...filesToAdd);
    window.renderSelectedFiles();
}

window.removeSelectedFile = function(index) {
    globalSelectedFiles.splice(index, 1);
    window.renderSelectedFiles();
}

window.renderSelectedFiles = function() {
    const container = document.getElementById('selected-files-container');
    const list = document.getElementById('selected-files-list');
    const btnUpload = document.getElementById('btn-do-upload');

    list.innerHTML = '';

    if (globalSelectedFiles.length === 0) {
        container.style.display = 'none';
        btnUpload.disabled = true;
        return;
    }

    container.style.display = 'block';
    btnUpload.disabled = false;

    globalSelectedFiles.forEach((file, index) => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center py-2';
        li.innerHTML = `
            <div class="text-truncate me-2" style="font-size: 0.9rem;">
                <i class="bi bi-file-text text-primary me-2"></i>${file.name}
            </div>
            <button class="btn btn-sm btn-outline-danger border-0" onclick="event.stopPropagation(); removeSelectedFile(${index});">
                <i class="bi bi-trash"></i>
            </button>
        `;
        list.appendChild(li);
    });
}

// 拖拽事件绑定
document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    if(dropZone) {
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                window.handleFilesSelect(Array.from(e.dataTransfer.files));
            }
        });
    }
});

// 显示 Toast 提示
window.showToast = function(title, message, isSuccess = true) {
    const toastEl = document.getElementById('globalToast');
    const header = document.getElementById('toast-header');
    document.getElementById('toast-body').innerHTML = message;
    
    if (isSuccess) {
        header.className = 'toast-header text-white bg-success';
    } else {
        header.className = 'toast-header text-white bg-danger';
    }
    
    const toast = new bootstrap.Toast(toastEl, { delay: 5000 });
    toast.show();
}

// 轮询任务状态
async function pollTaskStatus(taskId, fileName, currentFileIndex, totalFiles) {
    return new Promise((resolve, reject) => {
        const bar = document.getElementById('upload-progress-bar');
        const log = document.getElementById('upload-log');
        const warningBanner = document.getElementById('global-sync-warning');
        const warningText = document.getElementById('sync-warning-text');

        const timer = setInterval(async () => {
            try {
                const res = await fetch(`/api/document/task_status/${taskId}`);
                const data = await res.json();
                
                if (data.code === 200 && data.data) {
                    const status = data.data;
                    
                    // 1. 更新主弹窗的进度条
                    bar.style.width = `${status.progress}%`;
                    log.textContent = `[${currentFileIndex}/${totalFiles}] ${fileName} - ${status.message || '处理中...'}`;
                    
                    // 2. 更新右下角悬浮卡片的进度条与文本
                    warningBanner.style.display = 'block';
                    warningText.textContent = `[${currentFileIndex}/${totalFiles}] ${fileName}`;
                    document.getElementById('sync-warning-pct').textContent = `${status.progress}%`;
                    document.getElementById('sync-warning-bar').style.width = `${status.progress}%`;

                    if (status.status === 'completed') {
                        clearInterval(timer);
                        warningBanner.style.display = 'none';
                        resolve(status);
                    } else if (status.status === 'error') {
                        clearInterval(timer);
                        warningBanner.style.display = 'none';
                        reject(new Error(status.message));
                    }
                }
            } catch (err) {
                console.error("轮询报错:", err);
                // 偶尔网络抖动不中断轮询
            }
        }, 1500); // 1.5秒查一次
    });
}

window.doUploadFile = async function() {
    if (globalSelectedFiles.length === 0) return;

    const btnUpload = document.getElementById('btn-do-upload');
    const btnClose = document.getElementById('btn-close-modal');
    const dropZone = document.getElementById('drop-zone');
    const filesContainer = document.getElementById('selected-files-container');
    const uploadStatus = document.getElementById('upload-status');
    const fileInput = document.getElementById('file-input');
    const progressBar = document.getElementById('upload-progress-bar');

    // UI 切换到加载状态
    btnUpload.disabled = true;
    btnClose.disabled = true; // 强制等待不能取消
    dropZone.style.display = 'none';
    filesContainer.style.display = 'none';
    uploadStatus.style.display = 'block';
    progressBar.style.width = '0%';

    let totalSuccessChunks = 0;
    let errorMessages = [];

    // 依次上传并等待任务完成
    for (let i = 0; i < globalSelectedFiles.length; i++) {
        const file = globalSelectedFiles[i];
        document.getElementById('upload-log').textContent = `正在提交第 ${i + 1}/${globalSelectedFiles.length} 个文件: ${file.name}...`;

        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', '');
        
        try {
            // 1. 提交文件获取 Task ID
            const response = await fetch('/api/document/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (response.ok && data.code === 200) {
                const taskId = data.data.task_id;
                // 2. 轮询等待这个任务完成
                const taskResult = await pollTaskStatus(taskId, file.name, i + 1, globalSelectedFiles.length);
                totalSuccessChunks += (taskResult.stats?.total || 0);
            } else {
                errorMessages.push(`[${file.name}] 提交失败: ${data.message}`);
            }
        } catch (error) {
            errorMessages.push(`[${file.name}] 处理异常: ${error.message}`);
        }
    }

    // 全部结束
    if (errorMessages.length > 0) {
        let msg = `有部分文件失败：<br>` + errorMessages.join('<br>');
        if (totalSuccessChunks > 0) msg += `<br><br>但仍成功写入了 ${totalSuccessChunks} 个知识块。`;
        showToast('上传警告', msg, false);
    } else {
        showToast('入库成功', `🎉 知识库补充完成！<br>共向 Qdrant 存入了 ${totalSuccessChunks} 个知识块。`, true);
    }
    
    // 关闭模态框并恢复 UI
    bootstrap.Modal.getInstance(document.getElementById('uploadModal')).hide();
    
    setTimeout(() => {
        uploadStatus.style.display = 'none';
        dropZone.style.display = 'block';
        globalSelectedFiles = [];
        window.renderSelectedFiles();
        fileInput.value = '';
        btnClose.disabled = false;
    }, 500);
}

function switchMode(mode) {
    currentMode = mode;
    const texts = UI_TEXTS[currentDisplayType] || UI_TEXTS['opensource'];
    
    const inputEl = document.getElementById('main-input');
    const btnSearch = document.getElementById('btn-mode-search');
    const btnWrite = document.getElementById('btn-mode-write');
    const wsSearch = document.getElementById('mode-search-workspace');
    const wsWrite = document.getElementById('mode-write-workspace');
    
    if (mode === 'search') {
        btnSearch.classList.add('active');
        btnWrite.classList.remove('active');
        inputEl.placeholder = texts.placeholderSearch;
        wsSearch.style.display = 'block';
        wsWrite.style.display = 'none';
    } else {
        btnWrite.classList.add('active');
        btnSearch.classList.remove('active');
        inputEl.placeholder = texts.placeholderWrite;
        wsWrite.style.display = 'block';
        wsSearch.style.display = 'none';
        document.getElementById('outline-editor-card').style.display = 'none';
        document.getElementById('chapter-generation-area').style.display = 'none';
        document.getElementById('step1').className = 'active';
        document.getElementById('step2').className = '';
    }
}

// 确保页面加载完成后调用初始化
document.addEventListener('DOMContentLoaded', () => {
    initSysConfig();
});

async function handleMainSubmit() {
    const inputVal = document.getElementById('main-input').value.trim();
    if (!inputVal) return;
    
    const category = null;
    const submitBtn = document.getElementById('main-submit-btn');
    const loadingBox = document.getElementById('loading-main');
    const loadingText = document.getElementById('loading-text');
    
    submitBtn.disabled = true;
    loadingBox.style.display = 'block';
    
    if (currentMode === 'search') {
        loadingText.innerText = '正在知识库中检索并分析答案...';
        await doNormalSearch(inputVal, category);
    } else {
        loadingText.innerText = '正在基于历史文档提取制度结构大纲...';
        currentMainTopic = inputVal;
        await doGenerateOutline(inputVal, category);
    }
    
    submitBtn.disabled = false;
    loadingBox.style.display = 'none';
}

async function doNormalSearch(query, category) {
    try {
        const res = await fetch('/api/rag/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, category: category || null, top_k: 3, enable_answer: true })
        });
        const data = await res.json();
        
        if (data.code === 200) {
            const answerBox = document.getElementById('search-answer-box');
            const ans = data.data.answer;
            if(ans && ans.expert_summary) {
                let tipsHtml = (ans.additional_tips || []).map(t => `
                    <li class="tip-item">
                        <i class="bi bi-check-circle-fill text-success me-2"></i>
                        <span>${t}</span>
                    </li>
                `).join('');
                
                answerBox.innerHTML = `
                    <div class="ai-answer-container">
                        <div class="answer-header">
                            <i class="bi bi-robot"></i>
                            <span>AI 专家分析</span>
                        </div>
                        <div class="answer-content">${ans.expert_summary.replace(/\n/g, '<br>')}</div>
                        
                        ${tipsHtml ? `
                        <div class="tips-section">
                            <div class="tips-header">
                                <i class="bi bi-lightbulb-fill"></i>
                                <span>执行建议与提示</span>
                            </div>
                            <ul class="tips-list">${tipsHtml}</ul>
                        </div>
                        ` : ''}
                    </div>
                `;
            } else {
                answerBox.innerHTML = `
                    <div class="ai-answer-container">
                        <div class="answer-content text-muted">
                            <i class="bi bi-info-circle me-2"></i>
                            ${data.data.answer || '未能生成总结'}
                        </div>
                    </div>
                `;
            }

                        const sourceBox = document.getElementById('search-source-box');
                        const results = data.data.results || [];
                        if (results.length > 0) {
                            sourceBox.innerHTML = results.map((r, index) => `
                                <div class="source-item">
                                    <div class="source-number">${index + 1}</div>
                                    <div class="source-info">
                                        <div class="source-filename">
                                            <i class="bi bi-file-earmark-pdf-fill"></i>
                                            <span>${r.file_name}</span>
                                        </div>
                                        ${r.page_number > 0 ? `<div class="source-page"><i class="bi bi-file-text"></i> 第 ${r.page_number} 页</div>` : ''}
                                    </div>
                                </div>
                            `).join('');
                        } else {
                            sourceBox.innerHTML = `
                                <div class="empty-state">
                                    <i class="bi bi-inbox"></i>
                                    <p>未找到相关原文记录</p>
                                </div>
                            `;
                        }
        } else {
            alert("检索失败: " + data.message);
        }
    } catch(e) { alert("网络错误: " + e.message); }
}

async function doGenerateOutline(topic, category) {
    try {
        const res = await fetch('/api/copilot/generate-outline', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: topic, category: category || null })
        });
        const data = await res.json();
        
        if (data.code === 200) {
            const outlineArray = data.data.outline || [];
            const listEl = document.getElementById('outline-list');
            listEl.innerHTML = '';
            
            outlineArray.forEach((item) => {
                listEl.insertAdjacentHTML('beforeend', createOutlineItemHtml(item.chapter, item.sub_topics));
            });
            
            document.getElementById('outline-editor-card').style.display = 'block';
        } else {
            alert("大纲生成失败: " + data.message);
        }
    } catch(e) { alert("网络错误: " + e.message); }
}

function createOutlineItemHtml(chapterName, subTopics) {
    const subsStr = (subTopics || []).join('； ');
    return `
        <div class="outline-item">
            <div style="flex-grow:1;">
                <div class="d-flex align-items-center">
                    <i class="bi bi-grip-vertical text-muted me-2" style="cursor: move;"></i>
                    <input type="text" class="chapter-input fw-bold" value="${chapterName}">
                </div>
                <span class="sub-topics ms-4 text-muted"><i class="bi bi-arrow-return-right"></i> ${subsStr}</span>
            </div>
            <button class="btn btn-sm btn-outline-danger border-0" onclick="this.closest('.outline-item').remove()" title="删除此章">
                <i class="bi bi-trash"></i>
            </button>
        </div>
    `;
}

function addCustomOutlineItem() {
    const listEl = document.getElementById('outline-list');
    listEl.insertAdjacentHTML('beforeend', createOutlineItemHtml("新增自定义章节（请修改名称）", []));
}

async function startChapterGeneration() {
    const inputs = document.querySelectorAll('.chapter-input');
    const chapters = Array.from(inputs).map(inp => inp.value.trim()).filter(v => v);
    
    if (chapters.length === 0) {
        alert("大纲不能为空！"); return;
    }

    document.getElementById('outline-editor-card').style.display = 'none';
    document.getElementById('chapter-generation-area').style.display = 'block';
    document.getElementById('step1').className = '';
    document.getElementById('step2').className = 'active';
    
    const container = document.getElementById('chapters-container');
    container.innerHTML = '';
    const category = null;

    for (let i = 0; i < chapters.length; i++) {
        const chapTitle = chapters[i];
        const cardId = 'gen-card-' + i;
        
        container.insertAdjacentHTML('beforeend', `
            <div class="card mb-4 border-primary" id="${cardId}">
                <div class="card-header bg-primary text-white fw-bold">
                    <div class="spinner-border spinner-border-sm me-2"></div> 正在起草：${chapTitle}
                </div>
                <div class="card-body text-center py-4 text-muted">
                    <p>正在结合【${currentMainTopic}】的宏观要求，</p>
                    <p>去向量库检索相关档案，并交由 AI 专家润色行文...</p>
                </div>
            </div>
        `);
        
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });

        try {
            const res = await fetch('/api/copilot/generate-regulation-chapter', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    main_topic: currentMainTopic,
                    chapter_title: chapTitle,
                    category: category || null
                })
            });
            const resData = await res.json();
            const cardEl = document.getElementById(cardId);
            
            if (resData.code !== 200) {
                cardEl.className = "card mb-4 border-danger";
                cardEl.innerHTML = `<div class="card-header bg-danger text-white">${chapTitle} - 起草失败</div><div class="card-body">${resData.message}</div>`;
                continue;
            }
            
                        const draft = resData.data.draft_result || {};
            const draft_content = cleanChapterNumbers(draft.draft_content || '');
            const chapter_title = draft.chapter_title || chapTitle;
            const extracted_parameters = draft.extracted_parameters || [];
            const human_review_needed = draft.human_review_needed || [];
            const sources = resData.data.sources || [];
            
            let paramsHtml = extracted_parameters.map(p => `<span class="source-tag">${p}</span>`).join('');
            let reviewHtml = human_review_needed.map(r => `<div class="review-alert">${r}</div>`).join('');
            
            let sourcesHtml = sources.map(s => {
                let pageInfo = s.page_number > 0 ? ` <span class="badge bg-secondary" style="font-size:0.75em;">第${s.page_number}页</span>` : '';
                return `<div class="mb-2 pb-2 border-bottom" style="font-size:0.85rem;"><i class="bi bi-file-earmark-pdf text-danger"></i> ${s.file_name}${pageInfo}</div>`;
            }).join('');
            if (sources.length === 0) {
                sourcesHtml = '<div class="text-muted small fst-italic">该章节为AI基于经验起草，未找到具体的参考文件。</div>';
            }
            
            cardEl.className = "card mb-4 shadow-sm";
            cardEl.innerHTML = `
                <div class="card-header bg-light fw-bold d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-file-earmark-check text-success"></i> ${chapter_title}</span>
                    <button class="btn btn-sm btn-outline-success" onclick="this.innerHTML='<i class='bi bi-check'></i> 已确认并保存'; this.classList.add('active');"><i class="bi bi-save"></i> 确认本章无误</button>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-8 border-end">
                            <label class="text-muted small mb-1"><i class="bi bi-pencil"></i> AI草案内容 (支持富文本编辑)</label>
                            <textarea class="form-control draft-editor p-3 bg-white" rows="15" style="resize: vertical; box-shadow: inset 0 1px 3px rgba(0,0,0,.05); border: 1px solid #ced4da;">${draft_content}</textarea>
                        </div>
                        <div class="col-md-4 ps-3">
                            <div class="mb-3 p-3 bg-light rounded">
                                <label class="fw-bold mb-2 text-primary" style="font-size:0.9rem;"><i class="bi bi-journal-bookmark-fill"></i> 档案溯源出处</label>
                                <div style="max-height: 150px; overflow-y: auto;">
                                    ${sourcesHtml}
                                </div>
                            </div>
                            <div class="mb-3">
                                <label class="fw-bold mb-2 text-success" style="font-size:0.9rem;"><i class="bi bi-magic"></i> 核心参数/信息提取</label>
                                <div>
                                    ${paramsHtml || '<span class="text-muted small">未提取到核心参数</span>'}
                                </div>
                            </div>
                            <div>
                                <label class="fw-bold mb-2 text-danger" style="font-size:0.9rem;"><i class="bi bi-exclamation-triangle"></i> 人工审查留白项</label>
                                <div>
                                    ${reviewHtml || '<span class="text-muted small">无需特别审查填空</span>'}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } catch(e) {
            document.getElementById(cardId).innerHTML = `<div class="card-header bg-danger text-white">异常</div><div class="card-body">${e.message}</div>`;
        }
    }
    
    document.getElementById('step2').className = '';
    document.getElementById('step3').className = 'active';
    document.getElementById('finish-area').style.display = 'block';
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}
