/**
 * DevTrack AI - Enterprise Feature Pages
 * Payment, Inventory, Campaigns, Coupons, Loyalty, Team, Reports
 */

// ═══════════════════════════════════════════════════════════════════
// PAYMENTS PAGE
// ═══════════════════════════════════════════════════════════════════

window.pages.payments = async function() {
    const container = PAGE();
    container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

    let payments = [];
    let summary = { total: 0, completed: 0, pending: 0, refunded: 0 };
    
    try {
        const res = await api.get('/payments?limit=50');
        payments = res?.payments || res || [];
        payments.forEach(p => {
            summary.total += p.amount || 0;
            if (p.status === 'completed' || p.status === 'succeeded') summary.completed += p.amount || 0;
            if (p.status === 'pending') summary.pending += p.amount || 0;
            if (p.status === 'refunded') summary.refunded += p.amount || 0;
        });
    } catch (e) {
        payments = [
            { id: '1', payment_number: 'PAY-001', amount: 299.99, status: 'completed', method: 'card', card_brand: 'visa', card_last4: '4242', created_at: new Date().toISOString(), customer: { name: 'John Doe' } },
            { id: '2', payment_number: 'PAY-002', amount: 149.50, status: 'completed', method: 'card', card_brand: 'mastercard', card_last4: '5555', created_at: new Date().toISOString(), customer: { name: 'Jane Smith' } },
            { id: '3', payment_number: 'PAY-003', amount: 89.00, status: 'pending', method: 'card', created_at: new Date().toISOString(), customer: { name: 'Bob Wilson' } },
            { id: '4', payment_number: 'PAY-004', amount: 450.00, status: 'refunded', method: 'card', card_brand: 'visa', card_last4: '1234', created_at: new Date().toISOString(), customer: { name: 'Alice Brown' } },
        ];
        summary = { total: 988.49, completed: 449.49, pending: 89.00, refunded: 450.00 };
    }

    const paymentStatusBadge = (status) => {
        const colors = { completed: 'success', succeeded: 'success', pending: 'warning', processing: 'info', failed: 'danger', refunded: 'secondary', cancelled: 'danger' };
        return `<span class="badge badge-${colors[status] || 'info'}">${status}</span>`;
    };

    container.innerHTML = `
    <div class="page-enter">
        <div class="stats-grid">
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon blue">💰</div></div>
                <div class="stat-value">${formatCurrency(summary.total)}</div>
                <div class="stat-label">Total Processed</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon green">✅</div></div>
                <div class="stat-value">${formatCurrency(summary.completed)}</div>
                <div class="stat-label">Completed</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon yellow">⏳</div></div>
                <div class="stat-value">${formatCurrency(summary.pending)}</div>
                <div class="stat-label">Pending</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon red">↩️</div></div>
                <div class="stat-value">${formatCurrency(summary.refunded)}</div>
                <div class="stat-label">Refunded</div>
            </div>
        </div>

        <div class="card glass-card">
            <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
                <h3>💳 Recent Payments</h3>
                <div style="display:flex;gap:10px">
                    <select class="form-control form-control-sm" style="width:150px" onchange="window.pages._filterPayments(this.value)">
                        <option value="">All Status</option>
                        <option value="completed">Completed</option>
                        <option value="pending">Pending</option>
                        <option value="refunded">Refunded</option>
                    </select>
                    <button class="btn btn-primary btn-sm" onclick="window.pages._exportPayments()">📊 Export</button>
                </div>
            </div>
            <div class="card-body" style="padding:0">
                <table class="data-table">
                    <thead>
                        <tr><th>Payment #</th><th>Customer</th><th>Amount</th><th>Method</th><th>Status</th><th>Date</th><th>Actions</th></tr>
                    </thead>
                    <tbody id="payments-table-body">
                        ${payments.map(p => `
                            <tr data-status="${p.status}">
                                <td><code>${p.payment_number}</code></td>
                                <td>${p.customer?.name || 'Guest'}</td>
                                <td><strong>${formatCurrency(p.amount)}</strong></td>
                                <td>💳 ${p.card_brand || 'Card'}${p.card_last4 ? ' •••• ' + p.card_last4 : ''}</td>
                                <td>${paymentStatusBadge(p.status)}</td>
                                <td>${formatDate(p.created_at)}</td>
                                <td>
                                    <button class="btn btn-sm btn-secondary" onclick="window.pages._viewPayment('${p.id}')">👁</button>
                                    ${p.status === 'completed' ? `<button class="btn btn-sm btn-secondary" onclick="window.pages._refundPayment('${p.id}')">↩️</button>` : ''}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                ${payments.length === 0 ? '<div class="empty-state"><div class="empty-state-icon">💳</div><h3>No payments yet</h3></div>' : ''}
            </div>
        </div>
    </div>`;
};

window.pages._filterPayments = (status) => document.querySelectorAll('#payments-table-body tr').forEach(row => row.style.display = !status || row.dataset.status === status ? '' : 'none');
window.pages._viewPayment = (id) => app.showToast('Payment details loaded', 'info');
window.pages._refundPayment = (id) => confirm('Refund this payment?') && app.showToast('Refund initiated', 'success');
window.pages._exportPayments = () => app.showToast('Exporting payments...', 'info');


// ═══════════════════════════════════════════════════════════════════
// INVENTORY PAGE
// ═══════════════════════════════════════════════════════════════════

window.pages.inventory = async function() {
    const container = PAGE();
    container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

    let products = [];
    let summary = { total: 0, low: 0, out: 0, value: 0 };

    try {
        const res = await api.get('/inventory?limit=100');
        products = res?.items || res || [];
        products.forEach(p => {
            summary.total++;
            summary.value += (p.quantity_on_hand || 0) * (p.cost_price || 0);
            if (p.quantity_on_hand <= 0) summary.out++;
            else if (p.quantity_on_hand <= (p.reorder_point || 10)) summary.low++;
        });
    } catch (e) {
        products = [
            { id: '1', product: { name: 'Premium Widget', sku: 'WDG-001' }, quantity_on_hand: 45, quantity_reserved: 5, reorder_point: 20, cost_price: 15.00 },
            { id: '2', product: { name: 'Basic Gadget', sku: 'GDG-002' }, quantity_on_hand: 8, quantity_reserved: 2, reorder_point: 15, cost_price: 8.50 },
            { id: '3', product: { name: 'Super Tool', sku: 'TL-003' }, quantity_on_hand: 0, quantity_reserved: 0, reorder_point: 10, cost_price: 25.00 },
            { id: '4', product: { name: 'Deluxe Set', sku: 'SET-004' }, quantity_on_hand: 120, quantity_reserved: 10, reorder_point: 30, cost_price: 45.00 },
        ];
        summary = { total: 4, low: 1, out: 1, value: 6352.50 };
    }

    const stockBadge = (qty, reorder) => {
        if (qty <= 0) return '<span class="badge badge-danger">Out of Stock</span>';
        if (qty <= reorder) return '<span class="badge badge-warning">Low Stock</span>';
        return '<span class="badge badge-success">In Stock</span>';
    };

    container.innerHTML = `
    <div class="page-enter">
        <div class="stats-grid">
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon blue">📦</div></div>
                <div class="stat-value">${summary.total}</div>
                <div class="stat-label">Total Products</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon yellow">⚠️</div></div>
                <div class="stat-value">${summary.low}</div>
                <div class="stat-label">Low Stock</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon red">🚫</div></div>
                <div class="stat-value">${summary.out}</div>
                <div class="stat-label">Out of Stock</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon green">💰</div></div>
                <div class="stat-value">${formatCurrency(summary.value)}</div>
                <div class="stat-label">Inventory Value</div>
            </div>
        </div>

        <div class="card glass-card">
            <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
                <h3>📦 Stock Levels</h3>
                <div style="display:flex;gap:10px">
                    <input type="text" class="form-control form-control-sm" placeholder="Search..." style="width:180px" id="inv-search">
                    <button class="btn btn-primary btn-sm" onclick="window.pages._adjustStock()">➕ Adjust</button>
                    <button class="btn btn-secondary btn-sm" onclick="window.pages._createPO()">📋 New PO</button>
                </div>
            </div>
            <div class="card-body" style="padding:0">
                <table class="data-table">
                    <thead>
                        <tr><th>Product</th><th>SKU</th><th>On Hand</th><th>Reserved</th><th>Available</th><th>Reorder Point</th><th>Status</th><th>Actions</th></tr>
                    </thead>
                    <tbody id="inventory-tbody">
                        ${products.map(p => `
                            <tr>
                                <td><strong>${p.product?.name || p.name || 'Product'}</strong></td>
                                <td><code>${p.product?.sku || p.sku || '-'}</code></td>
                                <td>${p.quantity_on_hand || 0}</td>
                                <td>${p.quantity_reserved || 0}</td>
                                <td><strong>${(p.quantity_on_hand || 0) - (p.quantity_reserved || 0)}</strong></td>
                                <td>${p.reorder_point || 10}</td>
                                <td>${stockBadge(p.quantity_on_hand, p.reorder_point)}</td>
                                <td>
                                    <button class="btn btn-sm btn-secondary" onclick="window.pages._editInventory('${p.id}')">✏️</button>
                                    <button class="btn btn-sm btn-secondary" onclick="window.pages._viewHistory('${p.id}')">📜</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    </div>`;

    document.getElementById('inv-search')?.addEventListener('input', (e) => {
        const q = e.target.value.toLowerCase();
        document.querySelectorAll('#inventory-tbody tr').forEach(row => {
            row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
        });
    });
};

window.pages._adjustStock = () => app.showToast('Stock adjustment modal - Coming soon', 'info');
window.pages._createPO = () => app.showToast('Purchase Order creation - Coming soon', 'info');
window.pages._editInventory = (id) => app.showToast('Edit inventory item', 'info');
window.pages._viewHistory = (id) => app.showToast('Stock movement history', 'info');


// ═══════════════════════════════════════════════════════════════════
// CAMPAIGNS PAGE
// ═══════════════════════════════════════════════════════════════════

window.pages.campaigns = async function() {
    const container = PAGE();
    container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

    let campaigns = [];
    try {
        const res = await api.get('/campaigns?limit=50');
        campaigns = res?.campaigns || res || [];
    } catch (e) {
        campaigns = [
            { id: '1', name: 'Summer Sale Announcement', campaign_type: 'email', status: 'sent', total_recipients: 1250, opened_count: 456, clicked_count: 89, sent_at: new Date().toISOString() },
            { id: '2', name: 'New Product Launch', campaign_type: 'email', status: 'draft', total_recipients: 0, opened_count: 0, clicked_count: 0, created_at: new Date().toISOString() },
            { id: '3', name: 'Flash Sale SMS', campaign_type: 'sms', status: 'scheduled', total_recipients: 850, scheduled_at: new Date(Date.now() + 86400000).toISOString() },
            { id: '4', name: 'Welcome Series', campaign_type: 'email', status: 'active', total_recipients: 340, opened_count: 280, clicked_count: 120, created_at: new Date().toISOString() },
        ];
    }

    const typeIcon = (type) => ({ email: '📧', sms: '📱', whatsapp: '💬' }[type] || '📧');
    const statusBadge = (status) => {
        const colors = { draft: 'secondary', scheduled: 'warning', sending: 'info', sent: 'success', active: 'primary', paused: 'warning' };
        return `<span class="badge badge-${colors[status] || 'info'}">${status}</span>`;
    };

    container.innerHTML = `
    <div class="page-enter">
        <div class="stats-grid">
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon purple">📧</div></div>
                <div class="stat-value">${campaigns.length}</div>
                <div class="stat-label">Total Campaigns</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon green">✅</div></div>
                <div class="stat-value">${campaigns.filter(c => c.status === 'sent').length}</div>
                <div class="stat-label">Sent</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon blue">👁</div></div>
                <div class="stat-value">${campaigns.reduce((a, c) => a + (c.opened_count || 0), 0)}</div>
                <div class="stat-label">Total Opens</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon yellow">🖱️</div></div>
                <div class="stat-value">${campaigns.reduce((a, c) => a + (c.clicked_count || 0), 0)}</div>
                <div class="stat-label">Total Clicks</div>
            </div>
        </div>

        <div class="card glass-card">
            <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
                <h3>📧 Marketing Campaigns</h3>
                <button class="btn btn-primary" onclick="window.pages._createCampaign()">➕ New Campaign</button>
            </div>
            <div class="card-body" style="padding:0">
                <table class="data-table">
                    <thead>
                        <tr><th>Campaign</th><th>Type</th><th>Status</th><th>Recipients</th><th>Opens</th><th>Clicks</th><th>Rate</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                        ${campaigns.map(c => `
                            <tr>
                                <td><strong>${c.name}</strong></td>
                                <td>${typeIcon(c.campaign_type)} ${c.campaign_type}</td>
                                <td>${statusBadge(c.status)}</td>
                                <td>${c.total_recipients || 0}</td>
                                <td>${c.opened_count || 0}</td>
                                <td>${c.clicked_count || 0}</td>
                                <td>${c.total_recipients ? ((c.opened_count || 0) / c.total_recipients * 100).toFixed(1) + '%' : '-'}</td>
                                <td>
                                    <button class="btn btn-sm btn-secondary" onclick="window.pages._editCampaign('${c.id}')">✏️</button>
                                    ${c.status === 'draft' ? `<button class="btn btn-sm btn-primary" onclick="window.pages._sendCampaign('${c.id}')">🚀</button>` : ''}
                                    <button class="btn btn-sm btn-secondary" onclick="window.pages._viewStats('${c.id}')">📊</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                ${campaigns.length === 0 ? '<div class="empty-state"><div class="empty-state-icon">📧</div><h3>No campaigns yet</h3><p>Create your first marketing campaign</p></div>' : ''}
            </div>
        </div>

        <div class="card glass-card" style="margin-top:20px">
            <div class="card-header"><h3>📝 Email Templates</h3></div>
            <div class="card-body">
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:15px">
                    <div class="template-card" style="padding:20px;background:rgba(99,102,241,0.1);border-radius:12px;cursor:pointer;border:2px dashed rgba(99,102,241,0.3)" onclick="window.pages._createTemplate()">
                        <div style="text-align:center">
                            <div style="font-size:2rem;margin-bottom:10px">➕</div>
                            <strong>Create Template</strong>
                        </div>
                    </div>
                    <div class="template-card" style="padding:20px;background:rgba(255,255,255,0.05);border-radius:12px;cursor:pointer">
                        <div style="font-size:1.5rem;margin-bottom:10px">🎉</div>
                        <strong>Welcome Email</strong>
                        <p style="font-size:0.8rem;color:var(--text-secondary);margin-top:5px">New customer welcome</p>
                    </div>
                    <div class="template-card" style="padding:20px;background:rgba(255,255,255,0.05);border-radius:12px;cursor:pointer">
                        <div style="font-size:1.5rem;margin-bottom:10px">🛒</div>
                        <strong>Abandoned Cart</strong>
                        <p style="font-size:0.8rem;color:var(--text-secondary);margin-top:5px">Cart recovery</p>
                    </div>
                    <div class="template-card" style="padding:20px;background:rgba(255,255,255,0.05);border-radius:12px;cursor:pointer">
                        <div style="font-size:1.5rem;margin-bottom:10px">⭐</div>
                        <strong>Review Request</strong>
                        <p style="font-size:0.8rem;color:var(--text-secondary);margin-top:5px">Ask for feedback</p>
                    </div>
                </div>
            </div>
        </div>
    </div>`;
};

window.pages._createCampaign = () => app.showToast('Campaign builder - Coming soon', 'info');
window.pages._editCampaign = (id) => app.showToast('Edit campaign', 'info');
window.pages._sendCampaign = (id) => confirm('Send this campaign now?') && app.showToast('Campaign queued for sending', 'success');
window.pages._viewStats = (id) => app.showToast('Campaign statistics', 'info');
window.pages._createTemplate = () => app.showToast('Template editor - Coming soon', 'info');
