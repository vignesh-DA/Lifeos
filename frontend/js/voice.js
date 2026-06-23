/**
 * LIFEOS — Web Speech API Voice Input Handler
 * Real-time speech-to-text for brain dump.
 */

let recognition = null;
let isListening = false;
let finalTranscript = '';
let silenceTimer = null;

/**
 * Initialize voice recognition.
 */
function initVoiceInput(textareaId, statusId, btnId) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.disabled = true;
            btn.title = 'Speech recognition not supported in this browser';
        }
        console.warn('Web Speech API not supported');
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    const textarea = document.getElementById(textareaId);
    const status = document.getElementById(statusId);
    const btn = document.getElementById(btnId);

    recognition.onstart = () => {
        isListening = true;
        if (btn) {
            btn.classList.add('active');
            btn.innerHTML = '🔴';
        }
        if (status) {
            status.textContent = 'Listening...';
            status.style.color = 'var(--accent-crisis)';
        }
    };

    recognition.onresult = (event) => {
        let interimTranscript = '';

        // Reset silence timer
        clearTimeout(silenceTimer);
        silenceTimer = setTimeout(() => {
            if (isListening) {
                stopVoice();
            }
        }, 3000); // Stop after 3 seconds of silence

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript + ' ';
            } else {
                interimTranscript += transcript;
            }
        }

        if (textarea) {
            textarea.value = finalTranscript + interimTranscript;
            textarea.scrollTop = textarea.scrollHeight;
        }

        if (status && interimTranscript) {
            status.textContent = '🎤 Listening... (speak naturally)';
        }
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        if (status) {
            status.textContent = `Error: ${event.error}`;
            status.style.color = 'var(--accent-crisis)';
        }
        stopVoice();
    };

    recognition.onend = () => {
        isListening = false;
        if (btn) {
            btn.classList.remove('active');
            btn.innerHTML = '🎙️';
        }
        if (status) {
            if (finalTranscript.trim()) {
                status.textContent = '✅ Voice captured! Review and submit.';
                status.style.color = 'var(--accent-success)';
            } else {
                status.textContent = 'Click mic to start speaking';
                status.style.color = 'var(--text-tertiary)';
            }
        }
    };
}

/**
 * Toggle voice recording.
 */
function toggleVoice() {
    if (isListening) {
        stopVoice();
    } else {
        startVoice();
    }
}

/**
 * Start listening.
 */
function startVoice() {
    if (!recognition) {
        showToast('Voice input not supported in this browser', 'warning');
        return;
    }
    finalTranscript = '';
    try {
        recognition.start();
    } catch (e) {
        console.error('Failed to start recognition:', e);
    }
}

/**
 * Stop listening.
 */
function stopVoice() {
    clearTimeout(silenceTimer);
    if (recognition && isListening) {
        recognition.stop();
    }
}
