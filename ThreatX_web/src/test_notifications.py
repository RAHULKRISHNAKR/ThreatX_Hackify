import requests
import time
import random

# Base URL of your Flask app
BASE_URL = "http://localhost:5000"

def test_notifications():
    """Generate a series of test notifications with different severities"""
    severities = ['low', 'medium', 'high', 'critical']
    
    for i in range(5):  # Generate 5 test notifications
        severity = random.choice(severities)
        print(f"Generating {severity} notification...")
        
        # Call the test-notification endpoint
        response = requests.get(f"{BASE_URL}/test-notification?severity={severity}")
        
        if response.status_code == 200:
            print(f"Notification {i+1} sent successfully: {response.json()}")
        else:
            print(f"Failed to send notification: {response.status_code}, {response.text}")
        
        # Wait a few seconds between notifications
        time.sleep(2)

if __name__ == "__main__":
    test_notifications()
    print("Test completed!")
