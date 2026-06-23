/**
 * LIFEOS — Chart.js Configurations
 * All analytics charts for the insights page.
 */

// ─── Chart.js Global Defaults ───
if (typeof Chart !== 'undefined') {
    Chart.defaults.color = '#94A3B8';
    Chart.defaults.borderColor = 'rgba(45, 45, 78, 0.5)';
    Chart.defaults.font.family = "'Inter', sans-serif";
}

/**
 * Create Productivity Score Doughnut Chart.
 */
function createProductivityChart(canvasId, score) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const scoreColor = score >= 70 ? '#10B981' : score >= 40 ? '#F59E0B' : '#EF4444';

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [score, 100 - score],
                backgroundColor: [scoreColor, 'rgba(45, 45, 78, 0.3)'],
                borderWidth: 0,
                cutout: '78%',
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false },
            },
        },
        plugins: [{
            id: 'centerText',
            afterDraw: (chart) => {
                const { ctx, chartArea } = chart;
                const centerX = (chartArea.left + chartArea.right) / 2;
                const centerY = (chartArea.top + chartArea.bottom) / 2;

                ctx.save();
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';

                ctx.font = 'bold 28px Inter';
                ctx.fillStyle = '#F8FAFC';
                ctx.fillText(score, centerX, centerY - 8);

                ctx.font = '11px Inter';
                ctx.fillStyle = '#94A3B8';
                ctx.fillText('SCORE', centerX, centerY + 16);

                ctx.restore();
            },
        }],
    });
}

/**
 * Create Weekly Productivity Line Chart.
 */
function createWeeklyChart(canvasId, weeklyData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
    const data = weeklyData || [45, 52, 68, 74];

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Productivity Score',
                data,
                borderColor: '#6366F1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 6,
                pointHoverRadius: 8,
                pointBackgroundColor: '#6366F1',
                pointBorderColor: '#0F0F1A',
                pointBorderWidth: 3,
                borderWidth: 3,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(45, 45, 78, 0.3)' },
                    ticks: { stepSize: 25 },
                },
                x: {
                    grid: { display: false },
                },
            },
        },
    });
}

/**
 * Create Tasks by Category Bar Chart.
 */
function createCategoryChart(canvasId, categoryData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const categories = Object.keys(categoryData || {});
    const values = Object.values(categoryData || {});

    const colors = {
        academic: '#6366F1',
        career: '#8B5CF6',
        finance: '#10B981',
        personal: '#F59E0B',
        health: '#EC4899',
    };

    const bgColors = categories.map(c => colors[c] || '#6366F1');

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: categories.map(c => c.charAt(0).toUpperCase() + c.slice(1)),
            datasets: [{
                label: 'Tasks',
                data: values,
                backgroundColor: bgColors.map(c => c + '80'),
                borderColor: bgColors,
                borderWidth: 2,
                borderRadius: 8,
                barPercentage: 0.6,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(45, 45, 78, 0.3)' },
                    ticks: { stepSize: 1 },
                },
                x: {
                    grid: { display: false },
                },
            },
        },
    });
}

/**
 * Create Completion Rate Donut Chart.
 */
function createCompletionChart(canvasId, statusData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const labels = Object.keys(statusData || {}).map(s =>
        s.charAt(0).toUpperCase() + s.slice(1)
    );
    const values = Object.values(statusData || {});

    const colors = {
        completed: '#10B981',
        pending: '#F59E0B',
        overdue: '#EF4444',
        in_progress: '#6366F1',
        cancelled: '#64748B',
    };

    const bgColors = Object.keys(statusData || {}).map(s => colors[s] || '#64748B');

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: bgColors.map(c => c + '99'),
                borderColor: bgColors,
                borderWidth: 2,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true,
                        pointStyleWidth: 10,
                    },
                },
            },
        },
    });
}

/**
 * Create Hour-by-Hour Productivity Heatmap (as bar chart).
 */
function createHourChart(canvasId, hourData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);
    const values = hours.map((_, i) => (hourData || {})[String(i)] || 0);

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hours.filter((_, i) => i >= 6 && i <= 23),
            datasets: [{
                label: 'Tasks Completed',
                data: values.filter((_, i) => i >= 6 && i <= 23),
                backgroundColor: values.filter((_, i) => i >= 6 && i <= 23).map(v => {
                    if (v >= 3) return 'rgba(99, 102, 241, 0.8)';
                    if (v >= 1) return 'rgba(99, 102, 241, 0.4)';
                    return 'rgba(45, 45, 78, 0.3)';
                }),
                borderRadius: 4,
                barPercentage: 0.7,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(45, 45, 78, 0.3)' },
                    ticks: { stepSize: 1 },
                },
                x: {
                    grid: { display: false },
                    ticks: { maxRotation: 45 },
                },
            },
        },
    });
}
