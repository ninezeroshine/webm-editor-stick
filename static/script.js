const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const durationInput = document.getElementById('durationInput');
const compressCheckbox = document.getElementById('compressCheckbox');
const compressionOptions = document.getElementById('compressionOptions');
const crfInput = document.getElementById('crfInput');
const bitrateInput = document.getElementById('bitrateInput');
const processBtn = document.getElementById('processBtn');
const statusMessage = document.getElementById('statusMessage');
const loadingIndicator = document.getElementById('loadingIndicator');

let selectedFile = null;

compressCheckbox.addEventListener('change', () => {
    if (compressCheckbox.checked) {
        compressionOptions.classList.remove('hidden');
    } else {
        compressionOptions.classList.add('hidden');
    }
});

dropZone.addEventListener('click', () => {
    fileInput.click();
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelection(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelection(e.target.files[0]);
    }
});

function handleFileSelection(file) {
    hideStatusMessage();
    
    if (!file.name.toLowerCase().endsWith('.webm')) {
        showStatusMessage('Please select a .webm file', 'error');
        return;
    }
    
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
        showStatusMessage('File size must be less than 10MB', 'error');
        return;
    }
    
    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileInfo.classList.remove('hidden');
    processBtn.disabled = false;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

processBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    
    const duration = parseFloat(durationInput.value);
    if (isNaN(duration) || duration < 0) {
        showStatusMessage('Please enter a valid duration value', 'error');
        return;
    }
    
    processBtn.disabled = true;
    hideStatusMessage();
    loadingIndicator.classList.remove('hidden');
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('duration', duration.toString());
    
    const useCompression = compressCheckbox.checked;
    let endpoint = '/upload';
    let downloadSuffix = '_fixed';
    
    if (useCompression) {
        endpoint = '/compress';
        downloadSuffix = '_compressed';
        formData.append('crf', crfInput.value);
        formData.append('bitrate', bitrateInput.value);
        loadingIndicator.querySelector('p').textContent = 'Compressing video (this may take a few minutes)...';
    } else {
        loadingIndicator.querySelector('p').textContent = 'Processing your file...';
    }
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Processing failed');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        const originalName = selectedFile.name.replace('.webm', '');
        a.download = `${originalName}${downloadSuffix}.webm`;
        
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showStatusMessage('File processed successfully! Download started.', 'success');
    } catch (error) {
        showStatusMessage(error.message, 'error');
    } finally {
        loadingIndicator.classList.add('hidden');
        processBtn.disabled = false;
    }
});

function showStatusMessage(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    statusMessage.classList.remove('hidden');
}

function hideStatusMessage() {
    statusMessage.classList.add('hidden');
}
