/**
 * DevTrack AI - Real-time WebSocket Client
 * 
 * Handles:
 * - Persistent connection to the backend
 * - Authentication with JWT
 * - Message routing for different update types
 * - Automatic reconnection logic
 */

class DevTrackWS {
    /**
     * @param {string} token - JWT authentication token
     */
    constructor(token) {
        this.token = token;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 3000; // 3 seconds
        
        // Protocol: ws:// for development, wss:// for production
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        this.url = `${protocol}//${host}/ws?token=${token}`;
        
        this.handlers = {
            'message': [],
            'order_update': [],
            'booking_update': [],
            'notification': [],
            'typing': [],
            'user_status': [],
            'connection' : []
        };
    }

    /**
     * Initialize connection
     */
    connect() {
        console.log('🔌 Connecting to DevTrack WebSocket...');
        this.socket = new WebSocket(this.url);

        this.socket.onopen = (event) => {
            console.log('✅ WebSocket Connected!');
            this.reconnectAttempts = 0;
            this.emit('connection', { status: 'online' });
            
            // Start heartbeats
            this.startHeartbeat();
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.routeMessage(data);
            } catch (err) {
                console.error('❌ Error parsing WebSocket message:', err);
            }
        };

        this.socket.onclose = (event) => {
            console.warn('⚠️ WebSocket Disconnected.');
            this.emit('connection', { status: 'offline' });
            this.handleReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('❌ WebSocket Error:', error);
        };
    }

    /**
     * Dispatch messages to registered handlers based on type
     */
    routeMessage(data) {
        const type = data.type;
        if (this.handlers[type]) {
            this.handlers[type].forEach(handler => handler(data));
        }
        
        // Also fire a general 'all' message for debugging
        if (this.handlers['all']) {
            this.handlers['all'].forEach(handler => handler(data));
        }
    }

    /**
     * Register a callback for a specific message type
     */
    on(type, callback) {
        if (!this.handlers[type]) {
            this.handlers[type] = [];
        }
        this.handlers[type].push(callback);
    }

    /**
     * Send a message through the socket
     */
    send(type, payload = {}) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ type, ...payload }));
        } else {
            console.error('❌ Cannot send message: WebSocket is not open.');
        }
    }

    /**
     * Fire internal events
     */
    emit(event, data) {
        if (this.handlers[event]) {
            this.handlers[event].forEach(handler => handler(data));
        }
    }

    /**
     * Logic for automatic reconnection
     */
    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`⏳ Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            setTimeout(() => this.connect(), this.reconnectInterval);
        } else {
            console.error('❌ Max reconnection attempts reached. Please refresh the page.');
        }
    }

    /**
     * Keep alive heartbeats
     */
    startHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.send('ping');
            } else {
                clearInterval(this.heartbeatTimer);
            }
        }, 30000); // 30 seconds
    }
}

// Export for use in dashboard.js
window.DevTrackWS = DevTrackWS;
