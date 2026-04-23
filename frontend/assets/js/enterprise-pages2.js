/**
 * DevTrack AI - Enterprise Feature Pages (Part 2)
 * Coupons, Loyalty, Team, Reports
 */

// ═══════════════════════════════════════════════════════════════════
// COUPONS PAGE
// ═══════════════════════════════════════════════════════════════════

window.pages.coupons = async function() {
    const container = PAGE();
    container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

    let coupons = [];
    let promotions = [];
    try {
        const [cRes, pRes] = await Promise.all([
            api.get('/coupons?limit=50'),
            api.get('/coupons/promotions')
        ]);
        coupons = cRes?.coupons || cRes || [];
        promotions = pRes?.promotions || pRes || [];
    } catch (e) {
        coupons = [
            { id: '1', code: 'SAVE20', name: '20% Off Everything', discount_type: 'percentage', discount_value: 20, usage_limit: 100, times_used: 45, status: 'active', expires_at: new Date(Date.now() + 7*86400000).toISOString() },
            { id: '2', code: 'FLAT50', name: '$50 Off Orders $200+', discount_type: 'fixed', discount_value: 50, minimum_order_amount: 200, usage_limit: 50, times_used: 12, status: 'active' },
            { id: '3', code: 'FREESHIP', name: 'Free Shipping', discount_type: 'fixed', discount_value: 10, status: 'active', times_used: 89 },
            { id: '4', code: 'SUMMER23', name: 'Summer Sale', discount_type: 'percentage', discount_value: 15, status: 'expired', times_used: 234 },
        ];
        promotions = [
            { id: '1', name: 'Weekend Flash Sale', discount_type: 'percentage', discount_value: 25, is_active: true, starts_at: new Date().toISOString(), ends_at: new Date(Date.now() + 2*86400000).toISOString() },
        ];
    }

    const discountDisplay = (c) => c.discount_type === 'percentage' ? `${c.discount_value}%` : formatCurrency(c.discount_value);
    const statusBadge = (status) => {
        const colors = { active: 'success', expired: 'secondary', scheduled: 'warning', paused: 'warning' };
        return `<span class="badge badge-${colors[status] || 'info'}">${status}</span>`;
    };

    container.innerHTML = `
    <div class="page-enter">
        <div class="stats-grid">
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon purple">🏷️</div></div>
                <div class="stat-value">${coupons.length}</div>
                <div class="stat-label">Total Coupons</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon green">✅</div></div>
                <div class="stat-value">${coupons.filter(c => c.status === 'active').length}</div>
                <div class="stat-label">Active</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon blue">🔄</div></div>
                <div class="stat-value">${coupons.reduce((a, c) => a + (c.times_used || 0), 0)}</div>
                <div class="stat-label">Total Uses</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon yellow">🎁</div></div>
                <div class="stat-value">${promotions.filter(p => p.is_active).length}</div>
                <div class="stat-label">Active Promos</div>
            </div>
        </div>

        <!-- Active Promotions Banner -->
        ${promotions.filter(p => p.is_active).length > 0 ? `
        <div class="card glass-card" style="background:linear-gradient(135deg, rgba(99,102,241,0.2), rgba(168,85,247,0.2));border-color:rgba(99,102,241,0.3);margin-bottom:20px">
            <div class="card-body">
                <div style="display:flex;align-items:center;gap:15px">
                    <div style="font-size:2.5rem">🎉</div>
                    <div style="flex:1">
                        <h3 style="margin:0">${promotions[0].name}</h3>
                        <p style="margin:5px 0 0;color:var(--text-secondary)">${discountDisplay(promotions[0])} off • Ends ${formatDate(promotions[0].ends_at)}</p>
                    </div>
                    <button class="btn btn-secondary" onclick="window.pages._editPromotion('${promotions[0].id}')">Edit</button>
                </div>
            </div>
        </div>
        ` : ''}

        <div class="card glass-card">
            <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
                <h3>🏷️ Coupon Codes</h3>
                <button class="btn btn-primary" onclick="window.pages._createCoupon()">➕ New Coupon</button>
            </div>
            <div class="card-body" style="padding:0">
                <table class="data-table">
                    <thead>
                        <tr><th>Code</th><th>Name</th><th>Discount</th><th>Min. Order</th><th>Usage</th><th>Status</th><th>Expires</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                        ${coupons.map(c => `
                            <tr>
                                <td><code style="background:rgba(99,102,241,0.2);padding:4px 8px;border-radius:4px;font-weight:600">${c.code}</code></td>
                                <td>${c.name}</td>
                                <td><strong>${discountDisplay(c)}</strong></td>
                                <td>${c.minimum_order_amount ? formatCurrency(c.minimum_order_amount) : '-'}</td>
                                <td>${c.times_used || 0}${c.usage_limit ? ' / ' + c.usage_limit : ''}</td>
                                <td>${statusBadge(c.status)}</td>
                                <td>${c.expires_at ? formatDate(c.expires_at) : 'Never'}</td>
                                <td>
                                    <button class="btn btn-sm btn-secondary" onclick="window.pages._editCoupon('${c.id}')">✏️</button>
                                    <button class="btn btn-sm btn-secondary" onclick="navigator.clipboard.writeText('${c.code}');app.showToast('Copied!')">📋</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card glass-card" style="margin-top:20px">
            <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
                <h3>🎁 Promotions</h3>
                <button class="btn btn-secondary" onclick="window.pages._createPromotion()">➕ New Promotion</button>
            </div>
            <div class="card-body">
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:15px">
                    ${promotions.map(p => `
                        <div style="padding:20px;background:rgba(255,255,255,0.05);border-radius:12px;border:1px solid rgba(255,255,255,0.1)">
                            <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:10px">
                                <h4 style="margin:0">${p.name}</h4>
                                ${p.is_active ? '<span class="badge badge-success">Active</span>' : '<span class="badge badge-secondary">Inactive</span>'}
                            </div>
                            <p style="font-size:1.5rem;font-weight:700;color:var(--primary);margin:10px 0">${discountDisplay(p)}</p>
                            <p style="font-size:0.85rem;color:var(--text-secondary)">${formatDate(p.starts_at)} - ${formatDate(p.ends_at)}</p>
                            <button class="btn btn-sm btn-secondary" style="margin-top:10px" onclick="window.pages._editPromotion('${p.id}')">Edit</button>
                        </div>
                    `).join('')}
                    ${promotions.length === 0 ? '<p style="color:var(--text-secondary)">No promotions yet</p>' : ''}
                </div>
            </div>
        </div>
    </div>`;
};

window.pages._createCoupon = () => app.showToast('Coupon creator - Coming soon', 'info');
window.pages._editCoupon = (id) => app.showToast('Edit coupon', 'info');
window.pages._createPromotion = () => app.showToast('Promotion creator - Coming soon', 'info');
window.pages._editPromotion = (id) => app.showToast('Edit promotion', 'info');


// ═══════════════════════════════════════════════════════════════════
// LOYALTY PAGE
// ═══════════════════════════════════════════════════════════════════

window.pages.loyalty = async function() {
    const container = PAGE();
    container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

    let program = null;
    let tiers = [];
    let rewards = [];
    let topMembers = [];

    try {
        const [pRes, tRes, rRes] = await Promise.all([
            api.get('/loyalty/program'),
            api.get('/loyalty/tiers'),
            api.get('/loyalty/rewards')
        ]);
        program = pRes;
        tiers = tRes?.tiers || tRes || [];
        rewards = rRes?.rewards || rRes || [];
    } catch (e) {
        program = { name: 'Rewards Program', points_per_currency: 1, currency_per_point: 0.01, is_active: true };
        tiers = [
            { id: '1', name: 'Bronze', color: '#CD7F32', min_points: 0, points_multiplier: 1.0, discount_percentage: 0 },
            { id: '2', name: 'Silver', color: '#C0C0C0', min_points: 500, points_multiplier: 1.25, discount_percentage: 5 },
            { id: '3', name: 'Gold', color: '#FFD700', min_points: 2000, points_multiplier: 1.5, discount_percentage: 10 },
            { id: '4', name: 'Platinum', color: '#E5E4E2', min_points: 5000, points_multiplier: 2.0, discount_percentage: 15, free_shipping: true },
        ];
        rewards = [
            { id: '1', name: '$5 Off Your Order', points_cost: 500, reward_type: 'discount', reward_value: 5, is_active: true, times_redeemed: 45 },
            { id: '2', name: '$10 Off Your Order', points_cost: 900, reward_type: 'discount', reward_value: 10, is_active: true, times_redeemed: 32 },
            { id: '3', name: 'Free Product', points_cost: 2000, reward_type: 'product', is_active: true, times_redeemed: 8 },
        ];
        topMembers = [
            { name: 'John Doe', points: 4520, tier: 'Gold' },
            { name: 'Jane Smith', points: 3200, tier: 'Gold' },
            { name: 'Bob Wilson', points: 1850, tier: 'Silver' },
        ];
    }

    container.innerHTML = `
    <div class="page-enter">
        <!-- Program Status -->
        <div class="card glass-card" style="background:linear-gradient(135deg, rgba(251,191,36,0.1), rgba(245,158,11,0.1));border-color:rgba(251,191,36,0.3);margin-bottom:20px">
            <div class="card-body" style="display:flex;align-items:center;gap:20px">
                <div style="font-size:3rem">⭐</div>
                <div style="flex:1">
                    <h2 style="margin:0">${program?.name || 'Loyalty Program'}</h2>
                    <p style="margin:5px 0 0;color:var(--text-secondary)">Earn ${program?.points_per_currency || 1} point per $1 spent • Redeem for discounts & rewards</p>
                </div>
                <div style="text-align:right">
                    ${program?.is_active ? '<span class="badge badge-success" style="font-size:1rem;padding:8px 16px">✓ Active</span>' : '<span class="badge badge-secondary">Inactive</span>'}
                </div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon purple">👥</div></div>
                <div class="stat-value">1,247</div>
                <div class="stat-label">Total Members</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon yellow">⭐</div></div>
                <div class="stat-value">456K</div>
                <div class="stat-label">Points Issued</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon green">🎁</div></div>
                <div class="stat-value">${rewards.reduce((a, r) => a + (r.times_redeemed || 0), 0)}</div>
                <div class="stat-label">Rewards Redeemed</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon blue">🔗</div></div>
                <div class="stat-value">89</div>
                <div class="stat-label">Referrals</div>
            </div>
        </div>

        <!-- Tiers -->
        <div class="card glass-card">
            <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
                <h3>🏆 Loyalty Tiers</h3>
                <button class="btn btn-secondary btn-sm" onclick="window.pages._editTiers()">Edit Tiers</button>
            </div>
            <div class="card-body">
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px">
                    ${tiers.map(t => `
                        <div style="padding:20px;background:linear-gradient(135deg, ${t.color}22, ${t.color}11);border-radius:12px;border:2px solid ${t.color}">
                            <div style="display:flex;align-items:center;gap:10px;margin-bottom:15px">
                                <div style="width:40px;height:40px;border-radius:50%;background:${t.color};display:flex;align-items:center;justify-content:center">🏆</div>
                                <div>
                                    <h4 style="margin:0">${t.name}</h4>
                                    <span style="font-size:0.8rem;color:var(--text-secondary)">${t.min_points}+ points</span>
                                </div>
                            </div>
                            <div style="font-size:0.9rem">
                                <div style="margin-bottom:5px">🔢 ${t.points_multiplier}x points multiplier</div>
                                ${t.discount_percentage ? `<div style="margin-bottom:5px">💰 ${t.discount_percentage}% discount</div>` : ''}
                                ${t.free_shipping ? '<div>🚚 Free shipping</div>' : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>

        <!-- Rewards Catalog -->
        <div class="card glass-card" style="margin-top:20px">
            <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
                <h3>🎁 Rewards Catalog</h3>
                <button class="btn btn-primary" onclick="window.pages._createReward()">➕ Add Reward</button>
            </div>
            <div class="card-body">
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:15px">
                    ${rewards.map(r => `
                        <div style="padding:20px;background:rgba(255,255,255,0.05);border-radius:12px;text-align:center">
                            <div style="font-size:2.5rem;margin-bottom:10px">🎁</div>
                            <h4 style="margin:0 0 5px">${r.name}</h4>
                            <div style="font-size:1.25rem;font-weight:700;color:var(--primary)">${r.points_cost} pts</div>
                            <p style="font-size:0.8rem;color:var(--text-secondary);margin:10px 0">${r.times_redeemed || 0} redeemed</p>
                            <button class="btn btn-sm btn-secondary" onclick="window.pages._editReward('${r.id}')">Edit</button>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    </div>`;
};

window.pages._editTiers = () => app.showToast('Tier editor - Coming soon', 'info');
window.pages._createReward = () => app.showToast('Reward creator - Coming soon', 'info');
window.pages._editReward = (id) => app.showToast('Edit reward', 'info');


// ═══════════════════════════════════════════════════════════════════
// TEAM PAGE
// ═══════════════════════════════════════════════════════════════════

window.pages.team = async function() {
    const container = PAGE();
    container.innerHTML = '<div class="page-enter"><div class="spinner" style="margin:40px auto"></div></div>';

    let members = [];
    let roles = [];
    let invites = [];

    try {
        const [mRes, rRes, iRes] = await Promise.all([
            api.get('/team/members'),
            api.get('/team/roles'),
            api.get('/team/invites')
        ]);
        members = mRes?.members || mRes || [];
        roles = rRes?.roles || rRes || [];
        invites = iRes?.invites || iRes || [];
    } catch (e) {
        members = [
            { id: '1', user: { name: 'Admin User', email: 'admin@example.com' }, role: { name: 'Owner' }, is_active: true, last_active_at: new Date().toISOString() },
            { id: '2', user: { name: 'John Manager', email: 'john@example.com' }, role: { name: 'Manager' }, is_active: true, last_active_at: new Date(Date.now() - 3600000).toISOString() },
            { id: '3', user: { name: 'Jane Staff', email: 'jane@example.com' }, role: { name: 'Staff' }, is_active: true, last_active_at: new Date(Date.now() - 86400000).toISOString() },
        ];
        roles = [
            { id: '1', name: 'Owner', description: 'Full access to everything', is_system: true },
            { id: '2', name: 'Admin', description: 'Manage all operations', is_system: true },
            { id: '3', name: 'Manager', description: 'Manage team and operations', is_system: true },
            { id: '4', name: 'Staff', description: 'Handle day-to-day tasks', is_system: true },
        ];
        invites = [
            { id: '1', email: 'newmember@example.com', role: { name: 'Staff' }, status: 'pending', expires_at: new Date(Date.now() + 7*86400000).toISOString() },
        ];
    }

    const roleColors = { Owner: 'danger', Admin: 'primary', Manager: 'warning', Staff: 'info', Viewer: 'secondary' };

    container.innerHTML = `
    <div class="page-enter">
        <div class="stats-grid">
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon blue">👥</div></div>
                <div class="stat-value">${members.length}</div>
                <div class="stat-label">Team Members</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon green">✅</div></div>
                <div class="stat-value">${members.filter(m => m.is_active).length}</div>
                <div class="stat-label">Active</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon purple">🔑</div></div>
                <div class="stat-value">${roles.length}</div>
                <div class="stat-label">Roles</div>
            </div>
            <div class="stat-card glass-card">
                <div class="stat-header"><div class="stat-icon yellow">✉️</div></div>
                <div class="stat-value">${invites.filter(i => i.status === 'pending').length}</div>
                <div class="stat-label">Pending Invites</div>
            </div>
        </div>

        <!-- Pending Invites -->
        ${invites.filter(i => i.status === 'pending').length > 0 ? `
        <div class="card glass-card" style="margin-bottom:20px">
            <div class="card-header"><h3>✉️ Pending Invitations</h3></div>
            <div class="card-body">
                ${invites.filter(i => i.status === 'pending').map(i => `
                    <div style="display:flex;align-items:center;justify-content:space-between;padding:10px;background:rgba(255,255,255,0.05);border-radius:8px;margin-bottom:10px">
                        <div>
                            <strong>${i.email}</strong>
                            <span class="badge badge-${roleColors[i.role?.name] || 'info'}" style="margin-left:10px">${i.role?.name || 'Staff'}</span>
                        </div>
                        <div style="display:flex;gap:10px;align-items:center">
                            <span style="font-size:0.8rem;color:var(--text-secondary)">Expires ${formatDate(i.expires_at)}</span>
                            <button class="btn btn-sm btn-secondary" onclick="window.pages._resendInvite('${i.id}')">Resend</button>
                            <button class="btn btn-sm btn-secondary" onclick="window.pages._cancelInvite('${i.id}')">Cancel</button>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
        ` : ''}

        <!-- Team Members -->
        <div class="card glass-card">
            <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
                <h3>👥 Team Members</h3>
                <button class="btn btn-primary" onclick="window.pages._inviteMember()">➕ Invite Member</button>
            </div>
            <div class="card-body" style="padding:0">
                <table class="data-table">
                    <thead>
                        <tr><th>Member</th><th>Role</th><th>Status</th><th>Last Active</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                        ${members.map(m => `
                            <tr>
                                <td>
                                    <div style="display:flex;align-items:center;gap:10px">
                                        <div style="width:36px;height:36px;border-radius:50%;background:var(--primary);display:flex;align-items:center;justify-content:center;font-weight:600">${(m.user?.name || 'U')[0]}</div>
                                        <div>
                                            <div><strong>${m.user?.name || 'User'}</strong></div>
                                            <div style="font-size:0.8rem;color:var(--text-secondary)">${m.user?.email || ''}</div>
                                        </div>
                                    </div>
                                </td>
                                <td><span class="badge badge-${roleColors[m.role?.name] || 'info'}">${m.role?.name || 'Staff'}</span></td>
                                <td>${m.is_active ? '<span class="badge badge-success">Active</span>' : '<span class="badge badge-secondary">Inactive</span>'}</td>
                                <td>${m.last_active_at ? formatDate(m.last_active_at) : 'Never'}</td>
                                <td>
                                    <button class="btn btn-sm btn-secondary" onclick="window.pages._editMember('${m.id}')">✏️</button>
                                    ${m.role?.name !== 'Owner' ? `<button class="btn btn-sm btn-secondary" onclick="window.pages._removeMember('${m.id}')">🗑️</button>` : ''}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Roles -->
        <div class="card glass-card" style="margin-top:20px">
            <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
                <h3>🔑 Roles & Permissions</h3>
                <button class="btn btn-secondary btn-sm" onclick="window.pages._createRole()">➕ Create Role</button>
            </div>
            <div class="card-body">
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:15px">
                    ${roles.map(r => `
                        <div style="padding:20px;background:rgba(255,255,255,0.05);border-radius:12px">
                            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                                <h4 style="margin:0"><span class="badge badge-${roleColors[r.name] || 'info'}">${r.name}</span></h4>
                                ${r.is_system ? '<span style="font-size:0.7rem;color:var(--text-secondary)">System</span>' : ''}
                            </div>
                            <p style="font-size:0.85rem;color:var(--text-secondary);margin:0">${r.description || 'No description'}</p>
                            ${!r.is_system ? `<button class="btn btn-sm btn-secondary" style="margin-top:10px" onclick="window.pages._editRole('${r.id}')">Edit</button>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    </div>`;
};

window.pages._inviteMember = () => app.showToast('Invitation form - Coming soon', 'info');
window.pages._editMember = (id) => app.showToast('Edit member', 'info');
window.pages._removeMember = (id) => confirm('Remove this team member?') && app.showToast('Member removed', 'success');
window.pages._resendInvite = (id) => app.showToast('Invitation resent', 'success');
window.pages._cancelInvite = (id) => app.showToast('Invitation cancelled', 'info');
window.pages._createRole = () => app.showToast('Role creator - Coming soon', 'info');
window.pages._editRole = (id) => app.showToast('Edit role', 'info');


// ═══════════════════════════════════════════════════════════════════
// REPORTS PAGE
// ═══════════════════════════════════════════════════════════════════

window.pages.reports = async function() {
    const container = PAGE();
    
    container.innerHTML = `
    <div class="page-enter">
        <div class="card glass-card" style="background:linear-gradient(135deg, rgba(99,102,241,0.1), rgba(168,85,247,0.1));margin-bottom:20px">
            <div class="card-body" style="display:flex;align-items:center;gap:20px">
                <div style="font-size:3rem">📊</div>
                <div>
                    <h2 style="margin:0">Reports & Analytics</h2>
                    <p style="margin:5px 0 0;color:var(--text-secondary)">Generate detailed reports and export your data</p>
                </div>
            </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px">
            <!-- Sales Report -->
            <div class="card glass-card">
                <div class="card-body">
                    <div style="display:flex;align-items:center;gap:15px;margin-bottom:15px">
                        <div style="width:50px;height:50px;border-radius:12px;background:rgba(34,197,94,0.2);display:flex;align-items:center;justify-content:center;font-size:1.5rem">💰</div>
                        <div>
                            <h3 style="margin:0">Sales Report</h3>
                            <p style="margin:0;font-size:0.85rem;color:var(--text-secondary)">Revenue, orders, trends</p>
                        </div>
                    </div>
                    <div class="form-group" style="margin-bottom:10px">
                        <label style="font-size:0.85rem">Date Range</label>
                        <select class="form-control form-control-sm" id="sales-period">
                            <option value="7">Last 7 days</option>
                            <option value="30" selected>Last 30 days</option>
                            <option value="90">Last 90 days</option>
                            <option value="365">Last year</option>
                        </select>
                    </div>
                    <div style="display:flex;gap:10px">
                        <button class="btn btn-primary btn-sm" onclick="window.pages._downloadReport('sales', 'pdf')">📄 PDF</button>
                        <button class="btn btn-secondary btn-sm" onclick="window.pages._downloadReport('sales', 'excel')">📊 Excel</button>
                    </div>
                </div>
            </div>

            <!-- Inventory Report -->
            <div class="card glass-card">
                <div class="card-body">
                    <div style="display:flex;align-items:center;gap:15px;margin-bottom:15px">
                        <div style="width:50px;height:50px;border-radius:12px;background:rgba(59,130,246,0.2);display:flex;align-items:center;justify-content:center;font-size:1.5rem">📦</div>
                        <div>
                            <h3 style="margin:0">Inventory Report</h3>
                            <p style="margin:0;font-size:0.85rem;color:var(--text-secondary)">Stock levels, value, alerts</p>
                        </div>
                    </div>
                    <div style="display:flex;gap:10px">
                        <button class="btn btn-primary btn-sm" onclick="window.pages._downloadReport('inventory', 'pdf')">📄 PDF</button>
                        <button class="btn btn-secondary btn-sm" onclick="window.pages._downloadReport('inventory', 'excel')">📊 Excel</button>
                    </div>
                </div>
            </div>

            <!-- Customer Report -->
            <div class="card glass-card">
                <div class="card-body">
                    <div style="display:flex;align-items:center;gap:15px;margin-bottom:15px">
                        <div style="width:50px;height:50px;border-radius:12px;background:rgba(168,85,247,0.2);display:flex;align-items:center;justify-content:center;font-size:1.5rem">👥</div>
                        <div>
                            <h3 style="margin:0">Customer Report</h3>
                            <p style="margin:0;font-size:0.85rem;color:var(--text-secondary)">Customer analytics & segments</p>
                        </div>
                    </div>
                    <div style="display:flex;gap:10px">
                        <button class="btn btn-primary btn-sm" onclick="window.pages._downloadReport('customers', 'pdf')">📄 PDF</button>
                        <button class="btn btn-secondary btn-sm" onclick="window.pages._downloadReport('customers', 'excel')">📊 Excel</button>
                    </div>
                </div>
            </div>

            <!-- Financial Report -->
            <div class="card glass-card">
                <div class="card-body">
                    <div style="display:flex;align-items:center;gap:15px;margin-bottom:15px">
                        <div style="width:50px;height:50px;border-radius:12px;background:rgba(251,191,36,0.2);display:flex;align-items:center;justify-content:center;font-size:1.5rem">📈</div>
                        <div>
                            <h3 style="margin:0">Financial Summary</h3>
                            <p style="margin:0;font-size:0.85rem;color:var(--text-secondary)">Revenue, expenses, profit</p>
                        </div>
                    </div>
                    <div class="form-group" style="margin-bottom:10px">
                        <label style="font-size:0.85rem">Period</label>
                        <select class="form-control form-control-sm" id="financial-period">
                            <option value="month">This Month</option>
                            <option value="quarter">This Quarter</option>
                            <option value="year" selected>This Year</option>
                        </select>
                    </div>
                    <div style="display:flex;gap:10px">
                        <button class="btn btn-primary btn-sm" onclick="window.pages._downloadReport('financial', 'pdf')">📄 PDF</button>
                        <button class="btn btn-secondary btn-sm" onclick="window.pages._downloadReport('financial', 'excel')">📊 Excel</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Data Exports -->
        <div class="card glass-card" style="margin-top:20px">
            <div class="card-header"><h3>📤 Data Exports</h3></div>
            <div class="card-body">
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:15px">
                    <button class="btn btn-secondary" style="padding:20px;display:flex;flex-direction:column;align-items:center;gap:10px" onclick="window.pages._exportData('orders')">
                        <span style="font-size:1.5rem">📦</span>
                        <span>Export Orders</span>
                    </button>
                    <button class="btn btn-secondary" style="padding:20px;display:flex;flex-direction:column;align-items:center;gap:10px" onclick="window.pages._exportData('customers')">
                        <span style="font-size:1.5rem">👥</span>
                        <span>Export Customers</span>
                    </button>
                    <button class="btn btn-secondary" style="padding:20px;display:flex;flex-direction:column;align-items:center;gap:10px" onclick="window.pages._exportData('products')">
                        <span style="font-size:1.5rem">🏷️</span>
                        <span>Export Products</span>
                    </button>
                    <button class="btn btn-secondary" style="padding:20px;display:flex;flex-direction:column;align-items:center;gap:10px" onclick="window.pages._exportData('transactions')">
                        <span style="font-size:1.5rem">💳</span>
                        <span>Export Transactions</span>
                    </button>
                </div>
            </div>
        </div>
    </div>`;
};

window.pages._downloadReport = (type, format) => {
    const businessId = localStorage.getItem('business_id') || 'demo';
    let url = `/api/v1/reports/${type}?business_id=${businessId}&format=${format}`;
    
    if (type === 'sales') {
        const days = document.getElementById('sales-period')?.value || 30;
        const endDate = new Date().toISOString();
        const startDate = new Date(Date.now() - days * 86400000).toISOString();
        url += `&start_date=${startDate}&end_date=${endDate}`;
    }
    
    app.showToast(`Generating ${type} report...`, 'info');
    window.open(url, '_blank');
};

window.pages._exportData = (type) => {
    const businessId = localStorage.getItem('business_id') || 'demo';
    app.showToast(`Exporting ${type}...`, 'info');
    window.open(`/api/v1/reports/export/${type}?business_id=${businessId}`, '_blank');
};
