from app import app, socketio
import os

if __name__ == "__main__":
    # Get the host and port from environment or use defaults
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    
    # Start the Socket.IO server
    print(f"Starting ThreatX server on {host}:{port}...")
    socketio.run(app, host=host, port=port, debug=True, allow_unsafe_werkzeug=True)
