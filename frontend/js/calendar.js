/**
 * LIFEOS — FullCalendar.js Setup
 * Calendar view with color-coded task events.
 */

let calendar = null;

/**
 * Initialize FullCalendar with task events.
 */
function initCalendar(elementId) {
    const calendarEl = document.getElementById(elementId);
    if (!calendarEl || typeof FullCalendar === 'undefined') {
        console.error('FullCalendar not loaded or element not found');
        return;
    }

    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'timeGridWeek,timeGridDay,listWeek',
        },
        slotMinTime: '06:00:00',
        slotMaxTime: '23:00:00',
        allDaySlot: false,
        nowIndicator: true,
        editable: true,
        droppable: true,
        selectable: true,
        height: 'auto',
        expandRows: true,

        // Theme
        themeSystem: 'standard',

        // Event colors by priority
        eventDidMount: (info) => {
            const priority = info.event.extendedProps.priority_score || 5;
            if (priority >= 8) {
                info.el.style.borderLeft = '3px solid #EF4444';
            } else if (priority >= 5) {
                info.el.style.borderLeft = '3px solid #F59E0B';
            } else {
                info.el.style.borderLeft = '3px solid #10B981';
            }
            info.el.style.fontSize = '0.8rem';
        },

        // Event click — open edit modal
        eventClick: (info) => {
            const taskId = info.event.extendedProps.task_id;
            const title = info.event.title;
            if (taskId) {
                showTaskModal(taskId, title);
            }
        },

        // Event drag — update task time
        eventDrop: async (info) => {
            const taskId = info.event.extendedProps.task_id;
            if (taskId) {
                try {
                    const newDate = info.event.start.toISOString().split('T')[0];
                    await api.put(`/tasks/${taskId}`, { deadline: newDate });
                    showToast('Task rescheduled! 📅');
                } catch (err) {
                    info.revert();
                    showToast('Failed to reschedule', 'error');
                }
            }
        },

        // Custom styling
        dayHeaderFormat: { weekday: 'short', day: 'numeric' },
        slotLabelFormat: { hour: 'numeric', minute: '2-digit', hour12: true },
    });

    calendar.render();

    // Apply dark theme styles
    applyCalendarTheme();

    return calendar;
}

/**
 * Load tasks into calendar as events.
 */
async function loadCalendarEvents() {
    if (!calendar) return;

    try {
        const data = await getTasks();
        const tasks = data.tasks || [];

        // Remove existing events
        calendar.getEvents().forEach(e => e.remove());

        const pending = tasks.filter(t => t.status !== 'completed');

        if (pending.length === 0) {
            // Show empty state hint on calendar
            const el = document.getElementById('calendarEmptyHint');
            if (el) el.classList.remove('hidden');
            return;
        }

        // Spread tasks across the week intelligently
        const now = new Date();
        const weekStart = new Date(now);
        weekStart.setDate(now.getDate() - now.getDay() + 1); // Monday
        weekStart.setHours(9, 0, 0, 0);

        pending.forEach((task, idx) => {
            const priority = task.priority_score || 5;
            let color = '#6366F1';
            if (priority >= 8) color = '#EF4444';
            else if (priority >= 5) color = '#F59E0B';
            else color = '#10B981';

            let startDate;
            if (task.deadline && task.deadline !== 'unknown' && task.deadline !== 'overdue') {
                try {
                    startDate = new Date(task.deadline);
                    // if date is in the past, push to today
                    if (startDate < now) {
                        startDate = new Date(now);
                        startDate.setHours(9 + (idx % 8), 0, 0, 0);
                    }
                } catch { startDate = null; }
            }

            if (!startDate) {
                // Spread tasks Mon–Fri based on priority (high priority = earlier)
                const dayOffset = Math.floor(idx % 5); // 0=Mon … 4=Fri
                const hourOffset = 9 + Math.floor((idx / 5) % 4) * 2; // 9,11,13,15
                startDate = new Date(weekStart);
                startDate.setDate(weekStart.getDate() + dayOffset);
                startDate.setHours(hourOffset, 0, 0, 0);
            }

            const hours = task.estimated_hours || 1;
            const endDate = new Date(startDate.getTime() + hours * 60 * 60 * 1000);

            calendar.addEvent({
                title: `${getCategoryEmoji(task.category)} ${task.title}`,
                start: startDate,
                end: endDate,
                backgroundColor: color + '30',
                borderColor: color,
                textColor: '#F8FAFC',
                extendedProps: {
                    task_id: task._id,
                    priority_score: priority,
                    category: task.category,
                    task_title: task.title,
                },
            });
        });
    } catch (err) {
        console.error('Failed to load calendar events:', err);
    }
}

/**
 * Get emoji for category.
 */
function getCategoryEmoji(category) {
    const emojis = {
        academic: '📚',
        career: '💼',
        finance: '💰',
        personal: '👤',
        health: '🏃',
    };
    return emojis[category] || '📋';
}

/**
 * Show task edit modal.
 */
function showTaskModal(taskId, title) {
    const modal = document.getElementById('taskModal');
    if (modal) {
        modal.querySelector('.modal-title').textContent = title;
        modal.dataset.taskId = taskId;
        modal.style.display = 'flex';
    }
}

/**
 * Apply dark theme to FullCalendar.
 */
function applyCalendarTheme() {
    const style = document.createElement('style');
    style.textContent = `
        .fc {
            --fc-border-color: #2D2D4E;
            --fc-button-bg-color: #1A1A2E;
            --fc-button-border-color: #2D2D4E;
            --fc-button-text-color: #F8FAFC;
            --fc-button-hover-bg-color: #252540;
            --fc-button-hover-border-color: #6366F1;
            --fc-button-active-bg-color: #6366F1;
            --fc-button-active-border-color: #6366F1;
            --fc-today-bg-color: rgba(99, 102, 241, 0.08);
            --fc-neutral-bg-color: #0F0F1A;
            --fc-page-bg-color: #0F0F1A;
            --fc-now-indicator-color: #EF4444;
        }
        .fc .fc-timegrid-slot { height: 3rem; }
        .fc .fc-col-header-cell { background: #1A1A2E; }
        .fc .fc-timegrid-col { background: transparent; }
        .fc .fc-event { border-radius: 4px; padding: 2px 4px; }
        .fc .fc-toolbar-title { font-size: 1.2rem; font-weight: 600; }
    `;
    document.head.appendChild(style);
}
