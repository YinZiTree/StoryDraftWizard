document.addEventListener('DOMContentLoaded', function() {
    // 统计数据图表
    const chartContainers = document.querySelectorAll('[data-chart]');
    if (chartContainers.length > 0) {
        chartContainers.forEach(container => {
            const chartType = container.getAttribute('data-chart');
            const chartId = container.getAttribute('id');

            if (chartType === 'usage' || chartType === 'registrations') {
                drawChart(chartId, chartType);
            }
        });
    }

    // 时间范围选择
    const rangeSelector = document.getElementById('time-range');
    if (rangeSelector) {
        rangeSelector.addEventListener('change', function() {
            const range = this.value;
            const url = new URL(window.location);
            url.searchParams.set('range', range);
            window.location = url.toString();
        });
    }

    // 分页器
    const paginationLinks = document.querySelectorAll('.page-link');
    if (paginationLinks.length > 0) {
        paginationLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                if (this.getAttribute('href') === '#') {
                    e.preventDefault();
                }
            });
        });
    }

    // 确认删除
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    if (deleteButtons.length > 0) {
        deleteButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                const message = this.getAttribute('data-confirm');
                if (!confirm(message)) {
                    e.preventDefault();
                }
            });
        });
    }

    // 批量操作
    const bulkActionForm = document.getElementById('bulk-action-form');
    if (bulkActionForm) {
        bulkActionForm.addEventListener('submit', function(e) {
            const action = document.getElementById('bulk-action').value;
            const checkboxes = document.querySelectorAll('input[name="selected[]"]:checked');

            if (checkboxes.length === 0) {
                e.preventDefault();
                alert('请至少选择一项');
                return;
            }

            if (action === 'delete' && !confirm('确定要删除选中的项目吗？')) {
                e.preventDefault();
            }
        });
    }

    // 全选/取消全选
    const selectAllCheckbox = document.getElementById('select-all');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('input[name="selected[]"]');
            checkboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
        });
    }
});

// 绘制图表函数
function drawChart(containerId, dataType) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // 获取时间范围
    const rangeSelector = document.getElementById('time-range');
    const range = rangeSelector ? rangeSelector.value : 'day';

    // 从API获取数据
    fetch(`/admin/api/statistics?range=${range}`)
        .then(response => response.json())
        .then(data => {
            if (!data.data || !data.data[dataType]) {
                throw new Error('Invalid data format received from server');
            }
            
            const chartData = data.data[dataType];
            if (!Array.isArray(chartData)) {
                throw new Error('Chart data is not an array');
            }

            // 准备图表数据
            const labels = chartData.map(item => item.label);
            const values = chartData.map(item => item.value);

            // 创建图表
            new Chart(container, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: dataType === 'usage' ? '使用次数' : '注册用户数',
                        data: values,
                        backgroundColor: dataType === 'usage' ? 'rgba(75, 192, 192, 0.2)' : 'rgba(54, 162, 235, 0.2)',
                        borderColor: dataType === 'usage' ? 'rgba(75, 192, 192, 1)' : 'rgba(54, 162, 235, 1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('获取统计数据失败:', error);
            container.innerHTML = '<div class="alert alert-danger">加载数据失败</div>';
        });
}

function rechargeKey(keyId) {
    const amount = prompt('请输入充值次数：');
    if (amount && !isNaN(amount) && parseInt(amount) > 0) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/admin/keys/${keyId}/recharge`;

        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'amount';
        input.value = amount;

        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
    }
}

function toggleKey(keyId) {
}