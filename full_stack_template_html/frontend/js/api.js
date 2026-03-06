/**
 * API Helper Module
 * Handles all communication with the backend
 *
 * Usage in app.js:
 *   api.get('/api/health')
 *   api.post('/api/items', { name: 'Item 1' })
 *   api.put('/api/items/1', { name: 'Updated' })
 *   api.delete('/api/items/1')
 *   api.uploadForm('/api/upload', formData)
 *
 * Upload file:
 *   const formData = new FormData();
 *   formData.append('file', fileInput.files[0]);
 *   const { file_url } = await api.uploadForm('/api/upload', formData);
 */

const API_URL = 'http://localhost:2701';

/**
 * Process response: check status and parse JSON
 */
async function processResponse(response) {
  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail || data?.error || `HTTP ${response.status}`
    );
  }

  if (data && data.error) {
    throw new Error(data.error);
  }

  return data;
}

const api = {
  /**
   * Make a GET request
   * @param {string} path - API path (e.g., '/api/health')
   * @param {object} params - Query parameters
   * @returns {Promise<any>} Response data
   */
  async get(path, params = {}) {
    const url = new URL(`${API_URL}${path}`);
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, value);
      }
    });

    const response = await fetch(url.toString());
    return processResponse(response);
  },

  /**
   * Make a POST request
   * @param {string} path - API path (e.g., '/api/items')
   * @param {object} body - Request body
   * @returns {Promise<any>} Response data
   */
  async post(path, body = {}) {
    const response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return processResponse(response);
  },

  /**
   * Make a PUT request
   * @param {string} path - API path (e.g., '/api/items/1')
   * @param {object} body - Request body
   * @returns {Promise<any>} Response data
   */
  async put(path, body = {}) {
    const response = await fetch(`${API_URL}${path}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return processResponse(response);
  },

  /**
   * Make a DELETE request
   * @param {string} path - API path (e.g., '/api/items/1')
   * @param {object} body - Optional request body
   * @returns {Promise<any>} Response data
   */
  async delete(path, body = null) {
    const options = { method: 'DELETE' };
    if (body) {
      options.headers = { 'Content-Type': 'application/json' };
      options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_URL}${path}`, options);
    return processResponse(response);
  },

  /**
   * Upload files with FormData
   * @param {string} path - API path (e.g., '/api/upload')
   * @param {FormData} formData - FormData object with files and fields
   * @returns {Promise<any>} Response data
   */
  async uploadForm(path, formData) {
    const response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      body: formData,
    });
    return processResponse(response);
  },
};

// Export for use in other modules
window.api = api;
