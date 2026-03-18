/**
 * Main Application Module
 * Handles UI interactions and application logic (mobile-first)
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('App initialized');
    initBottomNav();
    init();
});

/**
 * Initialize the application
 */
async function init() {
    // Check backend health
    try {
        const health = await api.get('/health');
        console.log('Backend status:', health);
    } catch (error) {
        console.warn('Backend not available:', error.message);
    }
}

/**
 * Initialize bottom navigation tab switching
 */
function initBottomNav() {
    const navItems = document.querySelectorAll('.bottom-nav__item');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            // Remove active from all
            navItems.forEach(i => i.classList.remove('bottom-nav__item--active'));
            // Add active to clicked
            item.classList.add('bottom-nav__item--active');

            const tab = item.dataset.tab;
            onTabChange(tab);
        });
    });
}

/**
 * Handle tab change
 * @param {string} tab - Tab identifier
 */
function onTabChange(tab) {
    console.log('Tab changed:', tab);
    // AI: Implement tab-specific content loading here
}

/**
 * Show loading state in a container
 * @param {HTMLElement} container - Target container
 */
function showLoading(container) {
    container.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
        </div>
    `;
}

/**
 * Show error message in a container
 * @param {HTMLElement} container - Target container
 * @param {string} message - Error message
 */
function showError(container, message) {
    container.innerHTML = `
        <div class="error-message">
            <strong>Error:</strong> ${escapeHtml(message)}
        </div>
    `;
}

/**
 * Show empty state in a container
 * @param {HTMLElement} container - Target container
 * @param {string} message - Empty state message
 * @param {string} icon - Optional icon/emoji for empty state
 */
function showEmpty(container, message = 'No data available', icon = '') {
    container.innerHTML = `
        <div class="empty-state">
            ${icon ? `<div class="empty-state__icon">${icon}</div>` : ''}
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

/**
 * Open a bottom sheet modal
 * @param {string} content - HTML content for the sheet
 * @returns {HTMLElement} The overlay element (for closing)
 */
function openBottomSheet(content) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="bottom-sheet">
            <div class="bottom-sheet__handle"></div>
            ${content}
        </div>
    `;

    document.body.appendChild(overlay);

    // Trigger animation
    requestAnimationFrame(() => {
        overlay.classList.add('modal-overlay--active');
    });

    // Close on overlay tap (not sheet)
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeBottomSheet(overlay);
        }
    });

    return overlay;
}

/**
 * Close a bottom sheet modal
 * @param {HTMLElement} overlay - The overlay element
 */
function closeBottomSheet(overlay) {
    overlay.classList.remove('modal-overlay--active');
    overlay.addEventListener('transitionend', () => {
        overlay.remove();
    }, { once: true });
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format date for display
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
}

/**
 * Validate form data
 * @param {object} data - Form data object
 * @param {object} rules - Validation rules
 * @returns {object} { valid: boolean, errors: object }
 */
function validateForm(data, rules) {
    const errors = {};

    for (const [field, rule] of Object.entries(rules)) {
        const value = data[field];

        if (rule.required && (!value || value.trim() === '')) {
            errors[field] = `${rule.label || field} is required`;
            continue;
        }

        if (rule.minLength && value && value.length < rule.minLength) {
            errors[field] = `${rule.label || field} must be at least ${rule.minLength} characters`;
        }

        if (rule.maxLength && value && value.length > rule.maxLength) {
            errors[field] = `${rule.label || field} must be at most ${rule.maxLength} characters`;
        }

        if (rule.pattern && value && !rule.pattern.test(value)) {
            errors[field] = rule.patternMessage || `${rule.label || field} is invalid`;
        }
    }

    return {
        valid: Object.keys(errors).length === 0,
        errors,
    };
}

/**
 * Show form validation errors
 * @param {HTMLFormElement} form - Form element
 * @param {object} errors - Error messages by field name
 */
function showFormErrors(form, errors) {
    // Clear existing errors
    form.querySelectorAll('.form-error').forEach(el => el.remove());
    form.querySelectorAll('.form-input, .form-textarea').forEach(el => {
        el.style.borderColor = '';
    });

    // Show new errors
    for (const [field, message] of Object.entries(errors)) {
        const input = form.querySelector(`[name="${field}"]`);
        if (input) {
            input.style.borderColor = '#ef4444';
            const errorEl = document.createElement('p');
            errorEl.className = 'form-error';
            errorEl.textContent = message;
            input.parentNode.appendChild(errorEl);
        }
    }
}

/**
 * Clear form errors
 * @param {HTMLFormElement} form - Form element
 */
function clearFormErrors(form) {
    form.querySelectorAll('.form-error').forEach(el => el.remove());
    form.querySelectorAll('.form-input, .form-textarea').forEach(el => {
        el.style.borderColor = '';
    });
}

/**
 * Get form data as object
 * @param {HTMLFormElement} form - Form element
 * @returns {object} Form data
 */
function getFormData(form) {
    const formData = new FormData(form);
    const data = {};
    for (const [key, value] of formData.entries()) {
        data[key] = value;
    }
    return data;
}
