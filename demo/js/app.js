/**
 * News Reader App
 */
const app = {
    categories: [],
    articles: [],
    currentPage: 'home',
    currentCategory: null,
    adminTab: 'articles',
    editingArticle: null,
    editingCategory: null,
    articleSkip: 0,
    articleLimit: 12,
    totalArticles: 0,

    // ===== Init =====
    async init() {
        this.showLoading(true);
        try {
            await this.loadCategories();
            this.navigate('home');
        } catch (e) {
            this.toast('Khong the ket noi den server: ' + e.message, 'error');
        }
        this.showLoading(false);
    },

    // ===== Data Loading =====
    async loadCategories() {
        this.categories = await API.getCategories();
        this.renderCategoryNav();
    },

    async loadArticles(reset = true) {
        if (reset) {
            this.articleSkip = 0;
            this.articles = [];
        }
        const query = {};
        if (this.currentCategory) {
            query.category_id = this.currentCategory;
        }
        query.status = 'published';
        const data = await API.getArticles({
            query,
            limit: this.articleLimit,
            skip: this.articleSkip
        });
        if (reset) {
            this.articles = data.documents || [];
        } else {
            this.articles = this.articles.concat(data.documents || []);
        }
        this.totalArticles = data.total || 0;
    },

    // ===== Navigation =====
    navigate(page, params) {
        this.currentPage = page;
        switch (page) {
            case 'home':
                this.currentCategory = params || null;
                this.renderHome();
                break;
            case 'admin':
                this.renderAdmin();
                break;
        }
    },

    // ===== Category Nav =====
    renderCategoryNav() {
        const nav = document.getElementById('categoryNav');
        let html = `<button class="nav-item ${!this.currentCategory ? 'active' : ''}" onclick="app.navigate('home')">Trang chu</button>`;
        this.categories.forEach(cat => {
            const active = this.currentCategory === cat._id ? 'active' : '';
            html += `<button class="nav-item ${active}" onclick="app.navigate('home', '${cat._id}')">${this._esc(cat.name)}</button>`;
        });
        nav.innerHTML = html;
    },

    // ===== Home Page =====
    async renderHome() {
        const main = document.getElementById('mainContent');
        main.innerHTML = '<div class="spinner" style="margin:40px auto"></div>';

        this.showLoading(true);
        await this.loadArticles(true);
        this.showLoading(false);

        this.renderCategoryNav();

        if (this.articles.length === 0) {
            main.innerHTML = `
                <div class="empty-state">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 12h10"/>
                    </svg>
                    <h3>Chua co bai viet nao</h3>
                    <p>Hay vao trang quan ly de tao bai viet hoac them du lieu mau.</p>
                    <button class="btn btn-primary" onclick="app.navigate('admin')">Quan ly noi dung</button>
                </div>`;
            return;
        }

        let html = '';

        // Featured section (first 3 articles)
        if (!this.currentCategory && this.articles.length >= 3) {
            html += '<div class="featured-grid">';
            html += this._renderFeaturedCard(this.articles[0], true);
            html += this._renderFeaturedCard(this.articles[1], false);
            html += this._renderFeaturedCard(this.articles[2], false);
            html += '</div>';
        }

        // Category title if filtered
        if (this.currentCategory) {
            const cat = this.categories.find(c => c._id === this.currentCategory);
            if (cat) html += `<div class="section-title">${this._esc(cat.name)}</div>`;
        } else {
            html += '<div class="section-title">Bai viet moi nhat</div>';
        }

        // Article grid
        const startIdx = (!this.currentCategory && this.articles.length >= 3) ? 3 : 0;
        const gridArticles = this.articles.slice(startIdx);

        if (gridArticles.length > 0) {
            html += '<div class="article-grid">';
            gridArticles.forEach(a => {
                html += this._renderArticleCard(a);
            });
            html += '</div>';
        }

        // Load more
        if (this.articles.length < this.totalArticles) {
            html += `<div class="load-more">
                <button class="btn btn-outline" onclick="app.loadMore()">Xem them bai viet</button>
            </div>`;
        }

        html += `<div class="pagination-info">Hien thi ${this.articles.length} / ${this.totalArticles} bai viet</div>`;

        main.innerHTML = html;
    },

    async loadMore() {
        this.articleSkip += this.articleLimit;
        this.showLoading(true);
        await this.loadArticles(false);
        this.showLoading(false);
        // Re-render home without resetting
        this.renderHomeContent();
    },

    renderHomeContent() {
        // Same as renderHome but without reloading data
        const main = document.getElementById('mainContent');
        let html = '';

        if (!this.currentCategory && this.articles.length >= 3) {
            html += '<div class="featured-grid">';
            html += this._renderFeaturedCard(this.articles[0], true);
            html += this._renderFeaturedCard(this.articles[1], false);
            html += this._renderFeaturedCard(this.articles[2], false);
            html += '</div>';
        }

        if (this.currentCategory) {
            const cat = this.categories.find(c => c._id === this.currentCategory);
            if (cat) html += `<div class="section-title">${this._esc(cat.name)}</div>`;
        } else {
            html += '<div class="section-title">Bai viet moi nhat</div>';
        }

        const startIdx = (!this.currentCategory && this.articles.length >= 3) ? 3 : 0;
        const gridArticles = this.articles.slice(startIdx);

        if (gridArticles.length > 0) {
            html += '<div class="article-grid">';
            gridArticles.forEach(a => {
                html += this._renderArticleCard(a);
            });
            html += '</div>';
        }

        if (this.articles.length < this.totalArticles) {
            html += `<div class="load-more">
                <button class="btn btn-outline" onclick="app.loadMore()">Xem them bai viet</button>
            </div>`;
        }

        html += `<div class="pagination-info">Hien thi ${this.articles.length} / ${this.totalArticles} bai viet</div>`;
        main.innerHTML = html;
    },

    _renderFeaturedCard(article, isMain) {
        const cat = this.categories.find(c => c._id === article.category_id);
        const catName = cat ? cat.name : '';
        const imgHtml = article.thumbnail
            ? `<img src="${this._esc(article.thumbnail)}" alt="${this._esc(article.title)}">`
            : `<div class="placeholder-img">${this._esc(article.title.charAt(0))}</div>`;

        return `
            <div class="featured-card ${isMain ? 'main-featured' : ''}" onclick="app.openArticle('${article._id}')">
                ${imgHtml}
                <div class="featured-overlay">
                    ${catName ? `<span class="featured-category">${this._esc(catName)}</span>` : ''}
                    <div class="featured-title">${this._esc(article.title)}</div>
                    <div class="featured-meta">${this._esc(article.author || '')} &bull; ${this._formatDate(article.created_at)}</div>
                </div>
            </div>`;
    },

    _renderArticleCard(article) {
        const cat = this.categories.find(c => c._id === article.category_id);
        const catName = cat ? cat.name : '';
        const imgHtml = article.thumbnail
            ? `<img class="article-thumb" src="${this._esc(article.thumbnail)}" alt="${this._esc(article.title)}">`
            : `<div class="article-thumb placeholder-img">${this._esc(article.title.charAt(0))}</div>`;

        return `
            <div class="article-card" onclick="app.openArticle('${article._id}')">
                ${imgHtml}
                <div class="article-body">
                    ${catName ? `<div class="article-cat">${this._esc(catName)}</div>` : ''}
                    <div class="article-title">${this._esc(article.title)}</div>
                    <div class="article-summary">${this._esc(article.summary || '')}</div>
                    <div class="article-footer">
                        <span>${this._esc(article.author || 'Anonymous')}</span>
                        <span>${this._formatDate(article.created_at)}</span>
                    </div>
                </div>
            </div>`;
    },

    // ===== Article Detail =====
    async openArticle(id) {
        this.showLoading(true);
        try {
            const article = await API.getArticleById(id);
            if (!article) {
                this.toast('Khong tim thay bai viet', 'error');
                return;
            }
            const cat = this.categories.find(c => c._id === article.category_id);
            const catName = cat ? cat.name : '';

            const detail = document.getElementById('articleDetail');
            detail.innerHTML = `
                ${catName ? `<div class="detail-category">${this._esc(catName)}</div>` : ''}
                <h1 class="detail-title">${this._esc(article.title)}</h1>
                <div class="detail-meta">
                    <span>${this._esc(article.author || 'Anonymous')}</span>
                    <span>${this._formatDate(article.created_at)}</span>
                </div>
                ${article.thumbnail ? `<img class="detail-thumb" src="${this._esc(article.thumbnail)}" alt="">` : ''}
                <div class="detail-content">${article.content || ''}</div>
            `;

            document.getElementById('articleModal').classList.add('open');
            document.body.style.overflow = 'hidden';
        } catch (e) {
            this.toast('Loi: ' + e.message, 'error');
        }
        this.showLoading(false);
    },

    closeArticle() {
        document.getElementById('articleModal').classList.remove('open');
        document.body.style.overflow = '';
    },

    // ===== Admin Panel =====
    async renderAdmin() {
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="admin-layout">
                <aside class="admin-sidebar">
                    <h3>Quan ly</h3>
                    <button class="admin-nav-item ${this.adminTab === 'articles' ? 'active' : ''}" onclick="app.switchAdminTab('articles')">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/></svg>
                        Bai viet
                    </button>
                    <button class="admin-nav-item ${this.adminTab === 'categories' ? 'active' : ''}" onclick="app.switchAdminTab('categories')">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
                        Danh muc
                    </button>
                    <button class="admin-nav-item ${this.adminTab === 'seed' ? 'active' : ''}" onclick="app.switchAdminTab('seed')">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M2 12h20"/></svg>
                        Du lieu mau
                    </button>
                </aside>
                <div class="admin-content" id="adminContent"></div>
            </div>`;

        this.switchAdminTab(this.adminTab);
    },

    switchAdminTab(tab) {
        this.adminTab = tab;
        // Update sidebar active
        document.querySelectorAll('.admin-nav-item').forEach((el, i) => {
            const tabs = ['articles', 'categories', 'seed'];
            el.classList.toggle('active', tabs[i] === tab);
        });

        switch (tab) {
            case 'articles': this.renderAdminArticles(); break;
            case 'categories': this.renderAdminCategories(); break;
            case 'seed': this.renderSeedPanel(); break;
        }
    },

    // ----- Admin Articles -----
    async renderAdminArticles() {
        const content = document.getElementById('adminContent');
        content.innerHTML = '<div class="spinner" style="margin:40px auto"></div>';

        const data = await API.getArticles({ query: {}, limit: 100 });
        const articles = data.documents || [];

        if (articles.length === 0) {
            content.innerHTML = `
                <div class="admin-header">
                    <h2>Bai viet</h2>
                    <button class="btn btn-primary" onclick="app.showArticleForm()">+ Tao bai viet</button>
                </div>
                <div class="empty-state">
                    <h3>Chua co bai viet</h3>
                    <p>Tao bai viet dau tien hoac them du lieu mau.</p>
                </div>`;
            return;
        }

        let rows = '';
        articles.forEach(a => {
            const cat = this.categories.find(c => c._id === a.category_id);
            const statusClass = a.status === 'published' ? 'badge-published' : 'badge-draft';
            const statusText = a.status === 'published' ? 'Published' : 'Draft';
            rows += `<tr>
                <td class="td-title">${this._esc(a.title)}</td>
                <td>${cat ? this._esc(cat.name) : '-'}</td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
                <td>${this._formatDate(a.created_at)}</td>
                <td>
                    <div class="table-actions">
                        <button class="btn btn-outline btn-sm" onclick="app.showArticleForm('${a._id}')">Sua</button>
                        <button class="btn btn-danger btn-sm" onclick="app.deleteArticleConfirm('${a._id}')">Xoa</button>
                    </div>
                </td>
            </tr>`;
        });

        content.innerHTML = `
            <div class="admin-header">
                <h2>Bai viet (${articles.length})</h2>
                <button class="btn btn-primary" onclick="app.showArticleForm()">+ Tao bai viet</button>
            </div>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>Tieu de</th><th>Danh muc</th><th>Trang thai</th><th>Ngay tao</th><th>Thao tac</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>`;
    },

    async showArticleForm(id) {
        const content = document.getElementById('adminContent');
        let article = { title: '', summary: '', content: '', author: '', thumbnail: '', category_id: '', status: 'draft' };

        if (id) {
            this.showLoading(true);
            const found = await API.getArticleById(id);
            if (found) article = found;
            this.showLoading(false);
        }

        this.editingArticle = id || null;

        let catOptions = '<option value="">-- Chon danh muc --</option>';
        this.categories.forEach(c => {
            const sel = c._id === article.category_id ? 'selected' : '';
            catOptions += `<option value="${c._id}" ${sel}>${this._esc(c.name)}</option>`;
        });

        content.innerHTML = `
            <div class="admin-header">
                <h2>${id ? 'Sua bai viet' : 'Tao bai viet moi'}</h2>
            </div>
            <form onsubmit="app.saveArticle(event)">
                <div class="form-row">
                    <div class="form-group">
                        <label>Tieu de *</label>
                        <input type="text" id="artTitle" value="${this._esc(article.title)}" required>
                    </div>
                    <div class="form-group">
                        <label>Tac gia</label>
                        <input type="text" id="artAuthor" value="${this._esc(article.author || '')}">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Danh muc</label>
                        <select id="artCategory">${catOptions}</select>
                    </div>
                    <div class="form-group">
                        <label>Trang thai</label>
                        <select id="artStatus">
                            <option value="draft" ${article.status === 'draft' ? 'selected' : ''}>Draft</option>
                            <option value="published" ${article.status === 'published' ? 'selected' : ''}>Published</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label>Anh dai dien (URL)</label>
                    <input type="url" id="artThumb" value="${this._esc(article.thumbnail || '')}" placeholder="https://...">
                </div>
                <div class="form-group">
                    <label>Tom tat</label>
                    <textarea id="artSummary" rows="3" style="min-height:80px">${this._esc(article.summary || '')}</textarea>
                </div>
                <div class="form-group">
                    <label>Noi dung (HTML)</label>
                    <textarea id="artContent" rows="15">${this._escTextarea(article.content || '')}</textarea>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">Luu bai viet</button>
                    <button type="button" class="btn btn-outline" onclick="app.renderAdminArticles()">Huy</button>
                </div>
            </form>`;
    },

    async saveArticle(e) {
        e.preventDefault();
        const doc = {
            title: document.getElementById('artTitle').value.trim(),
            author: document.getElementById('artAuthor').value.trim(),
            category_id: document.getElementById('artCategory').value,
            status: document.getElementById('artStatus').value,
            thumbnail: document.getElementById('artThumb').value.trim(),
            summary: document.getElementById('artSummary').value.trim(),
            content: document.getElementById('artContent').value,
            updated_at: new Date().toISOString()
        };

        if (!doc.title) {
            this.toast('Vui long nhap tieu de', 'error');
            return;
        }

        this.showLoading(true);
        try {
            if (this.editingArticle) {
                await API.updateArticle(this.editingArticle, doc);
                this.toast('Da cap nhat bai viet', 'success');
            } else {
                doc.created_at = new Date().toISOString();
                await API.insertArticle(doc);
                this.toast('Da tao bai viet moi', 'success');
            }
            await this.renderAdminArticles();
        } catch (e) {
            this.toast('Loi: ' + e.message, 'error');
        }
        this.showLoading(false);
    },

    async deleteArticleConfirm(id) {
        if (!confirm('Ban co chac muon xoa bai viet nay?')) return;
        this.showLoading(true);
        try {
            await API.deleteArticle(id);
            this.toast('Da xoa bai viet', 'success');
            await this.renderAdminArticles();
        } catch (e) {
            this.toast('Loi: ' + e.message, 'error');
        }
        this.showLoading(false);
    },

    // ----- Admin Categories -----
    async renderAdminCategories() {
        const content = document.getElementById('adminContent');
        content.innerHTML = '<div class="spinner" style="margin:40px auto"></div>';

        await this.loadCategories();

        if (this.categories.length === 0) {
            content.innerHTML = `
                <div class="admin-header">
                    <h2>Danh muc</h2>
                    <button class="btn btn-primary" onclick="app.showCategoryForm()">+ Tao danh muc</button>
                </div>
                <div class="empty-state">
                    <h3>Chua co danh muc</h3>
                    <p>Tao danh muc dau tien.</p>
                </div>`;
            return;
        }

        let rows = '';
        this.categories.forEach((c, i) => {
            rows += `<tr>
                <td class="td-title">${this._esc(c.name)}</td>
                <td class="td-truncate">${this._esc(c.description || '-')}</td>
                <td>${c.order || i}</td>
                <td>
                    <div class="table-actions">
                        <button class="btn btn-outline btn-sm" onclick="app.showCategoryForm('${c._id}')">Sua</button>
                        <button class="btn btn-danger btn-sm" onclick="app.deleteCategoryConfirm('${c._id}')">Xoa</button>
                    </div>
                </td>
            </tr>`;
        });

        content.innerHTML = `
            <div class="admin-header">
                <h2>Danh muc (${this.categories.length})</h2>
                <button class="btn btn-primary" onclick="app.showCategoryForm()">+ Tao danh muc</button>
            </div>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>Ten</th><th>Mo ta</th><th>Thu tu</th><th>Thao tac</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>`;
    },

    showCategoryForm(id) {
        const content = document.getElementById('adminContent');
        let cat = { name: '', description: '', order: 0 };

        if (id) {
            const found = this.categories.find(c => c._id === id);
            if (found) cat = found;
        }

        this.editingCategory = id || null;

        content.innerHTML = `
            <div class="admin-header">
                <h2>${id ? 'Sua danh muc' : 'Tao danh muc moi'}</h2>
            </div>
            <form onsubmit="app.saveCategory(event)">
                <div class="form-group">
                    <label>Ten danh muc *</label>
                    <input type="text" id="catName" value="${this._esc(cat.name)}" required>
                </div>
                <div class="form-group">
                    <label>Mo ta</label>
                    <textarea id="catDesc" rows="3" style="min-height:80px">${this._esc(cat.description || '')}</textarea>
                </div>
                <div class="form-group">
                    <label>Thu tu hien thi</label>
                    <input type="number" id="catOrder" value="${cat.order || 0}">
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">Luu</button>
                    <button type="button" class="btn btn-outline" onclick="app.renderAdminCategories()">Huy</button>
                </div>
            </form>`;
    },

    async saveCategory(e) {
        e.preventDefault();
        const doc = {
            name: document.getElementById('catName').value.trim(),
            description: document.getElementById('catDesc').value.trim(),
            order: parseInt(document.getElementById('catOrder').value) || 0
        };

        if (!doc.name) {
            this.toast('Vui long nhap ten danh muc', 'error');
            return;
        }

        this.showLoading(true);
        try {
            if (this.editingCategory) {
                await API.updateCategory(this.editingCategory, doc);
                this.toast('Da cap nhat danh muc', 'success');
            } else {
                await API.insertCategory(doc);
                this.toast('Da tao danh muc moi', 'success');
            }
            await this.loadCategories();
            await this.renderAdminCategories();
        } catch (e) {
            this.toast('Loi: ' + e.message, 'error');
        }
        this.showLoading(false);
    },

    async deleteCategoryConfirm(id) {
        if (!confirm('Ban co chac muon xoa danh muc nay? Cac bai viet thuoc danh muc se khong bi xoa.')) return;
        this.showLoading(true);
        try {
            await API.deleteCategory(id);
            this.toast('Da xoa danh muc', 'success');
            await this.loadCategories();
            await this.renderAdminCategories();
        } catch (e) {
            this.toast('Loi: ' + e.message, 'error');
        }
        this.showLoading(false);
    },

    // ----- Seed Data -----
    renderSeedPanel() {
        const content = document.getElementById('adminContent');
        content.innerHTML = `
            <div class="admin-header">
                <h2>Du lieu mau</h2>
            </div>
            <p style="margin-bottom:20px;color:var(--text-light)">Them du lieu mau de test ung dung. Thao tac nay se tao cac danh muc va bai viet mau.</p>
            <div style="display:flex;gap:12px;flex-wrap:wrap">
                <button class="btn btn-seed" onclick="app.seedData()">Tao du lieu mau</button>
                <button class="btn btn-danger" onclick="app.clearAllData()">Xoa toan bo du lieu</button>
            </div>
            <div id="seedLog" style="margin-top:24px;font-family:monospace;font-size:13px;color:var(--text-light);white-space:pre-wrap"></div>`;
    },

    async seedData() {
        const log = document.getElementById('seedLog');
        const addLog = (msg) => { log.textContent += msg + '\n'; };

        this.showLoading(true);
        addLog('Bat dau tao du lieu mau...');

        try {
            // Create categories
            const catData = [
                { name: 'Cong nghe', description: 'Tin tuc cong nghe moi nhat', order: 1 },
                { name: 'Kinh doanh', description: 'Tin tuc kinh doanh, tai chinh', order: 2 },
                { name: 'The thao', description: 'Tin tuc the thao trong va ngoai nuoc', order: 3 },
                { name: 'Giai tri', description: 'Tin tuc giai tri, showbiz', order: 4 },
                { name: 'Suc khoe', description: 'Tin tuc suc khoe, y te', order: 5 }
            ];

            const catIds = [];
            for (const cat of catData) {
                const res = await API.insertCategory(cat);
                catIds.push(res.inserted_id);
                addLog(`+ Tao danh muc: ${cat.name}`);
            }

            // Create articles
            const articles = [
                {
                    title: 'Trai nghiem moi cua AI trong nam 2026',
                    summary: 'Tri tue nhan tao dang thay doi cach chung ta lam viec va song. Nhung xu huong moi nhat trong AI se anh huong den moi linh vuc.',
                    content: '<p>Nam 2026 danh dau mot buoc ngoat lon trong linh vuc tri tue nhan tao. Cac mo hinh ngon ngu lon (LLM) da dat den trinh do moi, co kha nang xu ly cac tac vu phuc tap hon bao gio het.</p><h2>Xu huong noi bat</h2><p>Cac ung dung AI dang duoc tich hop sau hon vao cac cong cu hang ngay. Tu viec viet code, thiet ke, den quan ly du an, AI da tro thanh tro ly khong the thieu.</p><p>Mot trong nhung tien bo dang chu y nhat la kha nang hieu ngon ngu tu nhien da duoc cai thien dang ke. Cac chatbot va tro ly ao gio day co the hieu duoc ngu canh phuc tap va dua ra cau tra loi chinh xac hon.</p><h2>Anh huong den thi truong lao dong</h2><p>Theo du bao cua cac chuyen gia, AI se khong thay the con nguoi ma se tao ra nhung co hoi viec lam moi. Nhung nguoi biet su dung AI se co loi the canh tranh lon.</p>',
                    author: 'Nguyen Van A',
                    thumbnail: 'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&q=80',
                    category_id: catIds[0],
                    status: 'published',
                    created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString()
                },
                {
                    title: 'Thi truong chung khoan tang manh trong quy 1',
                    summary: 'VN-Index vuot moc 1500 diem, cac nha dau tu lac quan ve trien vong kinh te nam 2026.',
                    content: '<p>Thi truong chung khoan Viet Nam da co mot quy dau nam an tuong voi VN-Index tang hon 15% so voi cuoi nam truoc.</p><p>Theo cac chuyen gia phan tich, da tang nay duoc ho tro boi nhieu yeu to:</p><ul><li>Dong von dau tu nuoc ngoai tang tro lai</li><li>Chinh sach tien te noi long</li><li>Ket qua kinh doanh cua cac doanh nghiep niem yet kha quan</li></ul><p>Tuy nhien, cac nha dau tu can than trong vi thi truong co the co nhung phien dieu chinh trong ngan han.</p>',
                    author: 'Tran Thi B',
                    thumbnail: 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80',
                    category_id: catIds[1],
                    status: 'published',
                    created_at: new Date(Date.now() - 1000 * 60 * 60).toISOString()
                },
                {
                    title: 'Doi tuyen Viet Nam chuan bi cho vong loai World Cup',
                    summary: 'HLV truong cong bo danh sach 25 cau thu chuan bi cho tran dau quan trong sap toi.',
                    content: '<p>Doi tuyen bong da quoc gia Viet Nam da bat dau tap trung chuan bi cho tran dau vong loai World Cup 2026 khu vuc chau A.</p><h2>Danh sach tap trung</h2><p>HLV truong da trieu tap 25 cau thu, trong do co nhieu guong mat tre tai nang tu giai V-League. Day la tin hieu tich cuc cho su phat trien cua bong da Viet Nam.</p><p>Doi tuyen se co 2 tuan tap trung truoc khi buoc vao tran dau chinh thuc. Cac buoi tap se dien ra tai Trung tam huan luyen the thao quoc gia.</p>',
                    author: 'Le Van C',
                    thumbnail: 'https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?w=800&q=80',
                    category_id: catIds[2],
                    status: 'published',
                    created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString()
                },
                {
                    title: 'Bo phim Viet Nam moi lap ky luc phong ve',
                    summary: 'Phim dien anh Viet moi ra mat da thu ve hon 200 ty dong sau 2 tuan cong chieu.',
                    content: '<p>Bo phim dien anh Viet Nam moi nhat da tao nen con sot phong ve khi thu ve hon 200 ty dong chi sau 2 tuan cong chieu.</p><p>Day la mot dau hieu cho thay khan gia Viet Nam ngay cang yeu thich phim noi dia. Chat luong phim Viet da duoc cai thien dang ke trong nhung nam gan day.</p><blockquote>Chung toi rat vui vi khan gia da don nhan bo phim mot cach nong nhiet. Day la dong luc de chung toi tiep tuc lam phim chat luong - Dao dien chia se.</blockquote>',
                    author: 'Pham Thi D',
                    thumbnail: 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=800&q=80',
                    category_id: catIds[3],
                    status: 'published',
                    created_at: new Date(Date.now() - 1000 * 60 * 180).toISOString()
                },
                {
                    title: '5 thoi quen tot cho suc khoe moi ngay',
                    summary: 'Nhung thoi quen don gian nhung hieu qua de duy tri suc khoe tot trong cuoc song ban ron.',
                    content: '<p>Trong cuoc song hien dai ban ron, viec duy tri suc khoe la dieu vo cung quan trong. Duoi day la 5 thoi quen don gian ma ban co the ap dung moi ngay:</p><h2>1. Uong du nuoc</h2><p>Hay uong it nhat 2 lit nuoc moi ngay. Nuoc giup co the hoat dong tot hon va thuc day qua trinh trao doi chat.</p><h2>2. Tap the duc deu dan</h2><p>Chi can 30 phut van dong moi ngay da co the cai thien dang ke suc khoe tim mach va tinh than.</p><h2>3. Ngu du giac</h2><p>Ngu 7-8 tieng moi dem giup co the phuc hoi va tang cuong he mien dich.</p><h2>4. An nhieu rau xanh</h2><p>Rau xanh cung cap vitamin va khoang chat can thiet cho co the.</p><h2>5. Giam stress</h2><p>Thuc hanh thien, yoga hoac cac hoat dong thu gian de giam cang thang.</p>',
                    author: 'Bs. Hoang E',
                    thumbnail: 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&q=80',
                    category_id: catIds[4],
                    status: 'published',
                    created_at: new Date(Date.now() - 1000 * 60 * 240).toISOString()
                },
                {
                    title: 'Startup Viet Nam goi von thanh cong 50 trieu USD',
                    summary: 'Mot startup cong nghe Viet Nam vua hoan thanh vong goi von Series B voi 50 trieu USD tu cac quy dau tu quoc te.',
                    content: '<p>Startup cong nghe XYZ da hoan thanh vong goi von Series B voi tong gia tri 50 trieu USD. Day la mot trong nhung vong goi von lon nhat cua startup Viet Nam trong nam 2026.</p><p>Quy dau tu dan dau vong goi von nay la mot quy lon den tu Singapore, cung voi su tham gia cua nhieu nha dau tu tu Nhat Ban va Han Quoc.</p><h2>Ke hoach su dung von</h2><p>Theo CEO cua startup, so von se duoc su dung de:</p><ul><li>Mo rong thi truong sang Dong Nam A</li><li>Dau tu vao R&D</li><li>Tuyen dung nhan su chat luong cao</li></ul>',
                    author: 'Nguyen Van F',
                    thumbnail: 'https://images.unsplash.com/photo-1559136555-9303baea8ebd?w=800&q=80',
                    category_id: catIds[1],
                    status: 'published',
                    created_at: new Date(Date.now() - 1000 * 60 * 300).toISOString()
                },
                {
                    title: 'Apple ra mat dong san pham moi tai WWDC 2026',
                    summary: 'Apple gioi thieu nhieu san pham va tinh nang moi tai su kien WWDC 2026, tap trung vao AI va AR.',
                    content: '<p>Apple da to chuc su kien WWDC 2026 voi nhieu cong bo dang chu y. Trong do, hang cong nghe My tap trung manh vao tri tue nhan tao va thuc te tang cuong.</p><h2>Nhung diem noi bat</h2><p>iOS 20 voi tro ly AI thong minh hon, co kha nang hieu ngon ngu tu nhien tot hon. macOS moi voi giao dien duoc thiet ke lai hoan toan.</p><p>Ngoai ra, Apple con gioi thieu kinh AR the he moi voi thiet ke nho gon hon va pin lau hon, hua hen mang lai trai nghiem thuc te tang cuong tot nhat tren thi truong.</p>',
                    author: 'Tech Review',
                    thumbnail: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800&q=80',
                    category_id: catIds[0],
                    status: 'published',
                    created_at: new Date(Date.now() - 1000 * 60 * 360).toISOString()
                },
                {
                    title: 'Giai bong da V-League 2026 khoi tranh',
                    summary: 'Mua giai V-League 2026 chinh thuc bat dau voi nhieu doi bong da tang cuong luc luong.',
                    content: '<p>Giai vo dich bong da quoc gia V-League 2026 da chinh thuc khoi tranh voi su tham gia cua 14 doi bong. Mua giai nam nay hua hen se rat hap dan voi nhieu thay doi ve luat va format thi dau.</p><p>Nhieu doi bong da co nhung ban hop dong chat luong trong giai doan chuyen nhuong, hua hen se mang den nhung tran dau kich tinh cho nguoi ham mo.</p>',
                    author: 'Le Van G',
                    thumbnail: 'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=800&q=80',
                    category_id: catIds[2],
                    status: 'published',
                    created_at: new Date(Date.now() - 1000 * 60 * 420).toISOString()
                },
                {
                    title: 'Xu huong am nhac 2026: Nhac Viet len ngoi',
                    summary: 'Nhac Viet dang co su tro lai manh me tren cac nen tang nghe nhac truc tuyen.',
                    content: '<p>Nam 2026, nhac Viet dang trai qua giai doan phat trien manh me. Nhieu nghe si tre da tao nen nhung ban hit vuot qua hang tram trieu luot nghe tren cac nen tang nhac so.</p><p>Su phat trien cua MV chat luong cao va cac chien dich marketing sang tao da giup nhac Viet tiep can duoc nhieu doi tuong khan gia hon.</p>',
                    author: 'Music Critic',
                    thumbnail: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&q=80',
                    category_id: catIds[3],
                    status: 'published',
                    created_at: new Date(Date.now() - 1000 * 60 * 480).toISOString()
                },
                {
                    title: 'Nghien cuu moi ve loi ich cua giac ngu',
                    summary: 'Mot nghien cuu moi cho thay giac ngu co vai tro quan trong hon chung ta tuong trong viec phong ngua benh tat.',
                    content: '<p>Mot nghien cuu duoc cong bo tren tap chi khoa hoc hang dau da chi ra rang giac ngu co vai tro cuc ky quan trong trong viec duy tri suc khoe.</p><h2>Ket qua nghien cuu</h2><p>Nhung nguoi ngu du 7-9 tieng moi dem co:</p><ul><li>Nguy co mac benh tim mach giam 30%</li><li>He mien dich khoe manh hon 40%</li><li>Kha nang tap trung va sang tao tot hon</li></ul><p>Nghien cuu cung chi ra rang thieu ngu kinh nien co the dan den nhieu van de suc khoe nghiem trong.</p>',
                    author: 'Bs. Tran H',
                    thumbnail: 'https://images.unsplash.com/photo-1541781774459-bb2af2f05b55?w=800&q=80',
                    category_id: catIds[4],
                    status: 'published',
                    created_at: new Date(Date.now() - 1000 * 60 * 540).toISOString()
                }
            ];

            for (const art of articles) {
                await API.insertArticle(art);
                addLog(`+ Tao bai viet: ${art.title}`);
            }

            await this.loadCategories();
            addLog('\nHoan thanh! Da tao 5 danh muc va 10 bai viet mau.');
            this.toast('Da tao du lieu mau thanh cong!', 'success');

        } catch (e) {
            addLog('\nLoi: ' + e.message);
            this.toast('Loi khi tao du lieu mau: ' + e.message, 'error');
        }
        this.showLoading(false);
    },

    async clearAllData() {
        if (!confirm('Ban co chac muon xoa TOAN BO du lieu? Thao tac nay khong the hoan tac!')) return;

        this.showLoading(true);
        const log = document.getElementById('seedLog');
        const addLog = (msg) => { if (log) log.textContent += msg + '\n'; };

        try {
            // Delete all articles
            const artData = await API.getArticles({ query: {}, limit: 1000 });
            for (const a of (artData.documents || [])) {
                await API.deleteArticle(a._id);
                addLog(`- Xoa bai viet: ${a.title}`);
            }

            // Delete all categories
            for (const c of this.categories) {
                await API.deleteCategory(c._id);
                addLog(`- Xoa danh muc: ${c.name}`);
            }

            this.categories = [];
            this.renderCategoryNav();
            addLog('\nDa xoa toan bo du lieu.');
            this.toast('Da xoa toan bo du lieu', 'success');
        } catch (e) {
            addLog('\nLoi: ' + e.message);
            this.toast('Loi: ' + e.message, 'error');
        }
        this.showLoading(false);
    },

    // ===== Utilities =====
    _esc(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    _escTextarea(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    },

    _formatDate(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        const now = new Date();
        const diff = now - d;

        if (diff < 60000) return 'Vua xong';
        if (diff < 3600000) return Math.floor(diff / 60000) + ' phut truoc';
        if (diff < 86400000) return Math.floor(diff / 3600000) + ' gio truoc';
        if (diff < 604800000) return Math.floor(diff / 86400000) + ' ngay truoc';

        return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
    },

    showLoading(show) {
        document.getElementById('loadingOverlay').classList.toggle('show', show);
    },

    toast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = '.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
};

// Close modal with Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') app.closeArticle();
});

// Close modal by clicking overlay
document.getElementById('articleModal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) app.closeArticle();
});

// Start app
app.init();
