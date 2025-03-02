document.addEventListener("DOMContentLoaded", function() {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatOutput = document.getElementById("chat-output");
    
    // Initialize notifications
    const notificationPanel = document.getElementById("notification-panel");
    const notificationsList = document.getElementById("notifications-list");
    const notificationBadge = document.getElementById("notification-badge");
    const notificationToggle = document.getElementById("notification-toggle");
    
    let lastNotificationId = 0;
    let unreadNotificationsCount = 0;
    let socket;

    if (!chatForm || !chatInput || !chatOutput) {
        console.error("Required chat elements not found!");
        return;
    }

    // Add initial greeting
    appendMessage("Assistant: Hello! I'm ThreatX AI. How can I assist you with cybersecurity today?", false);

    // Add better debug logging for the WebSocket connection
    function initializeWebSocket() {
        // Get the correct protocol (wss for HTTPS, ws for HTTP)
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/socket.io/?EIO=4&transport=websocket`;
        
        console.log("Attempting WebSocket connection to:", wsUrl);
        
        try {
            // Using Socket.IO client directly instead of raw WebSocket
            socket = io();
            
            socket.on('connect', function() {
                console.log("Socket.IO connected successfully with ID:", socket.id);
            });
            
            socket.on('notification', function(data) {
                console.log("Notification received:", data);
                if (data.notification) {
                    handleNewNotification(data.notification);
                }
            });
            
            socket.on('threat_detected', function(data) {
                console.log("Threat detected:", data);
                if (data.threat) {
                    handleThreatDetection(data.threat);
                }
            });
            
            socket.on('disconnect', function() {
                console.log("Socket.IO disconnected, will attempt reconnect automatically");
            });
            
            socket.on('connect_error', function(error) {
                console.error("Socket.IO connection error:", error);
            });
        } catch (e) {
            console.error("Error initializing Socket.IO:", e);
        }
    }
    
    // Handle new notification
    function handleNewNotification(notification) {
        lastNotificationId = notification.id;
        
        // Add notification to panel
        const notificationItem = document.createElement("div");
        notificationItem.className = `notification-item ${notification.severity}`;
        notificationItem.dataset.id = notification.id;
        
        notificationItem.innerHTML = `
            <div class="notification-header">
                <span class="notification-severity ${notification.severity}">${notification.severity}</span>
                <span class="notification-time">${formatTime(notification.timestamp)}</span>
            </div>
            <div class="notification-message">${notification.message}</div>
            <button class="notification-dismiss"><i class="fas fa-times"></i></button>
        `;
        
        if (notificationsList) {
            notificationsList.prepend(notificationItem);
            
            // Handle dismiss button
            notificationItem.querySelector(".notification-dismiss").addEventListener("click", function(e) {
                e.stopPropagation();
                markNotificationRead(notification.id);
                notificationItem.remove();
            });
            
            // Update badge
            updateNotificationBadge(++unreadNotificationsCount);
            
            // Flash the notification icon
            if (notificationToggle) {
                flashNotificationIcon();
            }
            
            // If it's a critical notification, show alert
            if (notification.severity === 'critical') {
                showAlertModal(notification);
            }
        }
    }
    
    // Show alert modal for critical notifications
    function showAlertModal(notification) {
        const modal = document.createElement("div");
        modal.className = "alert-modal";
        
        modal.innerHTML = `
            <div class="alert-modal-content">
                <div class="alert-modal-header">
                    <h2><i class="fas fa-exclamation-triangle"></i> Critical Security Alert</h2>
                </div>
                <div class="alert-modal-body">
                    <p>${notification.message}</p>
                </div>
                <div class="alert-modal-footer">
                    <button class="alert-dismiss-btn">Dismiss</button>
                    <button class="alert-details-btn">View Details</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        modal.querySelector(".alert-dismiss-btn").addEventListener("click", function() {
            modal.remove();
        });
        
        modal.querySelector(".alert-details-btn").addEventListener("click", function() {
            modal.remove();
            if (notificationPanel && notificationPanel.style.display === "none") {
                toggleNotificationPanel();
            }
        });
    }
    
    // Handle real-time threat detection
    function handleThreatDetection(threat) {
        // Add visual indicator in chat if the threat is related to current conversation
        const threatMessage = document.createElement("div");
        threatMessage.className = `system-message threat-warning ${threat.severity}`;
        
        threatMessage.innerHTML = `
            <i class="fas fa-shield-alt"></i> 
            <span>Potential ${threat.category} detected. Exercise caution.</span>
        `;
        
        chatOutput.appendChild(threatMessage);
        chatOutput.scrollTop = chatOutput.scrollHeight;
    }
    
    // Update notification badge
    function updateNotificationBadge(count) {
        if (notificationBadge) {
            notificationBadge.textContent = count > 0 ? count : '';
            notificationBadge.style.display = count > 0 ? 'flex' : 'none';
        }
    }
    
    // Flash notification icon to draw attention
    function flashNotificationIcon() {
        if (notificationToggle) {
            notificationToggle.classList.add('flash');
            setTimeout(() => {
                notificationToggle.classList.remove('flash');
            }, 2000);
        }
    }
    
    // Format timestamp for display
    function formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }
    
    // Mark notification as read
    function markNotificationRead(id) {
        fetch('/api/notifications/mark-read', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ notification_id: id })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success && unreadNotificationsCount > 0) {
                updateNotificationBadge(--unreadNotificationsCount);
            }
        })
        .catch(error => console.error('Error marking notification as read:', error));
    }
    
    // Toggle notification panel visibility
    function toggleNotificationPanel() {
        if (notificationPanel) {
            const isHidden = notificationPanel.style.display === "none" || !notificationPanel.style.display;
            notificationPanel.style.display = isHidden ? "block" : "none";
            
            if (isHidden) {
                fetchNotifications();
            }
        }
    }
    
    // Fetch notifications from server
    function fetchNotifications() {
        fetch(`/api/notifications?since_id=${lastNotificationId}`)
            .then(response => response.json())
            .then(data => {
                if (data.notifications && data.notifications.length) {
                    data.notifications.forEach(notification => {
                        handleNewNotification(notification);
                    });
                }
            })
            .catch(error => console.error('Error fetching notifications:', error));
    }
    
    // Initialize notification panel toggle if it exists
    if (notificationToggle) {
        notificationToggle.addEventListener("click", toggleNotificationPanel);
    }
    
    // Initialize WebSocket for notifications
    initializeWebSocket();
    
    // Poll for notifications as backup if WebSocket fails
    setInterval(fetchNotifications, 30000);

    // Chat form submission
    chatForm.addEventListener("submit", function(event) {
        event.preventDefault();
        const userInput = chatInput.value.trim();
        
        if (!userInput) return;
        
        // Disable input and show loading immediately
        chatInput.disabled = true;
        chatInput.value = "";

        // Show user message instantly
        appendMessage("Human: " + userInput, true);
        
        // Add loading animation
        const loadingMsg = appendMessage("Assistant: Analyzing response...", false);
        let dots = 0;
        const loadingInterval = setInterval(() => {
            dots = (dots + 1) % 4;
            loadingMsg.textContent = "Assistant: Analyzing response" + ".".repeat(dots);
        }, 300);

        fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: userInput })
        })
        .then(response => response.json())
        .then(data => {
            clearInterval(loadingInterval);
            loadingMsg.remove();
            appendMessage("Assistant: " + data.response, false);
        })
        .catch(error => {
            clearInterval(loadingInterval);
            loadingMsg.remove();
            appendMessage("Assistant: Sorry, there was an error processing your request.", false);
        })
        .finally(() => {
            chatInput.disabled = false;
            chatInput.focus();
        });
    });

    function appendMessage(message, isUser) {
        const messageElement = document.createElement("div");
        messageElement.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        
        if (!isUser && message.startsWith("Assistant: ")) {
            const markdownText = message.replace("Assistant: ", "");
            try {
                messageElement.innerHTML = marked.parse(markdownText);
            } catch (e) {
                messageElement.textContent = message;
            }
        } else {
            messageElement.textContent = message;
        }
        
        chatOutput.appendChild(messageElement);
        chatOutput.scrollTop = chatOutput.scrollHeight;
        return messageElement;
    }

    // Focus input field on load
    chatInput.focus();
});