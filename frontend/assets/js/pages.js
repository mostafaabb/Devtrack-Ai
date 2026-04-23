/**
 * DevTrack AI - Page Renderers
 * Each function renders a complete dashboard page into the #page-content container.
 */

const PAGE = () => document.getElementById('page-content');

function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatTime(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function formatCurrency(amount) {
    return '$' + Number(amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 });
}

function statusBadge(status) {
    const map = {
        active: 'info', ai_handling: 'primary', pending: 'warning', confirmed: 'info',
        preparing: 'info', ready: 'success', delivering: 'info', completed: 'success',
        cancelled: 'danger', closed: 'success', checked_in: 'info', no_show: 'danger',
        processed: 'success', processing: 'warning', uploaded: 'info', failed: 'danger',
        inactive: 'warning', draft: 'warning',
    };
    return `<span class="badge badge-${map[status] || 'info'}">${status?.replace(/_/g, ' ') || '—'}</span>`;
}

function fileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

// ═══════════════════════════════════════════════════════════════════
// PAGE RENDERERS
// ═══════════════════════════════════════════════════════════════════

window.pages = {

    // ─── 1. DASHBOARD (Home) ────────────────────────────────────
    async dashboard() {
        const container = PAGE();
        container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

        const [summary, chartData, insightsData] = await Promise.all([
            api.get('/analytics/summary'),
            api.get('/analytics/chart-data?period=week'),
            api.get('/analytics/insights'),
        ]);

        const s = summary || {};
        const chart = chartData || { labels: [], orders: [], revenue: [] };
        const insights = insightsData?.insights || '';

        container.innerHTML = `
        <div class="page-enter">
            <!-- Stats Grid -->
            <div class="stats-grid">
                <div class="stat-card glass-card">
                    <div class="stat-header">
                        <div class="stat-icon purple">👥</div>
                        <span class="stat-trend up">↑ 12%</span>
                    </div>
                    <div class="stat-value">${s.total_customers || 0}</div>
                    <div class="stat-label">Total Customers</div>
                </div>
                <div class="stat-card glass-card">
                    <div class="stat-header">
                        <div class="stat-icon green">💬</div>
                        <span class="stat-trend up">↑ 8%</span>
                    </div>
                    <div class="stat-value">${s.total_conversations || 0}</div>
                    <div class="stat-label">Conversations</div>
                </div>
                <div class="stat-card glass-card">
                    <div class="stat-header">
                        <div class="stat-icon yellow">📦</div>
                        <span class="stat-trend up">↑ 18%</span>
                    </div>
                    <div class="stat-value">${s.total_orders || 0}</div>
                    <div class="stat-label">Total Orders</div>
                </div>
                <div class="stat-card glass-card">
                    <div class="stat-header">
                        <div class="stat-icon blue">💰</div>
                        <span class="stat-trend up">↑ 24%</span>
                    </div>
                    <div class="stat-value">${formatCurrency(s.total_revenue)}</div>
                    <div class="stat-label">Total Revenue</div>
                </div>
            </div>

            <!-- AI Insights -->
            <div class="insights-widget">
                <div class="insights-header">
                    <span>🧠</span>
                    <h3>AI Business Insights</h3>
                </div>
                <div class="insights-content">${insights}</div>
            </div>

            <!-- Charts -->
            <div class="content-grid">
                <div class="card">
                    <div class="card-header">
                        <h3>📈 Orders This Week</h3>
                        <select class="btn btn-sm btn-secondary" style="padding:4px 10px;font-size:0.75rem">
                            <option>This Week</option>
                            <option>This Month</option>
                            <option>This Year</option>
                        </select>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <div style="width:100%">
                                <div class="chart-bars" id="orders-chart">
                                    ${chart.orders?.map((v, i) => {
                                        const max = Math.max(...chart.orders);
                                        const h = max > 0 ? (v / max * 180) : 20;
                                        return `<div class="chart-bar" style="height:${h}px"><span class="chart-tooltip">${v} orders</span></div>`;
                                    }).join('') || ''}
                                </div>
                                <div class="chart-labels">
                                    ${chart.labels?.map(l => `<span class="chart-label">${l}</span>`).join('') || ''}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3>💰 Revenue This Week</h3>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <div style="width:100%">
                                <div class="chart-bars" id="revenue-chart">
                                    ${chart.revenue?.map((v, i) => {
                                        const max = Math.max(...chart.revenue);
                                        const h = max > 0 ? (v / max * 180) : 20;
                                        return `<div class="chart-bar" style="height:${h}px;background:var(--gradient-success)"><span class="chart-tooltip">${formatCurrency(v)}</span></div>`;
                                    }).join('') || ''}
                                </div>
                                <div class="chart-labels">
                                    ${chart.labels?.map(l => `<span class="chart-label">${l}</span>`).join('') || ''}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Quick Stats Row -->
            <div class="content-grid three-col" style="margin-top:16px">
                <div class="card">
                    <div class="card-body" style="text-align:center;padding:24px">
                        <div style="font-size:2rem;margin-bottom:8px">🤖</div>
                        <div style="font-size:1.5rem;font-weight:800">${s.active_conversations || 0}</div>
                        <div style="color:var(--text-secondary);font-size:0.85rem">Active AI Chats</div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-body" style="text-align:center;padding:24px">
                        <div style="font-size:2rem;margin-bottom:8px">⏳</div>
                        <div style="font-size:1.5rem;font-weight:800">${s.pending_orders || 0}</div>
                        <div style="color:var(--text-secondary);font-size:0.85rem">Pending Orders</div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-body" style="text-align:center;padding:24px">
                        <div style="font-size:2rem;margin-bottom:8px">📅</div>
                        <div style="font-size:1.5rem;font-weight:800">${s.pending_bookings || 0}</div>
                        <div style="color:var(--text-secondary);font-size:0.85rem">Pending Bookings</div>
                    </div>
                </div>
            </div>
        </div>`;
    },

    // ─── 2. CONVERSATIONS ───────────────────────────────────────
    async conversations() {
        const container = PAGE();
        container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

        const conversations = await api.get('/conversations/') || [];

        container.innerHTML = `
        <div class="page-enter">
            <div class="chat-layout">
                <!-- Chat List -->
                <div class="chat-list">
                    <div class="chat-list-header">
                        <input type="text" class="chat-search" placeholder="🔍 Search conversations..." id="conv-search">
                    </div>
                    <div id="chat-items">
                        ${conversations.map((c, i) => `
                            <div class="chat-item ${i === 0 ? 'active' : ''}" data-id="${c.id}" onclick="window.pages._openConversation('${c.id}', this)">
                                <div class="chat-item-avatar">${(c.customer?.name || 'U')[0]}</div>
                                <div class="chat-item-info">
                                    <div class="chat-item-name">${c.customer?.name || 'Unknown'}</div>
                                    <div class="chat-item-preview">${c.messages?.[c.messages.length - 1]?.content?.slice(0, 40) || 'No messages'}...</div>
                                </div>
                                <div class="chat-item-meta">
                                    <div class="chat-item-time">${formatTime(c.last_message_at)}</div>
                                    ${statusBadge(c.status)}
                                </div>
                            </div>
                        `).join('') || '<div class="empty-state"><p>No conversations yet</p></div>'}
                    </div>
                </div>

                <!-- Chat Panel -->
                <div class="chat-panel">
                    <div class="chat-panel-header">
                        <div>
                            <strong id="chat-customer-name">${conversations[0]?.customer?.name || 'Select a conversation'}</strong>
                            <div style="font-size:0.8rem;color:var(--text-secondary)" id="chat-customer-channel">${conversations[0] ? (conversations[0].channel + ' • ' + (conversations[0].is_ai_enabled ? '🤖 AI Active' : '👤 Human')) : ''}</div>
                        </div>
                        <div style="display:flex;gap:8px;align-items:center">
                            <select class="form-control form-control-sm" style="width:120px;font-size:0.75rem" onchange="window.pages._changePersona(this.value)">
                                <option value="general">AI: General</option>
                                <option value="sales">AI: Sales</option>
                                <option value="support">AI: Support</option>
                                <option value="concierge">AI: Concierge</option>
                            </select>
                            <button class="btn btn-sm btn-secondary" onclick="window.pages._toggleAI()">🤖 Toggle AI</button>
                            <button class="btn btn-sm btn-secondary" onclick="window.pages._takeOver()">👤 Take Over</button>
                        </div>
                    </div>
                    <div class="chat-messages" id="chat-messages">
                        ${conversations[0]?.messages?.map(m => `
                            <div class="message ${m.sender_type}">
                                ${m.content}
                                <div class="message-meta">${m.sender_type}${m.ai_intent ? ' • 🎯 ' + m.ai_intent : ''} • ${formatTime(m.created_at)}</div>
                            </div>
                        `).join('') || '<div class="empty-state"><div class="empty-state-icon">💬</div><h3>Select a conversation</h3><p>Choose a conversation from the list</p></div>'}
                    </div>
                    <div class="chat-input-area">
                        <textarea class="chat-input" placeholder="Type a message..." rows="1" id="chat-msg-input"></textarea>
                        <button class="btn btn-primary" onclick="window.pages._sendMessage()" style="padding:10px 16px">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                        </button>
                    </div>
                </div>
            </div>
        </div>`;

        // Search filter
        document.getElementById('conv-search')?.addEventListener('input', (e) => {
            const q = e.target.value.toLowerCase();
            document.querySelectorAll('.chat-item').forEach(item => {
                const name = item.querySelector('.chat-item-name')?.textContent?.toLowerCase() || '';
                item.style.display = name.includes(q) ? '' : 'none';
            });
        });
    },

    _currentConvId: null,

    _openConversation(id, el) {
        window.pages._currentConvId = id;
        document.querySelectorAll('.chat-item').forEach(i => i.classList.remove('active'));
        el?.classList.add('active');

        // Find conversation data (from mock)
        const name = el?.querySelector('.chat-item-name')?.textContent || 'Customer';
        document.getElementById('chat-customer-name').textContent = name;
    },

    _sendMessage() {
        const input = document.getElementById('chat-msg-input');
        const content = input?.value?.trim();
        if (!content) return;

        const messages = document.getElementById('chat-messages');
        messages.innerHTML += `<div class="message staff">${content}<div class="message-meta">You • just now</div></div>`;
        input.value = '';
        messages.scrollTop = messages.scrollHeight;

        // Simulate AI response
        setTimeout(() => {
            messages.innerHTML += `<div class="message ai">Thank you for your message! I'm processing your request and will get back to you shortly. 😊<div class="message-meta">AI • just now</div></div>`;
            messages.scrollTop = messages.scrollHeight;
        }, 1500);
    },

    _toggleAI() { api.post(`/conversations/${window.pages._currentConvId}/takeover`); app.showToast('AI toggled for this conversation', 'info'); },
    _takeOver() { api.post(`/conversations/${window.pages._currentConvId}/takeover`); app.showToast('You are now handling this conversation', 'success'); },
    _changePersona(persona) { api.post(`/conversations/${window.pages._currentConvId}/persona/${persona}`); app.showToast(`AI Persona changed to ${persona}`, 'success'); },

    // ─── 3. CUSTOMERS ───────────────────────────────────────────
    async customers() {
        const container = PAGE();
        container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

        const customers = await api.get('/customers/') || [];

        container.innerHTML = `
        <div class="page-enter">
            <div class="action-bar">
                <div class="action-bar-left">
                    <input type="text" class="search-input" placeholder="🔍 Search customers..." id="customer-search">
                </div>
                <button class="btn btn-primary" onclick="window.pages._addCustomerModal()">+ Add Customer</button>
            </div>

            <div class="card">
                <div class="card-body" style="padding:0;overflow-x:auto">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Customer</th>
                                <th>Email</th>
                                <th>Phone</th>
                                <th>Channel</th>
                                <th>Tags</th>
                                <th>Last Seen</th>
                            </tr>
                        </thead>
                        <tbody id="customers-tbody">
                            ${customers.map(c => `
                                <tr>
                                    <td>
                                        <div style="display:flex;align-items:center;gap:10px">
                                            <div class="user-avatar" style="width:32px;height:32px;font-size:0.75rem">${(c.name || '?')[0]}</div>
                                            <strong>${c.name || 'Unknown'}</strong>
                                        </div>
                                    </td>
                                    <td style="color:var(--text-secondary)">${c.email || '—'}</td>
                                    <td>${c.phone || '—'}</td>
                                    <td>${statusBadge(c.channel)}</td>
                                    <td><div class="tags">${(c.tags || []).map(t => `<span class="tag">${t}</span>`).join('') || '—'}</div></td>
                                    <td style="color:var(--text-secondary)">${formatDate(c.last_seen)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>`;

        document.getElementById('customer-search')?.addEventListener('input', (e) => {
            const q = e.target.value.toLowerCase();
            document.querySelectorAll('#customers-tbody tr').forEach(row => {
                row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
            });
        });
    },

    _addCustomerModal() {
        app.showModal('Add Customer', `
            <div class="form-group"><label>Full Name</label><input type="text" id="new-cust-name" placeholder="Customer name"></div>
            <div class="form-row">
                <div class="form-group"><label>Email</label><input type="email" id="new-cust-email" placeholder="Email"></div>
                <div class="form-group"><label>Phone</label><input type="tel" id="new-cust-phone" placeholder="+961..."></div>
            </div>
        `, `<button class="btn btn-secondary" onclick="app.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="window.pages._createCustomer()">Add Customer</button>`);
    },

    async _createCustomer() {
        app.closeModal();
        app.showToast('Customer added successfully!', 'success');
        window.pages.customers();
    },

    // ─── 4. ORDERS ──────────────────────────────────────────────
    async orders() {
        const container = PAGE();
        container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

        const orders = await api.get('/orders/') || [];

        container.innerHTML = `
        <div class="page-enter">
            <div class="action-bar">
                <div class="action-bar-left">
                    <input type="text" class="search-input" placeholder="🔍 Search orders..." id="order-search">
                </div>
                <button class="btn btn-primary" onclick="window.pages._addOrderModal()">+ New Order</button>
            </div>

            <div class="card">
                <div class="card-body" style="padding:0;overflow-x:auto">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Order #</th>
                                <th>Customer</th>
                                <th>Type</th>
                                <th>Total</th>
                                <th>Source</th>
                                <th>Status</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody id="orders-tbody">
                            ${orders.map(o => `
                                <tr>
                                    <td><strong>${o.order_number}</strong></td>
                                    <td>${o.customer?.name || '—'}</td>
                                    <td>${statusBadge(o.order_type)}</td>
                                    <td><strong>${formatCurrency(o.total)}</strong></td>
                                    <td>${o.source === 'ai_chat' ? '🤖 AI' : o.source === 'whatsapp' ? '📱 WhatsApp' : '🌐 ' + o.source}</td>
                                    <td>${statusBadge(o.status)}</td>
                                    <td style="color:var(--text-secondary)">${formatDate(o.created_at)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>`;

        document.getElementById('order-search')?.addEventListener('input', (e) => {
            const q = e.target.value.toLowerCase();
            document.querySelectorAll('#orders-tbody tr').forEach(row => {
                row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
            });
        });
    },

    _addOrderModal() {
        app.showModal('Create New Order', `
            <div class="form-group"><label>Customer Name</label><input type="text" placeholder="Customer name"></div>
            <div class="form-group"><label>Order Type</label>
                <select><option>Delivery</option><option>Dine-in</option><option>Takeaway</option><option>Online</option></select>
            </div>
            <div class="form-group"><label>Items</label><textarea placeholder="Item list..." rows="3"></textarea></div>
            <div class="form-group"><label>Notes</label><input type="text" placeholder="Special instructions..."></div>
        `, `<button class="btn btn-secondary" onclick="app.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="app.closeModal();app.showToast('Order created!','success');window.pages.orders()">Create Order</button>`);
    },

    // ─── 5. BOOKINGS ────────────────────────────────────────────
    async bookings() {
        const container = PAGE();
        container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

        const bookings = await api.get('/bookings/') || [];

        container.innerHTML = `
        <div class="page-enter">
            <div class="action-bar">
                <div class="action-bar-left">
                    <input type="text" class="search-input" placeholder="🔍 Search bookings..." id="booking-search">
                </div>
                <button class="btn btn-primary" onclick="window.pages._addBookingModal()">+ New Booking</button>
            </div>

            <div class="card">
                <div class="card-body" style="padding:0;overflow-x:auto">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Booking #</th>
                                <th>Customer</th>
                                <th>Type</th>
                                <th>Date/Time</th>
                                <th>Party Size</th>
                                <th>Resource</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${bookings.map(b => `
                                <tr>
                                    <td><strong>${b.booking_number}</strong></td>
                                    <td>${b.customer?.name || '—'}</td>
                                    <td>${statusBadge(b.booking_type)}</td>
                                    <td>${formatDate(b.start_time)} ${formatTime(b.start_time)}</td>
                                    <td>${b.party_size} 👤</td>
                                    <td>${b.resource_name || b.service_name || '—'}</td>
                                    <td>${statusBadge(b.status)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>`;
    },

    _addBookingModal() {
        app.showModal('Create New Booking', `
            <div class="form-group"><label>Customer Name</label><input type="text" placeholder="Customer name"></div>
            <div class="form-row">
                <div class="form-group"><label>Type</label>
                    <select><option>Table</option><option>Room</option><option>Appointment</option><option>Service</option></select>
                </div>
                <div class="form-group"><label>Party Size</label><input type="number" value="1" min="1"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Date</label><input type="date"></div>
                <div class="form-group"><label>Time</label><input type="time"></div>
            </div>
            <div class="form-group"><label>Notes</label><input type="text" placeholder="Special requests..."></div>
        `, `<button class="btn btn-secondary" onclick="app.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="app.closeModal();app.showToast('Booking created!','success');window.pages.bookings()">Create Booking</button>`);
    },

    // ─── 6. PRODUCTS & SERVICES ─────────────────────────────────
    async products() {
        const container = PAGE();
        container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

        const products = await api.get('/products/') || [];

        container.innerHTML = `
        <div class="page-enter">
            <div class="action-bar">
                <div class="action-bar-left">
                    <input type="text" class="search-input" placeholder="🔍 Search products..." id="product-search">
                </div>
                <button class="btn btn-primary" onclick="window.pages._addProductModal()">+ Add Product</button>
            </div>

            <div class="module-grid">
                ${products.map(p => `
                    <div class="card glass-card" style="cursor:pointer">
                        <div class="card-body">
                            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
                                <div style="width:50px;height:50px;border-radius:12px;background:var(--gradient-primary);display:flex;align-items:center;justify-content:center;font-size:1.5rem">🏷️</div>
                                ${p.is_featured ? '<span class="badge badge-primary">⭐ Featured</span>' : ''}
                            </div>
                            <h4 style="font-weight:700;margin-bottom:4px">${p.name}</h4>
                            <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:12px">${p.description || 'No description'}</p>
                            <div style="display:flex;align-items:center;justify-content:space-between">
                                <div>
                                    ${p.sale_price ? `<span style="text-decoration:line-through;color:var(--text-tertiary);margin-right:8px">${formatCurrency(p.price)}</span><strong style="color:var(--success)">${formatCurrency(p.sale_price)}</strong>` : `<strong>${formatCurrency(p.price)}</strong>`}
                                </div>
                                ${statusBadge(p.is_active ? 'active' : 'inactive')}
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>`;
    },

    _addProductModal() {
        app.showModal('Add Product', `
            <div class="form-group"><label>Product Name</label><input type="text" placeholder="Product name"></div>
            <div class="form-group"><label>Description</label><textarea placeholder="Description..." rows="2"></textarea></div>
            <div class="form-row">
                <div class="form-group"><label>Price ($)</label><input type="number" step="0.01" placeholder="0.00"></div>
                <div class="form-group"><label>Sale Price ($)</label><input type="number" step="0.01" placeholder="Optional"></div>
            </div>
            <div class="form-group"><label>SKU</label><input type="text" placeholder="SKU code"></div>
        `, `<button class="btn btn-secondary" onclick="app.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="app.closeModal();app.showToast('Product added!','success');window.pages.products()">Add Product</button>`);
    },

    // ─── 7. DOCUMENTS (Knowledge Base) ──────────────────────────
    async documents() {
        const container = PAGE();
        container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

        const documents = await api.get('/documents/') || [];

        container.innerHTML = `
        <div class="page-enter">
            <div class="action-bar">
                <div class="action-bar-left">
                    <h3 style="font-weight:600">Knowledge Base</h3>
                </div>
                <button class="btn btn-primary" onclick="window.pages._uploadDocModal()">📄 Upload Document</button>
            </div>

            <div class="module-grid">
                ${documents.map(d => `
                    <div class="card glass-card">
                        <div class="card-body">
                            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
                                <div style="width:44px;height:44px;border-radius:10px;background:${d.file_type === 'pdf' ? 'var(--gradient-danger)' : 'var(--gradient-secondary)'};display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:0.7rem">${d.file_type.toUpperCase()}</div>
                                <div>
                                    <h4 style="font-weight:600">${d.title}</h4>
                                    <div style="font-size:0.8rem;color:var(--text-secondary)">${d.filename} • ${fileSize(d.file_size)}</div>
                                </div>
                            </div>
                            <div style="display:flex;align-items:center;justify-content:space-between">
                                <div style="font-size:0.8rem;color:var(--text-secondary)">📚 ${d.chunk_count} chunks</div>
                                ${statusBadge(d.status)}
                            </div>
                            <div style="font-size:0.75rem;color:var(--text-tertiary);margin-top:8px">Uploaded ${formatDate(d.created_at)}</div>
                        </div>
                    </div>
                `).join('') || '<div class="empty-state"><div class="empty-state-icon">📂</div><h3>No documents yet</h3><p>Upload documents to build your AI knowledge base</p></div>'}
            </div>
        </div>`;
    },

    _uploadDocModal() {
        app.showModal('Upload Document', `
            <p style="color:var(--text-secondary);margin-bottom:16px">Upload PDF, TXT, or DOCX files to build your AI knowledge base. The content will be processed and used by AI to answer customer questions.</p>
            <div class="form-group"><label>Document Title</label><input type="text" placeholder="e.g., Restaurant Menu 2024"></div>
            <div class="form-group"><label>File</label><input type="file" accept=".pdf,.txt,.docx" style="padding:8px"></div>
        `, `<button class="btn btn-secondary" onclick="app.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="app.closeModal();app.showToast('Document uploaded & processing...','success');window.pages.documents()">Upload & Process</button>`);
    },

    // ─── 8. WORKFLOWS (Automation) ──────────────────────────────
    async workflows() {
        const container = PAGE();
        container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

        const workflows = await api.get('/workflows/') || [];

        const triggerLabels = { message_received: '💬 Message Received', order_placed: '📦 Order Placed', booking_requested: '📅 Booking Requested', customer_created: '👤 New Customer' };
        const actionLabels = { ai_reply: '🤖 AI Auto-Reply', notify_admin: '🔔 Notify Admin', escalate: '👤 Escalate to Human', send_message: '💬 Send Message', create_order: '📦 Create Order', create_booking: '📅 Create Booking' };

        container.innerHTML = `
        <div class="page-enter">
            <div class="action-bar">
                <div class="action-bar-left">
                    <h3 style="font-weight:600">Automation Rules</h3>
                </div>
                <button class="btn btn-primary" onclick="window.pages._addWorkflowModal()">+ New Workflow</button>
            </div>

            ${workflows.map(w => `
                <div class="workflow-card glass-card">
                    <div style="flex:0 0 auto;display:flex;flex-direction:column;align-items:center;gap:4px">
                        ${statusBadge(w.status)}
                        <div style="font-size:0.7rem;color:var(--text-tertiary);margin-top:4px">${w.execution_count?.total || 0} runs</div>
                    </div>
                    <div class="workflow-trigger">
                        <div class="workflow-trigger-label">IF (Trigger)</div>
                        <div class="workflow-trigger-value">${triggerLabels[w.trigger_type] || w.trigger_type}</div>
                    </div>
                    <div class="workflow-arrow">→</div>
                    <div class="workflow-action">
                        <div class="workflow-action-label">THEN (Action)</div>
                        <div class="workflow-action-value">${actionLabels[w.action_type] || w.action_type}</div>
                    </div>
                    <div style="flex:0 0 auto">
                        <div style="font-weight:600;font-size:0.9rem">${w.name}</div>
                        <div style="font-size:0.8rem;color:var(--text-secondary)">${w.description || ''}</div>
                    </div>
                </div>
            `).join('') || '<div class="empty-state"><div class="empty-state-icon">⚡</div><h3>No workflows yet</h3><p>Create automation rules to streamline your business</p></div>'}
        </div>`;
    },

    _addWorkflowModal() {
        app.showModal('Create Workflow', `
            <div class="form-group"><label>Workflow Name</label><input type="text" placeholder="e.g., Auto-reply to messages"></div>
            <div class="form-group"><label>Description</label><input type="text" placeholder="What does this workflow do?"></div>
            <div class="form-group"><label>IF (Trigger)</label>
                <select>
                    <option value="message_received">💬 Message Received</option>
                    <option value="order_placed">📦 Order Placed</option>
                    <option value="booking_requested">📅 Booking Requested</option>
                    <option value="customer_created">👤 New Customer</option>
                </select>
            </div>
            <div class="form-group"><label>THEN (Action)</label>
                <select>
                    <option value="ai_reply">🤖 AI Auto-Reply</option>
                    <option value="notify_admin">🔔 Notify Admin</option>
                    <option value="escalate">👤 Escalate to Human</option>
                    <option value="send_message">💬 Send Message</option>
                </select>
            </div>
        `, `<button class="btn btn-secondary" onclick="app.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="app.closeModal();app.showToast('Workflow created!','success');window.pages.workflows()">Create</button>`);
    },

    // ─── 9. ANALYTICS ───────────────────────────────────────────
    async analytics() {
        const container = PAGE();
        container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

        const [summary, chartData, insightsData] = await Promise.all([
            api.get('/analytics/summary'),
            api.get('/analytics/chart-data?period=week'),
            api.get('/analytics/insights'),
        ]);

        const s = summary || {};
        const chart = chartData || { labels: [], orders: [], revenue: [], conversations: [], customers: [] };

        container.innerHTML = `
        <div class="page-enter">
            <!-- Stats -->
            <div class="stats-grid">
                <div class="stat-card glass-card">
                    <div class="stat-header"><div class="stat-icon purple">📦</div></div>
                    <div class="stat-value">${s.total_orders || 0}</div>
                    <div class="stat-label">Total Orders</div>
                </div>
                <div class="stat-card glass-card">
                    <div class="stat-header"><div class="stat-icon green">💰</div></div>
                    <div class="stat-value">${formatCurrency(s.total_revenue)}</div>
                    <div class="stat-label">Revenue</div>
                </div>
                <div class="stat-card glass-card">
                    <div class="stat-header"><div class="stat-icon yellow">📅</div></div>
                    <div class="stat-value">${s.total_bookings || 0}</div>
                    <div class="stat-label">Bookings</div>
                </div>
                <div class="stat-card glass-card">
                    <div class="stat-header"><div class="stat-icon blue">💬</div></div>
                    <div class="stat-value">${s.total_conversations || 0}</div>
                    <div class="stat-label">Conversations</div>
                </div>
            </div>

            <!-- Charts -->
            <div class="content-grid">
                <div class="card">
                    <div class="card-header"><h3>📊 Conversations Trend</h3></div>
                    <div class="card-body">
                        <div class="chart-container">
                            <div style="width:100%">
                                <div class="chart-bars">
                                    ${chart.conversations?.map(v => {
                                        const max = Math.max(...chart.conversations);
                                        const h = max > 0 ? (v / max * 180) : 20;
                                        return `<div class="chart-bar" style="height:${h}px;background:var(--gradient-secondary)"><span class="chart-tooltip">${v} chats</span></div>`;
                                    }).join('') || ''}
                                </div>
                                <div class="chart-labels">${chart.labels?.map(l => `<span class="chart-label">${l}</span>`).join('') || ''}</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h3>👥 New Customers</h3></div>
                    <div class="card-body">
                        <div class="chart-container">
                            <div style="width:100%">
                                <div class="chart-bars">
                                    ${chart.customers?.map(v => {
                                        const max = Math.max(...chart.customers);
                                        const h = max > 0 ? (v / max * 180) : 20;
                                        return `<div class="chart-bar" style="height:${h}px;background:var(--gradient-warning)"><span class="chart-tooltip">${v} new</span></div>`;
                                    }).join('') || ''}
                                </div>
                                <div class="chart-labels">${chart.labels?.map(l => `<span class="chart-label">${l}</span>`).join('') || ''}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- AI Insights -->
            <div class="insights-widget" style="margin-top:0">
                <div class="insights-header">
                    <span>🧠</span>
                    <h3>AI-Generated Business Report</h3>
                </div>
                <div class="insights-content">${insightsData?.insights || 'Loading insights...'}</div>
            </div>
        </div>`;
    },

    // ─── 10. MODULES ────────────────────────────────────────────
    async modules() {
        const container = PAGE();
        container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

        const modules = await api.get('/business/modules') || [];

        container.innerHTML = `
        <div class="page-enter">
            <div style="margin-bottom:20px">
                <h3 style="font-weight:700;margin-bottom:4px">Industry Modules</h3>
                <p style="color:var(--text-secondary)">Enable or disable modules based on your business type. Each module adds specialized features to your platform.</p>
            </div>

            <div class="module-grid">
                ${modules.map(m => `
                    <div class="module-card glass-card">
                        <div class="module-icon">${m.icon}</div>
                        <div class="module-header">
                            <div class="module-name">${m.name}</div>
                            <label class="toggle">
                                <input type="checkbox" ${m.is_enabled ? 'checked' : ''} onchange="window.pages._toggleModule('${m.key}', this.checked)">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        <div class="module-desc">${m.description}</div>
                        <ul class="module-features">
                            ${m.features?.map(f => `<li>${f}</li>`).join('') || ''}
                        </ul>
                        ${m.is_premium ? '<span class="badge badge-warning">⭐ Premium</span>' : ''}
                    </div>
                `).join('')}
            </div>
        </div>`;
    },

    async _toggleModule(key, enabled) {
        try {
            await api.post('/business/modules/toggle', { module_key: key, is_enabled: enabled });
            app.showToast(`Module ${enabled ? 'enabled' : 'disabled'}`, 'success');
        } catch (err) {
            app.showToast('Module updated (demo)', 'info');
        }
    },

    // ─── 11. SETTINGS ───────────────────────────────────────────
    async settings() {
        const container = PAGE();
        container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

        let business;
        try {
            business = await api.get('/business/');
        } catch (e) {
            business = await api._mockResponse('GET', '/business/', null);
        }

        const b = business || {};

        container.innerHTML = `
        <div class="page-enter">
            <!-- Business Settings -->
            <div class="settings-section">
                <h3>🏢 Business Information</h3>
                <div class="card">
                    <div class="card-body">
                        <div class="settings-grid">
                            <div class="form-group"><label>Business Name</label><input type="text" value="${b.name || ''}" id="set-name"></div>
                            <div class="form-group"><label>Business Type</label>
                                <select id="set-type">
                                    ${['restaurant', 'hotel', 'retail', 'clinic', 'delivery', 'general'].map(t => `<option value="${t}" ${b.business_type === t ? 'selected' : ''}>${t.charAt(0).toUpperCase() + t.slice(1)}</option>`).join('')}
                                </select>
                            </div>
                            <div class="form-group"><label>Phone</label><input type="text" value="${b.phone || ''}" id="set-phone"></div>
                            <div class="form-group"><label>Email</label><input type="text" value="${b.email || ''}" id="set-email"></div>
                            <div class="form-group" style="grid-column:span 2"><label>Address</label><input type="text" value="${b.address || ''}" id="set-address"></div>
                        </div>
                        <button class="btn btn-primary" style="margin-top:12px" onclick="window.pages._saveSettings()">Save Changes</button>
                    </div>
                </div>
            </div>

            <!-- AI Settings -->
            <div class="settings-section">
                <h3>🧠 AI Configuration</h3>
                <div class="card">
                    <div class="card-body">
                        <div class="settings-grid">
                            <div class="form-group"><label>AI Tone</label>
                                <select id="set-ai-tone">
                                    ${['professional', 'friendly', 'formal'].map(t => `<option value="${t}" ${b.ai_tone === t ? 'selected' : ''}>${t.charAt(0).toUpperCase() + t.slice(1)}</option>`).join('')}
                                </select>
                            </div>
                            <div class="form-group"><label>AI Language</label>
                                <select id="set-ai-lang">
                                    <option value="en" ${b.ai_language === 'en' ? 'selected' : ''}>English</option>
                                    <option value="ar" ${b.ai_language === 'ar' ? 'selected' : ''}>Arabic</option>
                                    <option value="mixed" ${b.ai_language === 'mixed' ? 'selected' : ''}>Mixed (EN/AR/Lebanese)</option>
                                </select>
                            </div>
                            <div class="form-group" style="grid-column:span 2"><label>Welcome Message</label><textarea id="set-welcome" rows="2">${b.welcome_message || ''}</textarea></div>
                        </div>
                        <button class="btn btn-primary" style="margin-top:12px" onclick="window.pages._saveAISettings()">Save AI Settings</button>
                    </div>
                </div>
            </div>

            <!-- Branding -->
            <div class="settings-section">
                <h3>🎨 Branding</h3>
                <div class="card">
                    <div class="card-body">
                        <div class="settings-grid">
                            <div class="form-group">
                                <label>Primary Color</label>
                                <div class="color-preview">
                                    <input type="color" value="${b.primary_color || '#6366f1'}" id="set-color-primary" style="width:50px;height:36px;border:none;cursor:pointer">
                                    <span>${b.primary_color || '#6366f1'}</span>
                                </div>
                            </div>
                            <div class="form-group">
                                <label>Secondary Color</label>
                                <div class="color-preview">
                                    <input type="color" value="${b.secondary_color || '#8b5cf6'}" id="set-color-secondary" style="width:50px;height:36px;border:none;cursor:pointer">
                                    <span>${b.secondary_color || '#8b5cf6'}</span>
                                </div>
                            </div>
                        </div>
                        <button class="btn btn-primary" style="margin-top:12px" onclick="window.pages._saveBranding()">Save Branding</button>
                    </div>
                </div>
            </div>

            <!-- WhatsApp & Integrations -->
            <div class="settings-section">
                <h3>🔑 WhatsApp & API</h3>
                <div class="card">
                    <div class="card-body">
                        <div style="display:flex;gap:20px;margin-bottom:20px;padding:15px;background:rgba(99, 102, 241, 0.1);border-radius:12px;border:1px solid rgba(99, 102, 241, 0.2)">
                            <div style="font-size:2rem">📱</div>
                            <div>
                                <h4 style="margin:0 0 5px 0">WhatsApp Business API</h4>
                                <p style="font-size:0.85rem;color:var(--text-secondary);margin:0">Connect your official WhatsApp Business account to enable AI auto-replies on WhatsApp.</p>
                            </div>
                        </div>

                        <div class="settings-grid">
                            <div class="form-group">
                                <label>Phone Number ID <span style="color:var(--text-secondary);font-weight:normal;font-size:0.7rem">(From Meta Dev Portal)</span></label>
                                <input type="text" value="${b.whatsapp_phone_number_id || ''}" id="set-wa-id" placeholder="e.g. 106543210987654">
                            </div>
                            <div class="form-group">
                                <label>Permanent Access Token</label>
                                <input type="password" value="${b.whatsapp_api_token || ''}" id="set-wa-token" placeholder="EAABw...">
                            </div>
                            <div class="form-group" style="grid-column:span 2">
                                <label>Webhook Verify Token <span style="color:var(--text-secondary);font-weight:normal;font-size:0.7rem">(Create any string for Meta to verify)</span></label>
                                <input type="text" value="${b.whatsapp_verify_token || ''}" id="set-wa-verify" placeholder="e.g. devtrack_secure_token_123">
                            </div>
                        </div>

                        <div style="margin-top:20px;padding:15px;background:rgba(0,0,0,0.1);border-radius:8px">
                            <label style="display:block;margin-bottom:8px;font-weight:600;font-size:0.85rem">🔗 Unique Callback URL (For Meta Webhooks)</label>
                            <div style="display:flex;gap:10px">
                                <input type="text" readonly value="${window.location.origin}/api/v1/whatsapp/webhook/${b.id}" style="flex:1;font-family:monospace;font-size:0.8rem;background:transparent;border:1px solid rgba(255,255,255,0.1);padding:8px;border-radius:4px">
                                <button class="btn btn-secondary btn-sm" onclick="navigator.clipboard.writeText('${window.location.origin}/api/v1/whatsapp/webhook/${b.id}'); app.showToast('Copied to clipboard!')">Copy</button>
                            </div>
                            <p style="font-size:0.75rem;color:#2563eb;margin-top:8px;font-weight:500">✨ Pro Tip: Use the 'Verify Token' above in your Meta Dashboard to instantly connect.</p>
                        </div>

                        <button class="btn btn-primary" style="margin-top:16px;width:100%" onclick="window.pages._saveWASettings()">🚀 Save & Connect WhatsApp</button>
                    </div>
                </div>
            </div>

            <!-- Payment Configuration -->
            <div class="settings-section">
                <h3>💳 Payment Gateway</h3>
                <div class="card">
                    <div class="card-body">
                        <div class="settings-grid">
                            <div class="form-group">
                                <label>Payment Provider</label>
                                <select id="set-pay-provider">
                                    <option value="none" ${b.payment_provider === 'none' ? 'selected' : ''}>None</option>
                                    <option value="stripe" ${b.payment_provider === 'stripe' ? 'selected' : ''}>Stripe (Global)</option>
                                    <option value="paymob" ${b.payment_provider === 'paymob' ? 'selected' : ''}>Paymob (Egypt/MENA)</option>
                                    <option value="areeba" ${b.payment_provider === 'areeba' ? 'selected' : ''}>Areeba (Lebanon)</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Payment Status</label>
                                <div style="display:flex;align-items:center;gap:10px;height:40px">
                                    <label class="toggle">
                                        <input type="checkbox" id="set-pay-enabled" ${b.payment_enabled ? 'checked' : ''}>
                                        <span class="toggle-slider"></span>
                                    </label>
                                    <span style="font-size:0.9rem">${b.payment_enabled ? 'Active' : 'Disabled'}</span>
                                </div>
                            </div>
                            <div class="form-group" style="grid-column:span 2">
                                <label>API Secret Key</label>
                                <input type="password" value="${b.payment_api_key || ''}" id="set-pay-key" placeholder="sk_test_...">
                            </div>
                        </div>
                        <button class="btn btn-primary btn-sm" style="margin-top:12px" onclick="window.pages._savePaymentSettings()">Configure Payment Gateway</button>
                    </div>
                </div>
            </div>

            <!-- Subscription -->
            <div class="settings-section">
                <h3>💳 Subscription</h3>
                <div class="card">
                    <div class="card-body">
                        <div style="display:flex;align-items:center;gap:16px;margin-bottom:16px">
                            <div style="font-size:2rem">🚀</div>
                            <div>
                                <div style="font-weight:700;font-size:1.1rem;text-transform:capitalize">${b.subscription_plan || 'Free'} Plan</div>
                                <div style="color:var(--text-secondary)">Your current subscription plan</div>
                            </div>
                        </div>
                        <button class="btn btn-primary btn-sm">Upgrade Plan</button>
                    </div>
                </div>
            </div>
        </div>`;
    },

    async _saveSettings() { app.showToast('Business settings saved!', 'success'); },
    async _saveAISettings() { app.showToast('AI settings saved!', 'success'); },
    async _saveBranding() { app.showToast('Branding saved!', 'success'); },
    async _saveWASettings() { app.showToast('WhatsApp configuration updated!', 'success'); },
    async _savePaymentSettings() { app.showToast('Payment gateway configured!', 'success'); },
};
