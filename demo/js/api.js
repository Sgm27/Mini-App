/**
 * API wrapper for Mini App Storage
 * Based on mini_app_storage.md documentation
 */
const CONFIG = {
    uid: 'ybG2ZuM1',
    baseUrl: 'https://maxflow.ai',
    articleStorageId: 58,
    categoryStorageId: 59,
    accessToken: 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJuaHVuZ3RydW9uZ0BtYXhmbG93dGVjaC5jb20iLCJpYXQiOjE3NzQwMTM5MzQsIm5iZiI6MTc3NDAxMzkzNCwianRpIjoiYWQ4MmQ0YTQtZTlkZC00YzRjLTkzYjktYjk1MDMxODI2NGY4IiwiZXhwIjoxODA1NTQ5OTM0LCJ0eXBlIjoiYWNjZXNzIiwiZnJlc2giOmZhbHNlLCJpZGVudGl0eSI6Im5odW5ndHJ1b25nQG1heGZsb3d0ZWNoLmNvbSJ9.UiYwjCkQDG4_Si6baVFxB2dsXanXW0gL2IU0FzkvCCgzmO4XROPedhqsCZlFuCV7vascP0AEQfbz4idxehKSRoLIHODfCzmzw5GRYYSWiqfH7RmiAECHLcQxcMbDnUuzmSpQe3XPd7wNGzqSv7XoFoL6z0K-3CrbxLzgHYs0leQ'
};

const API = {
    _base() {
        return `${CONFIG.baseUrl}/api/app/${CONFIG.uid}/db`;
    },

    _headers() {
        const h = { 'Content-Type': 'application/json' };
        if (CONFIG.accessToken) {
            h['Authorization'] = `Bearer ${CONFIG.accessToken}`;
        }
        return h;
    },

    async _post(storageId, action, body) {
        const url = `${this._base()}/${storageId}/${action}`;
        const res = await fetch(url, {
            method: 'POST',
            headers: this._headers(),
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || 'API Error');
        }
        return res.json();
    },

    async _put(storageId, action, body) {
        const url = `${this._base()}/${storageId}/${action}`;
        const res = await fetch(url, {
            method: 'PUT',
            headers: this._headers(),
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || 'API Error');
        }
        return res.json();
    },

    // ===== Category API =====
    async getCategories() {
        const data = await this._post(CONFIG.categoryStorageId, 'find', {
            query: {},
            sort: [['order', 1]],
            limit: 100
        });
        return data.documents || [];
    },

    async insertCategory(doc) {
        return this._post(CONFIG.categoryStorageId, 'insert', { documents: doc });
    },

    async updateCategory(id, updates) {
        return this._put(CONFIG.categoryStorageId, 'update', {
            filter: { _id: id },
            update: { $set: updates },
            many: false
        });
    },

    async deleteCategory(id) {
        return this._post(CONFIG.categoryStorageId, 'delete', {
            filter: { _id: id },
            many: false
        });
    },

    // ===== Article API =====
    async getArticles({ query = {}, sort = [['created_at', -1]], limit = 20, skip = 0 } = {}) {
        const data = await this._post(CONFIG.articleStorageId, 'find', {
            query,
            sort,
            limit,
            skip
        });
        return data;
    },

    async getArticleById(id) {
        const data = await this._post(CONFIG.articleStorageId, 'find', {
            query: { _id: id },
            limit: 1
        });
        return (data.documents || [])[0] || null;
    },

    async insertArticle(doc) {
        return this._post(CONFIG.articleStorageId, 'insert', { documents: doc });
    },

    async updateArticle(id, updates) {
        return this._put(CONFIG.articleStorageId, 'update', {
            filter: { _id: id },
            update: { $set: updates },
            many: false
        });
    },

    async deleteArticle(id) {
        return this._post(CONFIG.articleStorageId, 'delete', {
            filter: { _id: id },
            many: false
        });
    },

    async countArticles(query = {}) {
        const data = await this._post(CONFIG.articleStorageId, 'count', { query });
        return data.count || 0;
    }
};
