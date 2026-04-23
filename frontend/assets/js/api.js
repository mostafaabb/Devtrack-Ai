/**
 * DevTrack AI - API Client
 * Handles all HTTP communication with the FastAPI backend.
 * Manages authentication tokens and provides a clean API interface.
 */

const API_BASE = window.location.origin + '/api/v1';

class ApiClient {
    constructor() {
        this.token = localStorage.getItem('devtrack_token') || null;
        this.user = JSON.parse(localStorage.getItem('devtrack_user') || 'null');
        
        // Sticky Demo Mode
        if (window.location.search.includes('demo=true')) {
            localStorage.setItem('devtrack_demo', 'true');
        } else if (window.location.search.includes('demo=false')) {
            localStorage.removeItem('devtrack_demo');
        }
        this.isDemo = localStorage.getItem('devtrack_demo') === 'true';
    }

    // ─── Token Management ───────────────────────────────────────
    setAuth(token, user) {
        this.token = token;
        this.user = user;
        localStorage.setItem('devtrack_token', token);
        localStorage.setItem('devtrack_user', JSON.stringify(user));
        
        // Ensure theme and session consistency in demo mode
        if (this.isDemo) {
            console.log('✅ Demo session initialized');
        }
    }

    clearAuth() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('devtrack_token');
        localStorage.removeItem('devtrack_user');
    }

    isAuthenticated() {
        return !!this.token;
    }

    // ─── HTTP Methods ───────────────────────────────────────────
    async request(method, endpoint, data = null, isFormData = false) {
        // Force demo mode for ALL requests if sticky demo is enabled
        if (this.isDemo) {
            return this._mockResponse(method, endpoint, data);
        }
        
        const url = `${API_BASE}${endpoint}`;
        const headers = {};

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        if (!isFormData && data) {
            headers['Content-Type'] = 'application/json';
        }

        const config = { method, headers };

        if (data) {
            config.body = isFormData ? data : JSON.stringify(data);
        }

        try {
            const response = await fetch(url, config);

            if (response.status === 401) {
                this.clearAuth();
                window.location.reload();
                return null;
            }

            const result = await response.json();

            if (!response.ok) {
                // Fallback to demo mode on server errors or if specifically in demo mode
                if (response.status >= 500 || this.isDemo) {
                    console.warn(`API (Error ${response.status}) using Demo Mode fallback`);
                    return this._mockResponse(method, endpoint, data);
                }
                throw new Error(result?.detail || `Error ${response.status}`);
            }

            return result;
        } catch (error) {
            if (error.message.includes('Failed to fetch') || error.message.includes('Unexpected token') || error.message.includes('JSON') || error.name === 'SyntaxError') {
                console.warn('API not available (or returned HTML), using demo mode');
                return this._mockResponse(method, endpoint, data);
            }
            throw error;
        }
    }

    async get(endpoint) { return this.request('GET', endpoint); }
    async post(endpoint, data) { return this.request('POST', endpoint, data); }
    async put(endpoint, data) { return this.request('PUT', endpoint, data); }
    async delete(endpoint) { return this.request('DELETE', endpoint); }
    async upload(endpoint, formData) { return this.request('POST', endpoint, formData, true); }

    // ─── Auth Endpoints ─────────────────────────────────────────
    async register(data) {
        const result = await this.post('/auth/register', data);
        if (result && result.access_token) {
            this.setAuth(result.access_token, result.user);
        }
        return result;
    }

    async login(email, password) {
        const result = await this.post('/auth/login', { email, password });
        if (result && result.access_token) {
            this.setAuth(result.access_token, result.user);
        }
        return result;
    }

    // ─── Demo Mode (Mock Responses) ─────────────────────────────
    // When the backend is not running, provides realistic mock data
    _mockResponse(method, endpoint, data) {
        console.log(`[DEMO] ${method} ${endpoint}`, data);

        // Auth
        if (endpoint === '/auth/register' || endpoint === '/auth/login') {
            const user = {
                id: 'demo-user-001',
                email: data?.email || 'demo@devtrack.ai',
                full_name: data?.full_name || 'Demo User',
                role: 'admin',
                business_id: 'demo-biz-001',
                business_name: data?.business_name || 'Demo Business',
            };
            this.setAuth('demo-token-12345', user);
            return { access_token: 'demo-token-12345', token_type: 'bearer', user };
        }

        // Business
        if (endpoint === '/business/') {
            return {
                id: 'demo-biz-001', name: this.user?.business_name || 'Demo Business',
                slug: 'demo-business', description: 'A demo business for testing',
                business_type: 'restaurant', phone: '+961 70 123 456',
                email: 'info@demo.com', address: 'Beirut, Lebanon',
                city: 'Beirut', country: 'Lebanon', logo_url: null,
                primary_color: '#6366f1', secondary_color: '#8b5cf6',
                ai_tone: 'professional', ai_language: 'en',
                welcome_message: 'Welcome! How can we help you today?',
                subscription_plan: 'pro', is_active: true,
                created_at: '2024-01-15T10:00:00Z'
            };
        }

        // Analytics Summary
        if (endpoint === '/analytics/summary') {
            return {
                total_customers: 247, total_conversations: 1834,
                total_orders: 562, total_bookings: 189,
                total_revenue: 45280.50, active_conversations: 23,
                pending_orders: 12, pending_bookings: 8,
            };
        }

        // Analytics Insights
        if (endpoint === '/analytics/insights') {
            return {
                insights: "📊 Business Performance Summary\n• Total Customers: 247\n• Total Orders: 562\n• Total Revenue: $45,280.50\n• Average Order Value: $80.57\n\n📈 Trends\n• Orders up 18% from last month\n• Customer retention: 73%\n• Peak hours: 12pm-2pm, 7pm-9pm\n\n💡 Recommendations\n• Run lunch specials to boost weekday traffic\n• Implement loyalty program for top 20% customers\n• Automate follow-up messages for repeat orders",
                data: { total_customers: 247, total_orders: 562, total_revenue: 45280.50 }
            };
        }

        // Chart Data
        if (endpoint.startsWith('/analytics/chart-data')) {
            return {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                orders: [32, 28, 45, 38, 52, 68, 41],
                revenue: [960, 840, 1350, 1140, 1560, 2040, 1230],
                conversations: [45, 52, 38, 61, 48, 72, 55],
                customers: [8, 5, 12, 7, 15, 18, 10],
            };
        }

        // Conversations
        if (endpoint === '/conversations/' && method === 'GET') {
            return this._generateMockConversations();
        }

        // Customers
        if (endpoint.startsWith('/customers') && method === 'GET') {
            return this._generateMockCustomers();
        }

        // Orders
        if (endpoint.startsWith('/orders') && method === 'GET') {
            return this._generateMockOrders();
        }

        // Bookings
        if (endpoint.startsWith('/bookings') && method === 'GET') {
            return this._generateMockBookings();
        }

        // Products
        if (endpoint.startsWith('/products') && method === 'GET') {
            return this._generateMockProducts();
        }

        // Documents
        if (endpoint.startsWith('/documents') && method === 'GET') {
            return this._generateMockDocuments();
        }

        // Workflows
        if (endpoint.startsWith('/workflows') && method === 'GET') {
            return this._generateMockWorkflows();
        }

        // Modules
        if (endpoint === '/business/modules') {
            return [
                { key: 'restaurant', name: 'Restaurant Module', description: 'Menu, orders, table reservations', icon: '🍔', features: ['Menu management', 'Order system', 'Table reservations', 'Delivery integration'], is_enabled: true, is_premium: false, config: {} },
                { key: 'hotel', name: 'Hotel Module', description: 'Room booking, guest management', icon: '🏨', features: ['Room booking', 'Availability calendar', 'Guest management', 'Check-in/out'], is_enabled: false, is_premium: false, config: {} },
                { key: 'retail', name: 'Retail Module', description: 'Products, inventory, orders', icon: '🛍️', features: ['Product catalog', 'Inventory tracking', 'Online orders', 'Discounts'], is_enabled: true, is_premium: false, config: {} },
                { key: 'clinic', name: 'Clinic Module', description: 'Appointments, schedules, patients', icon: '🏥', features: ['Appointments', 'Doctor schedules', 'Patient records', 'Prescriptions'], is_enabled: false, is_premium: true, config: {} },
                { key: 'delivery', name: 'Delivery Module', description: 'Order tracking, drivers', icon: '🚚', features: ['Order tracking', 'Driver management', 'Route optimization', 'Delivery status'], is_enabled: false, is_premium: false, config: {} },
            ];
        }

        // Default
        return { message: 'OK (demo mode)' };
    }

    // ─── Mock Data Generators ───────────────────────────────────
    _generateMockConversations() {
        const names = ['Ahmad K.', 'Sara M.', 'Rami H.', 'Nour El-Din', 'Layla B.', 'Hassan J.', 'Maya R.', 'Omar S.'];
        const previews = [
            'I would like to place an order...', 'Can you reserve a table for tonight?',
            'What are your opening hours?', 'Do you have vegetarian options?',
            'I need to book an appointment', 'My order hasn\'t arrived yet',
            'Great service! Thank you!', 'Can I modify my booking?'
        ];
        const statuses = ['ai_handling', 'active', 'pending', 'ai_handling', 'active', 'ai_handling', 'closed', 'pending'];
        return names.map((name, i) => ({
            id: `conv-${i + 1}`,
            customer_id: `cust-${i + 1}`,
            channel: i % 3 === 0 ? 'whatsapp' : 'web',
            status: statuses[i],
            subject: null,
            is_ai_enabled: statuses[i] === 'ai_handling',
            sentiment_score: [75, 50, 30, 80, 60, -20, 90, 40][i],
            last_message_at: new Date(Date.now() - i * 3600000).toISOString(),
            created_at: new Date(Date.now() - i * 86400000).toISOString(),
            messages: [
                { id: `msg-${i}-1`, content: previews[i], sender_type: 'customer', ai_intent: null, is_read: true, created_at: new Date(Date.now() - i * 3600000 - 60000).toISOString() },
                { id: `msg-${i}-2`, content: 'Thank you for reaching out! How can I assist you today?', sender_type: 'ai', ai_intent: 'greeting', ai_confidence: 90, is_read: true, created_at: new Date(Date.now() - i * 3600000).toISOString() },
            ],
            customer: { id: `cust-${i + 1}`, name, email: `${name.toLowerCase().replace(/[\s.]/g, '')}@email.com`, phone: `+961 7${i} ${100 + i * 111} ${200 + i * 222}`, channel: i % 3 === 0 ? 'whatsapp' : 'web', tags: [], created_at: new Date(Date.now() - i * 86400000).toISOString() }
        }));
    }

    _generateMockCustomers() {
        const names = ['Ahmad Khalil', 'Sara Mansour', 'Rami Haddad', 'Nour El-Din Abbas', 'Layla Badran', 'Hassan Jamal', 'Maya Rizk', 'Omar Saad', 'Dina Fakhoury', 'Karim Nassar'];
        return names.map((name, i) => ({
            id: `cust-${i + 1}`, name, email: `${name.toLowerCase().replace(/\s/g, '.')}@email.com`,
            phone: `+961 ${70 + i} ${String(100000 + i * 11111).slice(0, 3)} ${String(200000 + i * 22222).slice(0, 3)}`,
            channel: ['web', 'whatsapp', 'web'][i % 3], tags: [['vip', 'frequent'], ['new'], ['frequent'], ['vip'], []][i % 5],
            created_at: new Date(Date.now() - i * 172800000).toISOString(),
            last_seen: new Date(Date.now() - i * 86400000).toISOString(),
        }));
    }

    _generateMockOrders() {
        const statuses = ['pending', 'confirmed', 'preparing', 'completed', 'completed', 'delivering', 'completed', 'cancelled'];
        return statuses.map((status, i) => ({
            id: `order-${i + 1}`, order_number: `ORD-${String(10000 + i * 1111).slice(0, 5)}${['AX', 'BY', 'CZ', 'DW', 'EV', 'FU', 'GT', 'HS'][i]}`,
            order_type: ['delivery', 'dine_in', 'takeaway', 'online'][i % 4], status,
            subtotal: [45.00, 32.50, 78.00, 25.00, 120.00, 55.00, 88.50, 42.00][i],
            tax: [4.95, 3.58, 8.58, 2.75, 13.20, 6.05, 9.74, 4.62][i],
            discount: 0, delivery_fee: i % 4 === 0 ? 5 : 0,
            total: [49.95, 36.08, 86.58, 27.75, 133.20, 61.05, 98.24, 46.62][i],
            currency: 'USD', source: ['ai_chat', 'manual', 'whatsapp', 'web'][i % 4],
            created_at: new Date(Date.now() - i * 7200000).toISOString(),
            customer: { id: `cust-${i + 1}`, name: ['Ahmad K.', 'Sara M.', 'Rami H.', 'Nour E.', 'Layla B.', 'Hassan J.', 'Maya R.', 'Omar S.'][i] }
        }));
    }

    _generateMockBookings() {
        const statuses = ['confirmed', 'pending', 'completed', 'pending', 'cancelled', 'confirmed'];
        const types = ['table', 'appointment', 'room', 'service', 'table', 'appointment'];
        return statuses.map((status, i) => ({
            id: `booking-${i + 1}`, booking_number: `BKG-${String(20000 + i * 1111).slice(0, 5)}${['PQ', 'RS', 'TU', 'VW', 'XY', 'ZA'][i]}`,
            booking_type: types[i], status,
            start_time: new Date(Date.now() + (i + 1) * 86400000).toISOString(),
            end_time: null, duration_minutes: [120, 30, null, 60, 90, 45][i],
            party_size: [4, 1, 2, 1, 6, 1][i],
            resource_name: ['Table 5', null, 'Room 201', null, 'Table 12', null][i],
            service_name: [null, 'Consultation', null, 'Haircut', null, 'Checkup'][i],
            price: [0, 50, 150, 30, 0, 75][i], source: ['web', 'ai_chat', 'manual', 'whatsapp', 'web', 'ai_chat'][i],
            created_at: new Date(Date.now() - i * 86400000).toISOString(),
            customer: { id: `cust-${i + 1}`, name: ['Ahmad K.', 'Sara M.', 'Rami H.', 'Nour E.', 'Layla B.', 'Hassan J.'][i] }
        }));
    }

    _generateMockProducts() {
        return [
            { id: 'prod-1', name: 'Grilled Chicken Plate', description: 'Juicy grilled chicken with rice and salad', price: 18.00, sale_price: null, sku: 'GCP-001', stock_quantity: null, image_url: null, is_active: true, is_featured: true, created_at: new Date().toISOString() },
            { id: 'prod-2', name: 'Beef Shawarma Wrap', description: 'Traditional Lebanese shawarma', price: 12.50, sale_price: 10.00, sku: 'BSW-002', stock_quantity: null, image_url: null, is_active: true, is_featured: true, created_at: new Date().toISOString() },
            { id: 'prod-3', name: 'Fattoush Salad', description: 'Fresh mixed greens with sumac dressing', price: 8.00, sale_price: null, sku: 'FS-003', stock_quantity: null, image_url: null, is_active: true, is_featured: false, created_at: new Date().toISOString() },
            { id: 'prod-4', name: 'Hummus Plate', description: 'Creamy hummus with warm bread', price: 6.50, sale_price: null, sku: 'HP-004', stock_quantity: null, image_url: null, is_active: true, is_featured: false, created_at: new Date().toISOString() },
            { id: 'prod-5', name: 'Mixed Grill Platter', description: 'Assorted grilled meats for 2-3 people', price: 45.00, sale_price: 39.99, sku: 'MGP-005', stock_quantity: null, image_url: null, is_active: true, is_featured: true, created_at: new Date().toISOString() },
            { id: 'prod-6', name: 'Fresh Lemonade', description: 'Freshly squeezed with mint', price: 4.50, sale_price: null, sku: 'FL-006', stock_quantity: null, image_url: null, is_active: true, is_featured: false, created_at: new Date().toISOString() },
        ];
    }

    _generateMockDocuments() {
        return [
            { id: 'doc-1', title: 'Restaurant Menu', filename: 'menu_2024.pdf', file_type: 'pdf', file_size: 245000, status: 'processed', chunk_count: 12, created_at: new Date(Date.now() - 604800000).toISOString(), processed_at: new Date(Date.now() - 604000000).toISOString() },
            { id: 'doc-2', title: 'Business Policies', filename: 'policies.txt', file_type: 'txt', file_size: 18500, status: 'processed', chunk_count: 5, created_at: new Date(Date.now() - 1209600000).toISOString(), processed_at: new Date(Date.now() - 1209000000).toISOString() },
            { id: 'doc-3', title: 'FAQ Answers', filename: 'faq.pdf', file_type: 'pdf', file_size: 52000, status: 'processed', chunk_count: 8, created_at: new Date(Date.now() - 2592000000).toISOString(), processed_at: new Date(Date.now() - 2591000000).toISOString() },
        ];
    }

    _generateMockWorkflows() {
        return [
            { id: 'wf-1', name: 'Auto-Reply to Messages', description: 'AI automatically responds to customer messages', status: 'active', trigger_type: 'message_received', trigger_conditions: {}, action_type: 'ai_reply', action_config: {}, execution_count: { total: 1245, success: 1230, failed: 15 }, created_at: new Date(Date.now() - 2592000000).toISOString() },
            { id: 'wf-2', name: 'Notify on New Order', description: 'Send notification when a new order is placed', status: 'active', trigger_type: 'order_placed', trigger_conditions: {}, action_type: 'notify_admin', action_config: { message: 'New order received!' }, execution_count: { total: 562, success: 560, failed: 2 }, created_at: new Date(Date.now() - 1296000000).toISOString() },
            { id: 'wf-3', name: 'Escalate Complaints', description: 'Route negative sentiment to human agent', status: 'active', trigger_type: 'message_received', trigger_conditions: { intent: 'complaint' }, action_type: 'escalate', action_config: {}, execution_count: { total: 23, success: 23, failed: 0 }, created_at: new Date(Date.now() - 864000000).toISOString() },
            { id: 'wf-4', name: 'Welcome New Customers', description: 'Send welcome message to new customers', status: 'inactive', trigger_type: 'customer_created', trigger_conditions: {}, action_type: 'send_message', action_config: { message: 'Welcome to our business! 🎉' }, execution_count: { total: 89, success: 89, failed: 0 }, created_at: new Date(Date.now() - 432000000).toISOString() },
        ];
    }
}

// Global API client instance
const api = new ApiClient();
