document.addEventListener('DOMContentLoaded', function() {
    // 文件上传预览
    const fileInput = document.getElementById('storyboard_file');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const fileNameDisplay = document.getElementById('file-name');
            if (fileNameDisplay) {
                fileNameDisplay.textContent = this.files[0] ? this.files[0].name : '未选择文件';
            }
            
            // 验证文件类型
            if (this.files[0]) {
                const fileType = this.files[0].name.split('.').pop().toLowerCase();
                if (fileType !== 'json') {
                    alert('请上传JSON文件');
                    this.value = '';
                    if (fileNameDisplay) {
                        fileNameDisplay.textContent = '未选择文件';
                    }
                }
            }
        });
    }
    
    // 拖放上传
    const dropArea = document.querySelector('.file-upload-wrapper');
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, function() {
                dropArea.classList.add('dragover');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, function() {
                dropArea.classList.remove('dragover');
            }, false);
        });
        
        dropArea.addEventListener('drop', function(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (fileInput) {
                fileInput.files = files;
                const event = new Event('change');
                fileInput.dispatchEvent(event);
            }
        }, false);
    }
    
    // 表单验证
    const forms = document.querySelectorAll('.needs-validation');
    if (forms.length > 0) {
        Array.from(forms).forEach(form => {
            form.addEventListener('submit', event => {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                
                form.classList.add('was-validated');
            }, false);
        });
    }
    
    // 卡密显示/隐藏
    const toggleButtons = document.querySelectorAll('.toggle-key');
    if (toggleButtons.length > 0) {
        toggleButtons.forEach(button => {
            button.addEventListener('click', function() {
                const keyElement = this.previousElementSibling;
                if (keyElement.classList.contains('text-truncate')) {
                    keyElement.classList.remove('text-truncate');
                    this.innerHTML = '<i class="fas fa-eye-slash"></i>';
                    this.setAttribute('title', '隐藏卡密');
                } else {
                    keyElement.classList.add('text-truncate');
                    this.innerHTML = '<i class="fas fa-eye"></i>';
                    this.setAttribute('title', '显示卡密');
                }
            });
        });
    }
    
    // 复制到剪贴板
    const copyButtons = document.querySelectorAll('.copy-key');
    if (copyButtons.length > 0) {
        copyButtons.forEach(button => {
            button.addEventListener('click', function() {
                const keyText = this.getAttribute('data-key');
                navigator.clipboard.writeText(keyText).then(function() {
                    const originalText = button.innerHTML;
                    button.innerHTML = '<i class="fas fa-check"></i> 已复制';
                    setTimeout(function() {
                        button.innerHTML = originalText;
                    }, 2000);
                }, function(err) {
                    console.error('复制失败: ', err);
                });
            });
        });
    }
    
    // Bootstrap工具提示初始化
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (tooltipTriggerList.length > 0) {
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
});
