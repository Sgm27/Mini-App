/**
 * Main Application Module
 * Handles UI interactions and application logic
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('App initialized');
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
 */
function showEmpty(container, message = 'No data available') {
    container.innerHTML = `
        <div class="empty-state">
            <p>${escapeHtml(message)}</p>
        </div>
    `;
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
