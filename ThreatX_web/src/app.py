from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room
from hackbot.hackbot import Print_AI_out, AI_OPTION, initialize_gemini
from hackbot.threat_detector import threat_detector
import traceback
from functools import lru_cache
import threading
import time
import json
import uuid
import random
from datetime import datetime, timedelta

# Update the initialization part
app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True
app.secret_key = 'threatx_secret_key'  # Replace with a secure secret key in production
socketio = SocketIO(app, cors_allowed_origins="*")

# Track connected clients for notifications
connected_clients = set()

# Only initialize once at startup, store the result
if AI_OPTION == "GEMINI":
    gemini_initialized = initialize_gemini()
    if not gemini_initialized:
        print("WARNING: Failed to initialize Gemini at startup. Will retry on first request.")

# Background thread for simulating threat detection (for demo)
def threat_detection_simulator():
    example_threats = [
        {
            "type": "spam_call",
            "content": "This is an urgent call about your car warranty",
            "source": {"phone": "+1234567890", "caller_id": "Unknown"}
        },
        {
            "type": "spam_sms",
            "content": "URGENT: Click here to claim your free $1000 gift card! www.example-scam.com",
            "source": {"phone": "+0987654321"}
        },
        {
            "type": "malicious_content",
            "content": "SELECT * FROM users WHERE username='admin' OR 1=1--'",
            "source": {"ip": "103.45.76.12", "user_agent": "Mozilla/5.0"}
        },
        {
            "type": "spam_email",
            "content": "Dear Sir, I am a prince from Nigeria and I need your help...",
            "source": {"email": "prince@nigeria-royal-family.co", "ip": "91.234.56.78"}
        }
    ]

    while True:
        time.sleep(30)  # Simulate a threat every 30 seconds
        if connected_clients:
            # Pick a random threat example
            import random
            threat = random.choice(example_threats)
            
            # Use the threat detector to analyze
            detection_result = threat_detector.detect_threats(
                threat["content"], 
                source_info=threat["source"]
            )
            
            if detection_result["threats_detected"]:
                notification = {
                    "id": str(int(time.time() * 1000)),
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Detected {list(detection_result['categories'].keys())[0].replace('_', ' ')}",
                    "severity": "high" if random.random() > 0.7 else "medium",
                    "details": detection_result
                }
                
                # Emit to all connected clients
                socketio.emit('notification', {'type': 'notification', 'notification': notification})

# Start the background thread for simulated threats (comment out in production)
threat_thread = threading.Thread(target=threat_detection_simulator)
threat_thread.daemon = True
threat_thread.start()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Render the security dashboard"""
    return render_template('dashboard.html')

@app.route('/chatbot')
def chatbot():
    # Generate session ID if not exists
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return render_template('cybercrime_chatbot.html')

# Cache frequent responses
@lru_cache(maxsize=100)
def get_cached_response(prompt):
    return Print_AI_out(prompt, AI_OPTION)

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        user_input = request.json.get('message', '')
        if not user_input:
            return jsonify({'response': 'No message provided'}), 400

        print(f"Processing request: {user_input[:100]}...")
        
        # Check for threats in the message
        source_info = {
            "ip": request.remote_addr,
            "user_agent": request.headers.get('User-Agent', ''),
            "session_id": session.get('user_id', 'unknown')
        }
        
        threat_result = threat_detector.detect_threats(user_input, source_info)
        if threat_result["threats_detected"]:
            # Create notification for admin
            notification = {
                "id": str(int(time.time() * 1000)),
                "timestamp": datetime.now().isoformat(),
                "message": f"Suspicious message from {source_info.get('ip', 'unknown IP')}",
                "severity": "medium",
                "details": threat_result
            }
            
            # Emit to admins
            socketio.emit('admin_notification', {'type': 'notification', 'notification': notification})
        
        # Try to initialize Gemini if it hasn't been successfully initialized yet
        from hackbot.hackbot import initialization_successful
        if AI_OPTION == "GEMINI" and not initialization_successful:
            initialize_gemini()
            
        response = get_cached_response(user_input)
        
        if "Rate limit exceeded" in response:
            return jsonify({'response': response}), 429
        elif "Error:" in response:
            print(f"API error response: {response}")
            return jsonify({'response': response}), 200
            
        return jsonify({'response': response})

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'response': 'The service is temporarily unavailable. Please try again later.'
        }), 500

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Get recent notifications"""
    since_id = request.args.get('since_id', '0')
    limit = int(request.args.get('limit', 10))
    include_read = request.args.get('include_read', 'false').lower() == 'true'
    
    notifications = threat_detector.get_notifications(
        since_id=since_id,
        limit=limit,
        include_read=include_read
    )
    
    return jsonify({
        'success': True,
        'notifications': notifications
    })

@app.route('/api/notifications/mark-read', methods=['POST'])
def mark_notification_read():
    """Mark notification as read"""
    notification_id = request.json.get('notification_id')
    if not notification_id:
        return jsonify({'success': False, 'error': 'Missing notification ID'}), 400
        
    success = threat_detector.mark_notification_read(notification_id)
    return jsonify({'success': success})

@app.route('/api/threats/stats', methods=['GET'])
def get_threat_stats():
    """Get threat statistics for dashboard with optional timeframe filter"""
    timeframe = request.args.get('timeframe', 'weekly')
    
    # Get base stats
    stats = threat_detector.calculate_threat_statistics()
    
    # Add mock trend data if not present
    if 'recent_trend' not in stats or not stats['recent_trend']:
        if timeframe == 'weekly':
            dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7, 0, -1)]
        elif timeframe == 'monthly':
            dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30, 0, -3)]
        else:  # yearly
            dates = [(datetime.now() - timedelta(days=i*30)).strftime('%Y-%m') for i in range(12, 0, -1)]
        
        stats['recent_trend'] = [
            {
                "date": date,
                "count": random.randint(1, 20),
                "spam_calls": random.randint(1, 10),
                "spam_messages": random.randint(5, 15),
                "malicious_content": random.randint(1, 8)
            } for date in dates
        ]
    
    return jsonify(stats)

@app.route('/api/threats/report', methods=['POST'])
def report_threat():
    """External API to report threats (e.g., from email services, phone companies)"""
    if not request.json:
        return jsonify({'success': False, 'error': 'Missing JSON data'}), 400
        
    content = request.json.get('content')
    source_info = request.json.get('source_info', {})
    api_key = request.headers.get('X-API-Key')
    
    # In production, validate API key here
    if not api_key:
        return jsonify({'success': False, 'error': 'Missing API key'}), 401
    
    # Process the threat
    result = threat_detector.detect_threats(content, source_info)
    
    if result["threats_detected"]:
        # If threat detected, notify connected clients
        notification = {
            "id": str(int(time.time() * 1000)),
            "timestamp": datetime.now().isoformat(),
            "message": f"Detected {list(result['categories'].keys())[0].replace('_', ' ')}",
            "severity": "high" if random.random() > 0.7 else "medium", 
            "details": result
        }
        
        socketio.emit('notification', {'type': 'notification', 'notification': notification})
        
    return jsonify({
        'success': True,
        'threat_detected': result["threats_detected"],
        'categories': result.get("categories", {})
    })

@app.route('/api/threats/recent')
def get_recent_threats():
    """Get recent threats for dashboard"""
    limit = int(request.args.get('limit', 10))
    
    # Get recent detection events
    detections = threat_detector.get_recent_detections(limit=limit)
    
    # Format for the table
    threats = []
    for detection in detections:
        if detection.get("threats_detected", False):
            threat_id = detection.get("id", str(uuid.uuid4()))
            threats.append({
                "id": threat_id,
                "timestamp": detection.get("timestamp", datetime.now().isoformat()),
                "categories": detection.get("categories", {}),
                "severity": detection.get("severity", "medium"),
                "source_info": detection.get("source_info", {}),
                "status": "Active"
            })
    
    return jsonify({"threats": threats})

@app.route('/api/threats/<threat_id>/block', methods=['POST'])
def block_threat_source(threat_id):
    """Block a threat source"""
    # In a real implementation, this would add the IP/source to a blocklist
    # For demo purposes, we just return success
    return jsonify({"success": True, "message": f"Source for threat {threat_id} has been blocked"})

@app.route('/test-notification')
def test_notification():
    """Test endpoint to manually trigger a notification"""
    notification = {
        "id": str(int(time.time() * 1000)),
        "timestamp": datetime.now().isoformat(),
        "message": "This is a test notification",
        "severity": request.args.get('severity', 'medium'),  # Can pass severity as query param
        "details": {
            "test": True,
            "source": "manual trigger"
        }
    }
    
    # Emit to all clients
    socketio.emit('notification', {'type': 'notification', 'notification': notification})
    
    return jsonify({
        'success': True,
        'message': 'Test notification sent'
    })

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    connected_clients.add(request.sid)
    print(f"Client connected: {request.sid}, Total: {len(connected_clients)}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    if request.sid in connected_clients:
        connected_clients.remove(request.sid)
        print(f"Client disconnected: {request.sid}, Total: {len(connected_clients)}")

@socketio.on('subscribe')
def handle_subscribe(data):
    """Handle channel subscription"""
    channel = data.get('channel')
    if channel:
        join_room(channel)
        print(f"Client {request.sid} subscribed to {channel}")

# Only use regular Flask app.run in development without sockets
if __name__ == "__main__":
    # For development with WebSockets, use socketio.run instead
    socketio.run(app, debug=True, host='127.0.0.1', port=5000, allow_unsafe_werkzeug=True)