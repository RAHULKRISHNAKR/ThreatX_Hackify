/**
 * WebSocket Connection Manager
 * Handles WebSocket connections for real-time threat notifications
 */

class SocketHandler {
    constructor(options = {}) {
        this.options = {
            reconnectInterval: 5000,
            pingInterval: 30000,
            debug: false,
            onNotification: null,
            onThreatDetected: null,
            onStatsUpdate: null,
            ...options
        };
        
        this.socket = null;
        this.reconnectTimeout = null;
        this.pingTimeout = null;
        this.connected = false;
        this.connecting = false;
    }
    
    /**
     * Initialize the WebSocket connection
     */
    connect() {
        if (this.connected || this.connecting) return;
        
        this.connecting = true;
        this._log('Connecting to WebSocket server...');
        
        // Get the correct protocol (wss for HTTPS, ws for HTTP)
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications`;
        
        try {
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = this._handleOpen.bind(this);
            this.socket.onclose = this._handleClose.bind(this);
            this.socket.onmessage = this._handleMessage.bind(this);
            this.socket.onerror = this._handleError.bind(this);
        } catch (error) {
            this._log('Error creating WebSocket:', error);
            this._scheduleReconnect();
        }
    }
    
    /**
     * Disconnect the WebSocket
     */
    disconnect() {
        this._log('Disconnecting WebSocket...');
        
        this._clearTimers();
        
        if (this.socket) {
            // Remove event handlers to avoid potential memory leaks
            this.socket.onopen = null;
            this.socket.onclose = null;
            this.socket.onmessage = null;
            this.socket.onerror = null;
            
            // Close the connection
            if (this.connected) {
                this.socket.close();
            }
            
            this.socket = null;
        }
        
        this.connected = false;
        this.connecting = false;
    }
    
    /**
     * Send a message through the WebSocket
     * @param {Object} data - The data to send
     * @returns {Boolean} - Whether the message was sent
     */
    send(data) {
        if (!this.connected || !this.socket) {
            return false;
        }
        
        try {
            this.socket.send(JSON.stringify(data));
            return true;
        } catch (error) {
            this._log('Error sending message:', error);
            return false;
        }
    }
    
    /**
     * Subscribe to a specific notification channel
     * @param {String} channel - The channel to subscribe to
     */
    subscribe(channel) {
        this.send({
            type: 'subscribe',
            channel: channel
        });
    }
    
    /**
     * Handle WebSocket open event
     */
    _handleOpen(event) {
        this._log('WebSocket connection established');
        this.connected = true;
        this.connecting = false;
        
        // Start ping interval to keep connection alive
        this._startPingInterval();
        
        // Subscribe to all notifications by default
        this.subscribe('all');
    }
    
    /**
     * Handle WebSocket close event
     */
    _handleClose(event) {
        this._log('WebSocket connection closed', event.code, event.reason);
        this.connected = false;
        this.connecting = false;
        
        this._clearTimers();
        this._scheduleReconnect();
    }
    
    /**
     * Handle WebSocket error event
     */
    _handleError(error) {
        this._log('WebSocket error:', error);
        
        // The socket will also trigger onclose after an error
    }
    
    /**
     * Handle WebSocket message event
     */
    _handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            
            // Handle different message types
            switch (data.type) {
                case 'ping':
                    this._handlePing();
                    break;
                    
                case 'notification':
                    this._handleNotification(data.notification);
                    break;
                    
                case 'threat_detected':
                    this._handleThreatDetected(data.threat);
                    break;
                    
                case 'stats_update':
                    this._handleStatsUpdate(data.stats);
                    break;
                    
                default:
                    this._log('Unknown message type:', data.type);
            }
        } catch (error) {
            this._log('Error processing message:', error);
        }
    }
    
    /**
     * Handle ping messages to keep the connection alive
     */
    _handlePing() {
        this.send({ type: 'pong' });
    }
    
    /**
     * Handle notification messages
     */
    _handleNotification(notification) {
        this._log('Received notification:', notification);
        
        if (typeof this.options.onNotification === 'function') {
            this.options.onNotification(notification);
        }
    }
    
    /**
     * Handle threat detection messages
     */
    _handleThreatDetected(threat) {
        this._log('Threat detected:', threat);
        
        if (typeof this.options.onThreatDetected === 'function') {
            this.options.onThreatDetected(threat);
        }
    }
    
    /**
     * Handle stats update messages
     */
    _handleStatsUpdate(stats) {
        this._log('Stats updated:', stats);
        
        if (typeof this.options.onStatsUpdate === 'function') {
            this.options.onStatsUpdate(stats);
        }
    }
    
    /**
     * Start ping interval to keep connection alive
     */
    _startPingInterval() {
        this._clearTimers();
        
        this.pingTimeout = setInterval(() => {
            this.send({ type: 'ping' });
        }, this.options.pingInterval);
    }
    
    /**
     * Schedule reconnection
     */
    _scheduleReconnect() {
        this._clearTimers();
        
        this.reconnectTimeout = setTimeout(() => {
            this._log('Attempting to reconnect...');
            this.connect();
        }, this.options.reconnectInterval);
    }
    
    /**
     * Clear all timers
     */
    _clearTimers() {
        if (this.pingTimeout) {
            clearInterval(this.pingTimeout);
            this.pingTimeout = null;
        }
        
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }
    }
    
    /**
     * Log messages if debug is enabled
     */
    _log(...args) {
        if (this.options.debug) {
            console.log('[SocketHandler]', ...args);
        }
    }
}

// Export for use in other files
window.SocketHandler = SocketHandler;
