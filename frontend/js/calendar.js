/**
 * LIFEOS — Premium Calendar JS
 * FullCalendar with hover popups, priority filtering, and dark command center theme.
 */

let calendar = null;
let _popupTimeout = null;
let _calTasks = [];

// ─── Category helpers ───
function getCategoryEmoji(cat) {
    return { academic: '📚', career: '💼', finance: '💰', personal: '👤', health: '🏃' }[cat] || '📋';
}
function getPriorityColor(score) {
    if (score >= 8) return '#EF4444';
    if (score >= 5) return '#F59E0B';
    return '#10B981';
}
function getPriorityLabel(score) {
    if (score >= 8) return 'URGENT';
    if (score >= 5) return 'MEDIUM';
    return 'LOW';
}

/**
 * Initialize FullCalendar.
 */
function initCalendar(elementId) {
    const calendarEl = document.getElementById(elementId);
    if (!calendarEl || typeof FullCalendar === 'undefined') {
        console.error('FullCalendar not loaded or element missing');
        return;
    }

    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        headerToolbar: false, // Using custom toolbar
        slotMinTime: '06:00:00',
        slotMaxTime: '23:00:00',
        allDaySlot: false,
        nowIndicator: true,
        editable: true,
        droppable: true,
        selectable: true,
        height: 'auto',
        expandRows: true,
        dayHeaderFormat: { weekday: 'short', day: 'numeric' },
        slotLabelFormat: { hour: 'numeric', minute: '2-digit', hour12: true },

        // Custom event rendering — premium cards
        eventContent: (arg) => {
            const props = arg.event.extendedProps;
            const score = props.priority_score || 5;
            const color = getPriorityColor(score);
            const emoji = getCategoryEmoji(props.category);
            const start = arg.event.start;
            const timeStr = start ? start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true }) : '';

            const isOverdue = arg.event.extendedProps.deadline && new Date(arg.event.extendedProps.deadline) < new Date();
            const overdueClass = isOverdue ? 'overdue-event' : '';
            const overdueBadge = isOverdue ? '<div class="overdue-badge-fc">⚠️ OVERDUE</div><br/>' : '';

            return {
                html: `
                    <div class="${overdueClass}" style="
                        padding: 3px 6px;
                        height: 100%;
                        border-left: 3px solid ${color};
                        background: ${color}18;
                        border-radius: 5px;
                        overflow: hidden;
                    ">
                        <div style="font-size:0.75rem; font-weight:700; color:#F8FAFC; white-space:normal; line-height: 1.2;">
                            ${overdueBadge}${emoji} ${escapeHtml(props.task_title || arg.event.title.replace(/^[^\s]+\s/, ''))}
                        </div>
                        <div style="font-size:0.65rem; color:rgba(248,250,252,0.55); margin-top:2px;">${timeStr} · ${props.category || 'task'}</div>
                    </div>
                `
            };
        },

        // Mouse enter — show popup
        eventMouseEnter: (info) => {
            clearTimeout(_popupTimeout);
            showEventPopup(info);
        },

        // Mouse leave — hide popup with delay
        eventMouseLeave: () => {
            _popupTimeout = setTimeout(() => hidePopup(), 300);
        },

        // Click — complete or crisis
        eventClick: (info) => {
            const props = info.event.extendedProps;
            if (props.task_id) showTaskModal(props.task_id, props.task_title || info.event.title);
        },

        // Drag — reschedule
        eventDrop: async (info) => {
            const props = info.event.extendedProps;
            if (props.task_id) {
                try {
                    const newDate = info.event.start.toISOString();
                    await api.put(`/tasks/${props.task_id}`, { deadline: newDate });
                    showToast('Task rescheduled! 📅');
                } catch {
                    info.revert();
                    showToast('Failed to reschedule', 'error');
                }
            }
        },

        // Click on empty slot — quick add
        select: (info) => {
            const titleInput = document.getElementById('qaTitle');
            const deadlineInput = document.getElementById('qaDeadline');
            if (titleInput) titleInput.focus();
            if (deadlineInput) {
                const d = info.start;
                const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
                deadlineInput.value = local.toISOString().slice(0, 16);
            }
        },
    });

    calendar.render();
    return calendar;
}

/**
 * Load all tasks into calendar.
 * Returns the raw task array for sidebar use.
 */
async function loadCalendarEvents() {
    if (!calendar) return [];

    try {
        const data = await getTasks();
        const tasks = data.tasks || [];
        _calTasks = tasks;

        calendar.getEvents().forEach(e => e.remove());
        const emptyHint = document.getElementById('calendarEmptyHint');

        const pending = tasks.filter(t => t.status !== 'completed');

        if (pending.length === 0) {
            if (emptyHint) emptyHint.classList.remove('hidden');
            return tasks;
        }
        if (emptyHint) emptyHint.classList.add('hidden');

        const now = new Date();
        const weekStart = new Date(now);
        weekStart.setDate(now.getDate() - now.getDay() + 1); // Monday
        weekStart.setHours(9, 0, 0, 0);

        pending.forEach((task, idx) => {
            const score = task.priority_score || 5;
            const color = getPriorityColor(score);

            let startDate;
            if (task.deadline && task.deadline !== 'unknown' && task.deadline !== 'overdue') {
                try {
                    const d = new Date(task.deadline);
                    if (!isNaN(d.getTime())) {
                        // Push past dates to current week
                        startDate = d < now
                            ? (() => { const s = new Date(now); s.setHours(9 + (idx * 2) % 10, 0, 0, 0); return s; })()
                            : d;
                    }
                } catch { /* fall through */ }
            }

            if (!startDate) {
                // Spread across Mon–Fri, 9am–3pm
                const dayOff = idx % 5;
                const hourOff = 9 + Math.floor((idx / 5) % 4) * 2;
                startDate = new Date(weekStart);
                startDate.setDate(weekStart.getDate() + dayOff);
                startDate.setHours(hourOff, 0, 0, 0);
            }

            const hours = task.estimated_hours || 1;
            const endDate = new Date(startDate.getTime() + hours * 3600 * 1000);

            calendar.addEvent({
                title: `${getCategoryEmoji(task.category)} ${task.title}`,
                start: startDate,
                end: endDate,
                backgroundColor: color + '18',
                borderColor: color,
                textColor: '#F8FAFC',
                extendedProps: {
                    task_id: task._id,
                    priority_score: score,
                    category: task.category,
                    task_title: task.title,
                    deadline: task.deadline,
                    estimated_hours: task.estimated_hours || 1,
                },
            });
        });

        return tasks;
    } catch (err) {
        console.error('loadCalendarEvents error:', err);
        return [];
    }
}

/**
 * Show hover popup for an event.
 */
function showEventPopup(info) {
    const popup = document.getElementById('taskPopup');
    if (!popup) return;

    const props = info.event.extendedProps;
    const score = props.priority_score || 5;
    const color = getPriorityColor(score);
    const emoji = getCategoryEmoji(props.category);

    // Populate fields
    document.getElementById('popupEmoji').textContent = emoji;
    document.getElementById('popupTitle').textContent = props.task_title || info.event.title;
    document.getElementById('popupCategory').textContent = (props.category || 'personal').charAt(0).toUpperCase() + (props.category || 'personal').slice(1);

    const scoreEl = document.getElementById('popupScore');
    scoreEl.textContent = `${score.toFixed(1)} / 10`;
    scoreEl.style.background = color + '20';
    scoreEl.style.color = color;

    const start = info.event.start;
    const end = info.event.end;
    const fmtTime = d => d ? d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true }) : '';
    document.getElementById('popupTime').textContent = `${fmtTime(start)} – ${fmtTime(end)}`;
    document.getElementById('popupDuration').textContent = `${props.estimated_hours || 1} hour${(props.estimated_hours || 1) !== 1 ? 's' : ''}`;

    const dl = props.deadline;
    const dlEl = document.getElementById('popupDeadlineRow');
    if (dl && dl !== 'unknown' && dl !== 'overdue') {
        dlEl.classList.remove('hidden');
        document.getElementById('popupDeadline').textContent = getDeadlineText(dl);
    } else {
        dlEl.classList.add('hidden');
    }

    // Wire buttons
    document.getElementById('popupComplete').onclick = () => {
        handleCompleteTask(props.task_id);
        hidePopup();
        setTimeout(() => { loadCalendarEvents().then(t => { renderSidebar(t); updateAIInsight(t); }); }, 600);
    };
    document.getElementById('popupCrisis').onclick = () => {
        handleCrisisMode(props.task_id, props.task_title);
        hidePopup();
    };

    // Position popup near event
    const rect = info.el.getBoundingClientRect();
    const popupW = 320;
    let left = rect.right + 10;
    if (left + popupW > window.innerWidth - 20) left = rect.left - popupW - 10;
    let top = rect.top + window.scrollY;
    if (top + 300 > window.innerHeight + window.scrollY) top = Math.max(10, window.innerHeight + window.scrollY - 310);

    popup.style.left = `${left}px`;
    popup.style.top = `${top}px`;
    popup.classList.add('visible');

    // Keep popup open if hovering it
    popup.onmouseenter = () => clearTimeout(_popupTimeout);
    popup.onmouseleave = () => { _popupTimeout = setTimeout(hidePopup, 150); };
}

function hidePopup() {
    const popup = document.getElementById('taskPopup');
    if (popup) popup.classList.remove('visible');
}

/**
 * Show task modal (for click action).
 */
function showTaskModal(taskId, title) {
    const modal = document.getElementById('taskModal');
    if (modal) {
        modal.querySelector('.modal-title').textContent = title;
        modal.dataset.taskId = taskId;
        modal.style.display = 'flex';
    }
}
