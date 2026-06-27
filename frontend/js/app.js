/**
 * LIFEOS — Core Application Logic
 * API client, task rendering, countdown timers, and shared utilities.
 */

// ─── Configuration ───
const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api'
    : '/api';

let DEFAULT_USER_ID = null;

// ─── API Client ───
const api = {
    async post(endpoint, data) {
        try {
            const res = await fetch(`${API_BASE}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!res.ok) throw new Error(`API error: ${res.status}`);
            return await res.json();
        } catch (err) {
            console.error(`POST ${endpoint} failed:`, err);
            throw err;
        }
    },

    async get(endpoint) {
        try {
            const res = await fetch(`${API_BASE}${endpoint}`);
            if (!res.ok) throw new Error(`API error: ${res.status}`);
            return await res.json();
        } catch (err) {
            console.error(`GET ${endpoint} failed:`, err);
            throw err;
        }
    },

    async put(endpoint, data = {}) {
        try {
            const res = await fetch(`${API_BASE}${endpoint}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!res.ok) throw new Error(`API error: ${res.status}`);
            return await res.json();
        } catch (err) {
            console.error(`PUT ${endpoint} failed:`, err);
            throw err;
        }
    },

    async delete(endpoint) {
        try {
            const res = await fetch(`${API_BASE}${endpoint}`, {
                method: 'DELETE',
            });
            if (!res.ok) throw new Error(`API error: ${res.status}`);
            return await res.json();
        } catch (err) {
            console.error(`DELETE ${endpoint} failed:`, err);
            throw err;
        }
    },
};

// ─── Brain Dump ───
async function submitBrainDump(text) {
    return api.post('/brain-dump', { text, user_id: DEFAULT_USER_ID });
}

// ─── Agent Plan ───
async function getAgentPlan(context, mood = null) {
    return api.post('/agent/plan', {
        user_id: DEFAULT_USER_ID,
        context,
        mood,
    });
}

// ─── Tasks ───
async function getTasks(status = null) {
    let url = `/tasks/${DEFAULT_USER_ID}`;
    if (status) url += `?status=${status}`;
    return api.get(url);
}

async function completeTask(taskId) {
    return api.put(`/tasks/${taskId}/complete`);
}

async function postponeTask(taskId) {
    return api.put(`/tasks/${taskId}/postpone`);
}

async function deleteTask(taskId) {
    return api.delete(`/tasks/${taskId}`);
}

// ─── Mood ───
async function setMood(mood) {
    return api.post('/mood', { user_id: DEFAULT_USER_ID, mood });
}

// ─── Crisis ───
async function activateCrisis(taskTitle, minutes, taskId = null) {
    return api.post('/crisis/activate', {
        task_id: taskId,
        task_title: taskTitle,
        minutes_available: minutes,
    });
}

async function getCrisisAssist(taskTitle, step, stepTitle, question) {
    return api.post('/crisis/assist', {
        task_title: taskTitle,
        step,
        step_title: stepTitle,
        question,
    });
}

// ─── Insights ───
async function getInsights() {
    return api.get(`/insights/${DEFAULT_USER_ID}`);
}

// ─── Streak ───
async function getStreak() {
    return api.get(`/user/${DEFAULT_USER_ID}/streak`);
}

// ─── Weekly Review ───
async function generateReview(week = '') {
    return api.post('/review/generate', { user_id: DEFAULT_USER_ID, week });
}

// ─── Email Draft ───
async function draftEmail(taskTitle, deadline, reason) {
    return api.post('/email/draft', {
        task_title: taskTitle,
        task_deadline: deadline,
        reason,
    });
}

// ═══════════════════════════════════════════════
// UI Rendering Utilities
// ═══════════════════════════════════════════════

/**
 * Create a task card HTML element.
 */
function createTaskCard(task, options = {}) {
    const priority = task.priority_score || task.urgency_score || 5;
    const priorityClass = priority >= 8 ? 'high' : priority >= 5 ? 'medium' : 'low';
    const priorityLevel = priority >= 8 ? 'URGENT' : priority >= 5 ? 'MEDIUM' : 'LOW';

    const deadlineText = getDeadlineText(task.deadline);
    const deadlineClass = isUrgentDeadline(task.deadline) ? 'urgent' : '';

    const showActions = options.showActions !== false;
    const showCrisis = options.showCrisis !== false;
    const animationDelay = options.delay || 0;

    // Use JSON.stringify to safely encode strings with quotes/apostrophes
    const safeTitle = JSON.stringify(task.title || '');
    const safeId = JSON.stringify(task._id || '');

    return `
        <div class="task-card priority-${priorityClass} animate-slide-up"
             style="animation-delay: ${animationDelay}s"
             data-task-id="${task._id || ''}"
             data-priority="${priority}">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
                    <span class="priority-badge ${priorityClass}">${priorityLevel} ${priority.toFixed(1)}</span>
                    <span class="category-tag">${task.category || 'personal'}</span>
                </div>
                ${task.postpone_count > 0 ? `<span style="font-size: 0.7rem; color: var(--accent-warning);">⚠ Postponed ${task.postpone_count}x</span>` : ''}
            </div>
            <h4 style="margin-bottom: 0.5rem; color: var(--text-primary);">${escapeHtml(task.title)}</h4>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="deadline-text ${deadlineClass}">
                    🕐 ${deadlineText}
                    ${task.estimated_hours ? ` • ${task.estimated_hours}h estimated` : ''}
                </span>
                ${showActions ? `
                <div style="display: flex; gap: 0.5rem;">
                    <button class="btn-success" data-id="${escapeHtml(task._id)}" onclick="handleCompleteTask(this.dataset.id)" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">
                        ✓ Done
                    </button>
                    ${showCrisis && priority >= 7 ? `
                    <button class="btn-ghost" data-id="${escapeHtml(task._id)}" data-title="${escapeHtml(task.title)}" onclick="handleCrisisMode(this.dataset.id, this.dataset.title)"
                            style="padding: 0.35rem 0.75rem; font-size: 0.8rem; color: var(--accent-crisis); border-color: var(--accent-crisis);">
                        🚨 Crisis
                    </button>` : ''}
                    <button class="btn-ghost" data-id="${escapeHtml(task._id)}" onclick="handleDeleteTask(this.dataset.id)"
                            style="padding: 0.35rem 0.75rem; font-size: 0.8rem; color: #EF4444; border-color: #EF4444;">
                        🗑️ Delete
                    </button>
                </div>` : ''}
            </div>
        </div>
    `;
}

/**
 * Get human-readable deadline text.
 */
function getDeadlineText(deadline) {
    if (!deadline || deadline === 'unknown') return 'No deadline';
    if (deadline === 'overdue') return '⚠️ OVERDUE';

    try {
        const deadlineDate = new Date(deadline);
        const now = new Date();
        const diff = deadlineDate - now;
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const days = Math.floor(hours / 24);

        if (hours < 0) return '⚠️ OVERDUE';
        if (hours < 1) return 'Due NOW';
        if (hours < 24) return `${hours}h remaining`;
        if (days === 1) return 'Tomorrow';
        if (days < 7) return `${days} days left`;
        return deadlineDate.toLocaleDateString();
    } catch {
        return deadline;
    }
}

/**
 * Check if deadline is urgent (<24 hours).
 */
function isUrgentDeadline(deadline) {
    if (!deadline || deadline === 'unknown') return false;
    if (deadline === 'overdue') return true;
    try {
        const diff = new Date(deadline) - new Date();
        return diff < 24 * 60 * 60 * 1000;
    } catch {
        return false;
    }
}

/**
 * Escape HTML to prevent XSS.
 */
function escapeHtml(text) {
    if (!text) return '';
    return text.toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/**
 * Count-up animation for stat numbers.
 */
function animateCountUp(element, target, duration = 1000) {
    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // Ease out cubic
        const current = Math.floor(start + (target - start) * eased);

        element.textContent = current;

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            element.textContent = target;
        }
    }

    requestAnimationFrame(update);
}

/**
 * Update ambient deadline pressure (background tint).
 */
function updateAmbientPressure(tasks) {
    if (!tasks || tasks.length === 0) {
        document.documentElement.style.setProperty('--ambient-tint', 'transparent');
        return;
    }

    const now = new Date();
    let closestHours = Infinity;

    tasks.forEach(task => {
        if (task.deadline && task.deadline !== 'unknown' && task.status !== 'completed') {
            try {
                const diff = (new Date(task.deadline) - now) / (1000 * 60 * 60);
                if (diff > 0 && diff < closestHours) {
                    closestHours = diff;
                }
            } catch { }
        }
    });

    let tint = 'transparent';
    if (closestHours <= 24) {
        tint = 'rgba(239, 68, 68, 0.06)'; // Red danger
    } else if (closestHours <= 72) {
        tint = 'rgba(245, 158, 11, 0.04)'; // Amber warning
    } else if (closestHours <= 168) {
        tint = 'rgba(245, 158, 11, 0.02)'; // Slight warm
    }

    document.documentElement.style.setProperty('--ambient-tint', tint);
}

/**
 * Show loading state.
 */
function showLoading(containerId, count = 3) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let skeletons = '';
    for (let i = 0; i < count; i++) {
        skeletons += `
            <div class="skeleton" style="height: 80px; margin-bottom: 0.75rem;"></div>
        `;
    }
    container.innerHTML = skeletons;
}

/**
 * Show toast notification.
 */
function showToast(message, type = 'success') {
    const colors = {
        success: 'var(--accent-success)',
        error: 'var(--accent-crisis)',
        warning: 'var(--accent-warning)',
        info: 'var(--accent-primary)',
    };

    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        background: var(--bg-surface);
        border: 1px solid ${colors[type]};
        color: var(--text-primary);
        padding: 1rem 1.5rem;
        border-radius: 0.75rem;
        font-size: 0.9rem;
        z-index: 10000;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
        animation: slide-in-up 0.3s ease;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    `;

    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    toast.innerHTML = `<span>${icons[type]}</span> ${escapeHtml(message)}`;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'fade-in 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Task action handlers.
 */
async function handleCompleteTask(taskId) {
    try {
        const result = await completeTask(taskId);
        showToast(result.message || 'Task completed! 🎉');

        // Remove the card with animation
        const card = document.querySelector(`[data-task-id="${taskId}"]`);
        if (card) {
            card.style.transition = 'all 0.4s ease';
            card.style.transform = 'translateX(100px)';
            card.style.opacity = '0';
            setTimeout(() => card.remove(), 400);
        }

        // Refresh data if function exists
        if (typeof refreshDashboard === 'function') refreshDashboard();
    } catch (err) {
        showToast('Failed to complete task', 'error');
    }
}

async function handleDeleteTask(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) return;
    try {
        await deleteTask(taskId);
        showToast('Task deleted successfully');

        // Remove card with animation
        const card = document.querySelector(`[data-task-id="${taskId}"]`);
        if (card) {
            card.style.transition = 'all 0.4s ease';
            card.style.transform = 'scale(0.9)';
            card.style.opacity = '0';
            setTimeout(() => card.remove(), 400);
        }

        // Refresh data if functions exist
        if (typeof refreshDashboard === 'function') refreshDashboard();
        if (typeof loadCalendarEvents === 'function') {
            const calendarTasks = await loadCalendarEvents();
            if (typeof renderSidebar === 'function') renderSidebar(calendarTasks);
            if (typeof updateAIInsight === 'function') updateAIInsight(calendarTasks);
        }
        if (typeof loadInsights === 'function') loadInsights();
    } catch (err) {
        showToast('Failed to delete task', 'error');
    }
}

async function handleCrisisMode(taskId, taskTitle) {
    // Redirect to crisis page with task info
    const params = new URLSearchParams({
        task_id: taskId || '',
        task_title: taskTitle || '',
    });
    window.location.href = `crisis.html?${params.toString()}`;
}

// Toggle user dropdown footer menu
window.toggleUserMenu = function() {
    const menu = document.getElementById('userMenu');
    if (menu) {
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    }
};

document.addEventListener('click', (e) => {
    const avatar = document.getElementById('userAvatar');
    if (avatar && !avatar.contains(e.target)) {
        const menu = document.getElementById('userMenu');
        if (menu) menu.style.display = 'none';
    }
});

// Sidebar Navigation Highlights and User Avatar Binding
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    let activeId = '';
    if (path.includes('dashboard.html')) activeId = 'nav-dashboard';
    else if (path.includes('onboard.html')) activeId = 'nav-dump';
    else if (path.includes('plan.html')) activeId = 'nav-plan';
    else if (path.includes('calendar.html')) activeId = 'nav-calendar';
    else if (path.includes('insights.html')) activeId = 'nav-insights';

    if (activeId) {
        const link = document.getElementById(activeId);
        if (link) link.classList.add('active');
    }

    // Auto load user profile for sidebar
    fetch('/auth/me').then(r => r.json()).then(data => {
        if (data.user) {
            const photoEl = document.getElementById('sidebarUserPhoto') || document.getElementById('userPhoto');
            const nameEl = document.getElementById('sidebarUserName') || document.getElementById('userName');
            const emailEl = document.getElementById('sidebarUserEmail') || document.getElementById('userEmail');
            if (photoEl) photoEl.src = data.user.picture || `https://ui-avatars.com/api/?name=${encodeURIComponent(data.user.name || 'User')}&background=7C5CFF&color=fff`;
            if (nameEl) nameEl.textContent = data.user.name || 'User';
            if (emailEl) emailEl.textContent = data.user.email || '';

            // Connection Status update for all sidebars
            if (data.user.calendar_connected) {
                const calPill = document.getElementById('calendarStatusPill');
                if (calPill) {
                    calPill.classList.replace('bg-slate-800', 'bg-indigo-900/40');
                    calPill.classList.replace('border-slate-700', 'border-indigo-500/30');
                    const calText = calPill.querySelector('.status-text');
                    if (calText) {
                        calText.textContent = 'Connected';
                        calText.className = 'status-text text-indigo-400 font-medium';
                    }
                }
            }
            if (data.user.gmail_connected) {
                const gmailPill = document.getElementById('gmailStatusPill');
                if (gmailPill) {
                    gmailPill.classList.replace('bg-slate-800', 'bg-red-900/40');
                    gmailPill.classList.replace('border-slate-700', 'border-red-500/30');
                    const gmailText = gmailPill.querySelector('.status-text');
                    if (gmailText) {
                        gmailText.textContent = 'Connected';
                        gmailText.className = 'status-text text-red-400 font-medium';
                    }
                }
            }
        }
    }).catch(() => {});
});

/**
 * Format date for display.
 */
function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        return new Date(dateStr).toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
        });
    } catch {
        return dateStr;
    }
}

/**
 * Get current date info.
 */
function getCurrentDateInfo() {
    const now = new Date();
    return {
        full: now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }),
        short: now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }),
        time: now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        greeting: now.getHours() < 12 ? 'Good Morning' : now.getHours() < 17 ? 'Good Afternoon' : 'Good Evening',
    };
}

// ─── Notification Service ───
const NotificationService = {
    initialized: false,
    intervalId: null,

    init() {
        if (!('Notification' in window)) return;
        
        // Modern browsers block permission requests on page load.
        // Request permission on the first user interaction.
        if (Notification.permission === 'default') {
            const requestOnInteraction = () => {
                Notification.requestPermission();
                document.removeEventListener('click', requestOnInteraction);
            };
            document.addEventListener('click', requestOnInteraction);
        }
        
        if (!this.initialized) {
            this.intervalId = setInterval(() => this.checkTasks(), 60000); // Check every minute
            this.initialized = true;
            // Check immediately on load after a short delay to allow tasks to load
            setTimeout(() => this.checkTasks(), 5000);
        }
    },

    async checkTasks() {
        if (Notification.permission !== 'granted') return;
        if (!DEFAULT_USER_ID) return;

        try {
            const data = await getTasks();
            const tasks = data.tasks || [];
            const now = new Date();
            
            // Get already notified tasks from localStorage
            const notifiedTasksStr = localStorage.getItem('notified_tasks');
            const notifiedTasks = notifiedTasksStr ? JSON.parse(notifiedTasksStr) : {};

            let newNotifications = 0;

            tasks.forEach(task => {
                if (task.status === 'completed' || !task.deadline) return;

                const deadline = new Date(task.deadline);
                const timeDiff = deadline - now;
                const minutesDiff = timeDiff / (1000 * 60);

                let shouldNotify = false;
                let title = '';
                let body = '';

                if (minutesDiff < 0 && minutesDiff > -60 && !notifiedTasks[`${task._id}_overdue`]) {
                    // Just became overdue (within the last hour)
                    shouldNotify = true;
                    title = '🚨 Task Overdue!';
                    body = `"${task.title}" is now overdue.`;
                    notifiedTasks[`${task._id}_overdue`] = true;
                } else if (minutesDiff > 0 && minutesDiff <= 15 && !notifiedTasks[`${task._id}_15min`]) {
                    // Due in <= 15 mins
                    shouldNotify = true;
                    title = '⏰ Task Due Soon!';
                    body = `"${task.title}" is due in ${Math.ceil(minutesDiff)} minutes.`;
                    notifiedTasks[`${task._id}_15min`] = true;
                }

                if (shouldNotify && newNotifications < 3) {
                    new Notification(title, {
                        body: body,
                        icon: '/favicon.ico' // Or any suitable icon
                    });
                    newNotifications++;
                }
            });

            localStorage.setItem('notified_tasks', JSON.stringify(notifiedTasks));

        } catch (err) {
            console.error('Failed to check tasks for notifications:', err);
        }
    }
};

// Initialize NotificationService when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only init if we are on a page that tracks tasks (like dashboard or calendar)
    if (window.location.pathname.includes('dashboard') || window.location.pathname.includes('calendar') || window.location.pathname === '/') {
        NotificationService.init();
    }
});
