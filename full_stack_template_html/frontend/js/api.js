/**
 * API Helper Module
 * Handles all communication with the backend via maxflow.app proxy
 *
 * Request format:
 *   GET: ?request_input=JSON.stringify({ option, parameters })
 *   POST: body = { request_input: { option, parameters } }  (used for file uploads with base64)
 *
 * Response format:
 *   { "json_response": { ...actual data... } }
 *
 * Usage in app.js (unchanged):
 *   api.get('/api/health')
 *   api.post('/api/items', { name: 'Item 1' })
 *   api.uploadForm('/api/items', formData)
 */

const API_URL = 'https://maxflow.app/api/';

/**
 * Convert a Blob/File to base64 string
 */
function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Unwrap json_response and check for errors
 */
function processResponse(data, response) {
  const result =
    data && data.json_response !== undefined ? data.json_response : data;

  if (!response.ok) {
    throw new Error(
      result?.detail || result?.error || `HTTP ${response.status}`
    );
  }

  if (result && result.error) {
    throw new Error(result.error);
  }

  return result;
}

/**
 * Send GET request with request_input as query parameter
 */
async function sendGet(option, parameters = {}) {
  const requestInput = JSON.stringify({ option, parameters });
  const url = `${API_URL}?request_input=${encodeURIComponent(requestInput)}`;

  const response = await fetch(url);
  const data = await response.json();
  return processResponse(data, response);
}

/**
 * Send POST request with JSON body (for large payloads like base64 files)
 */
async function sendPost(option, parameters = {}) {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request_input: { option, parameters } }),
  });

  const data = await response.json();
  return processResponse(data, response);
}

const api = {
  /**
   * Make a GET request
   * @param {string} option - API path (e.g., '/api/health')
   * @param {object} parameters - Request parameters
   * @returns {Promise<any>} Unwrapped response data
   */
  async get(option, parameters = {}) {
    return sendGet(option, parameters);
  },

  /**
   * Make a POST request
   * @param {string} option - API path (e.g., '/api/items')
   * @param {object} parameters - Request parameters
   * @returns {Promise<any>} Unwrapped response data
   */
  async post(option, parameters = {}) {
    return sendGet(option, parameters);
  },

  /**
   * Make a PUT request
   * @param {string} option - API path
   * @param {object} parameters - Request parameters
   * @returns {Promise<any>} Unwrapped response data
   */
  async put(option, parameters = {}) {
    return sendGet(option, parameters);
  },

  /**
   * Make a DELETE request
   * @param {string} option - API path
   * @param {object} parameters - Request parameters
   * @returns {Promise<any>} Unwrapped response data
   */
  async delete(option, parameters = {}) {
    return sendGet(option, parameters);
  },

  /**
   * Upload files with FormData
   * Converts Blob/File values to base64 and sends as JSON via POST
   * @param {string} option - API path (e.g., '/api/reports')
   * @param {FormData} formData - FormData object with files and fields
   * @returns {Promise<any>} Unwrapped response data
   */
  async uploadForm(option, formData) {
    const parameters = {};

    for (const [key, value] of formData.entries()) {
      if (value instanceof Blob || value instanceof File) {
        const base64 = await blobToBase64(value);
        const fileObj = {
          filename: value.name || `${key}.bin`,
          data: base64,
          content_type: value.type || 'application/octet-stream',
        };

        if (key in parameters && Array.isArray(parameters[key])) {
          parameters[key].push(fileObj);
        } else if (key in parameters) {
          parameters[key] = [parameters[key], fileObj];
        } else {
          parameters[key] = fileObj;
        }
      } else {
        parameters[key] = value;
      }
    }

    return sendPost(option, parameters);
  },
};

// Export for use in other modules
window.api = api;
