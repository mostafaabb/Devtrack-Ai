/**
 * DevTrack AI - Main Application Controller
 * Handles authentication, navigation, theme switching, and app initialization.
 */

class App {

    // ─── Initialization ─────────────────────────────────────────
    init() {
        this.bindAuthEvents();
        this.bindNavEvents();
        this.bindTopbarEvents();
        this.initMetaSDK();

        // Check if user is already authenticated
        if (api.isAuthenticated()) {
            this.showDashboard();
        } else {
            this.showAuth();
        }
    }

    // ─── Auth Events ────────────────────────────────────────────
    bindAuthEvents() {
        // Toggle between login and register forms
        document.getElementById('show-register')?.addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('login-form').classList.remove('active');
            document.getElementById('register-form').classList.add('active');
        });

        document.getElementById('show-login')?.addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('register-form').classList.remove('active');
            document.getElementById('login-form').classList.add('active');
        });

        // Login
        document.getElementById('login-form')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            const btn = document.getElementById('login-btn');

            btn.innerHTML = '<span class="spinner"></span>';
            try {
                await api.login(email, password);
                this.showDashboard();
                this.showToast('Welcome back! 👋', 'success');
            } catch (err) {
                this.showToast(err.message || 'Login failed', 'error');
            }
            btn.innerHTML = '<span>Sign In</span><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>';
        });

        // Register
        document.getElementById('register-form')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = {
                full_name: document.getElementById('reg-name').value,
                phone: document.getElementById('reg-phone').value,
                email: document.getElementById('reg-email').value,
                password: document.getElementById('reg-password').value,
                business_name: document.getElementById('reg-business').value,
                business_type: document.getElementById('reg-type').value,
                whatsapp_phone_number_id: document.getElementById('reg-wa-id').value || null,
                whatsapp_api_token: document.getElementById('reg-wa-token').value || null,
            };
            const btn = document.getElementById('register-btn');

            btn.innerHTML = '<span class="spinner"></span>';
            try {
                await api.register(data);
                this.showDashboard();
                this.showToast('Account created successfully! 🚀', 'success');
            } catch (err) {
                this.showToast(err.message || 'Registration failed', 'error');
            }
            btn.innerHTML = '<span>Create Account</span><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>';
        });

        // WhatsApp Connect (Meta Embedded Signup)
        document.getElementById('btn-wa-connect')?.addEventListener('click', () => {
            this.launchWhatsAppSignup();
        });
    }

    // ─── Meta WhatsApp SDK ──────────────────────────────────────
    initMetaSDK() {
        // We'll init when we have the app ID from the user object or backend settings
        const appId = api.user?.meta_app_id || '7842516335805216'; // Fallback to your ID
        
        window.fbAsyncInit = function() {
            FB.init({
                appId      : appId,
                cookie     : true,
                xfbml      : true,
                version    : 'v18.0'
            });
        };
        console.log("Meta SDK Ready with App ID:", appId);
    }

    launchWhatsAppSignup() {
        FB.login((response) => {
            if (response.authResponse) {
                const accessToken = response.authResponse.accessToken;
                // In a real flow, we would call an endpoint to get the PhoneID 
                // but for this demo, we'll simulate the successful capture
                document.getElementById('reg-wa-token').value = accessToken;
                document.getElementById('reg-wa-id').value = 'auto_provisioned_' + Math.random().toString(36).substring(7);
                
                const container = document.getElementById('wa-onboarding-container');
                container.style.background = 'rgba(37, 211, 102, 0.2)';
                container.innerHTML = `
                    <div style="color:#25D366; font-weight:700; display:flex; align-items:center; justify-content:center; gap:8px">
                        <span>✅</span> WhatsApp Connected Successfully
                    </div>
                `;
                this.showToast('WhatsApp connected! Finish registration to go live.', 'success');
            } else {
                this.showToast('Facebook login cancelled or failed.', 'error');
            }
        }, {
            scope: 'whatsapp_business_management,whatsapp_business_messaging',
            extras: {
                feature: 'whatsapp_embedded_signup'
            }
        });
    }

    // ─── Navigation Events ──────────────────────────────────────
    bindNavEvents() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const page = item.dataset.page;
                if (page) this.navigateTo(page);
            });
        });
    }

    // ─── Topbar Events ──────────────────────────────────────────
    bindTopbarEvents() {
        // Theme toggle
        document.getElementById('theme-toggle')?.addEventListener('click', () => {
            const html = document.documentElement;
            const current = html.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', next);
            localStorage.setItem('devtrack_theme', next);
        });

        // Mobile menu
        document.getElementById('mobile-menu')?.addEventListener('click', () => {
            document.getElementById('sidebar')?.classList.toggle('open');
        });

        // Sidebar toggle
        document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
            document.getElementById('sidebar')?.classList.toggle('collapsed');
        });

        // Logout
        document.getElementById('logout-btn')?.addEventListener('click', () => {
            api.clearAuth();
            this.showAuth();
            this.showToast('Logged out successfully', 'info');
        });

        // Restore saved theme
        const savedTheme = localStorage.getItem('devtrack_theme');
        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
        }
    }

    // ─── Screen Switching ───────────────────────────────────────
    showAuth() {
        document.getElementById('auth-screen').classList.remove('hidden');
        document.getElementById('dashboard').classList.add('hidden');
    }

    showDashboard() {
        document.getElementById('auth-screen').classList.add('hidden');
        document.getElementById('dashboard').classList.remove('hidden');

        // Update user info in sidebar
        if (api.user) {
            const avatar = document.getElementById('user-avatar');
            const name = document.getElementById('user-name');
            const role = document.getElementById('user-role');
            const bizName = document.getElementById('business-name-display');

            if (avatar) avatar.textContent = (api.user.full_name || 'A')[0].toUpperCase();
            if (name) name.textContent = api.user.full_name || 'Admin';
            if (role) role.textContent = api.user.role || 'admin';
            if (bizName) bizName.textContent = api.user.business_name || 'My Business';
        }

        // Navigate to dashboard page
        this.navigateTo('dashboard');
    }

    // ─── Page Navigation ────────────────────────────────────────
    navigateTo(page) {
        this.currentPage = page;

        // Update active nav item
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === page);
        });

        // Update page title
        const titles = {
            dashboard: '📊 Dashboard',
            conversations: '💬 Conversations',
            customers: '👥 Customers',
            orders: '📦 Orders',
            bookings: '📅 Bookings',
            products: '🏷️ Products & Services',
            documents: '📂 Documents',
            workflows: '⚡ Automation',
            analytics: '📈 Analytics',
            modules: '🧩 Modules',
            settings: '⚙️ Settings',
        };
        document.getElementById('page-title').textContent = titles[page] || page;

        // Close mobile sidebar
        document.getElementById('sidebar')?.classList.remove('open');

        // Render the page
        if (window.pages && window.pages[page]) {
            window.pages[page]();
        }
    }

    // ─── Toast Notifications ────────────────────────────────────
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
        
        let displayMessage = message;
        if (typeof message === 'object') {
            displayMessage = message.message || message.detail || JSON.stringify(message);
        }
        
        toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${displayMessage}</span>`;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // ─── Modal Helper ───────────────────────────────────────────
    showModal(title, contentHtml, footerHtml = '') {
        const existing = document.querySelector('.modal-overlay');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="btn-icon modal-close" onclick="this.closest('.modal-overlay').remove()">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                </div>
                <div class="modal-body">${contentHtml}</div>
                ${footerHtml ? `<div class="modal-footer">${footerHtml}</div>` : ''}
            </div>
        `;

        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.remove();
        });

        document.body.appendChild(overlay);
        return overlay;
    }

    closeModal() {
        const overlay = document.querySelector('.modal-overlay');
        if (overlay) overlay.remove();
    }
}

// ─── Initialize App ─────────────────────────────────────────────
const app = new App();
document.addEventListener('DOMContentLoaded', () => app.init());
