import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
import logging

# Configuration
EMAIL_SENDER = "your_email@example.com"
EMAIL_PASSWORD = "your_email_password"
EMAIL_RECEIVER = "admin@example.com"

TWILIO_ACCOUNT_SID = "your_twilio_account_sid"
TWILIO_AUTH_TOKEN = "your_twilio_auth_token"
TWILIO_PHONE_NUMBER = "+1234567890"  # Your Twilio number
ADMIN_PHONE_NUMBER = "+0987654321"   # Admin phone number

# Logging setup
logging.basicConfig(filename="security_alerts.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Spam detection logic
def detect_spam(message):
    spam_keywords = ["free", "win", "prize", "click here", "urgent"]
    if any(keyword in message.lower() for keyword in spam_keywords):
        return True
    return False

# Hacking detection logic
def detect_hacking_attempt(message):
    hacking_patterns = ["' OR '1'='1", "<script>", "DROP TABLE", "UNION SELECT"]
    if any(pattern in message for pattern in hacking_patterns):
        return True
    return False

# Email alert function
def send_email_alert(subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        logging.info("Email alert sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send email alert: {e}")

# SMS alert function (using Twilio)
def send_sms_alert(message):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=f"ALERT: {message}",
            from_=TWILIO_PHONE_NUMBER,
            to=ADMIN_PHONE_NUMBER
        )
        logging.info("SMS alert sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send SMS alert: {e}")

# Log threat function
def log_threat(threat_type, message):
    logging.warning(f"{threat_type} detected: {message}")

# Main function to test the alert system
def test_alert_system():
    print("Testing the alert system. Enter messages to check for spam or hacking attempts.")
    while True:
        user_message = input("Enter a message (or type 'exit' to quit): ")
        if user_message.lower() == "exit":
            break

        if detect_spam(user_message):
            print("Spam detected!")
            log_threat("Spam", user_message)
            send_email_alert("Spam Detected", f"Spam message: {user_message}")
            send_sms_alert(f"Spam detected: {user_message}")

        if detect_hacking_attempt(user_message):
            print("Hacking attempt detected!")
            log_threat("Hacking Attempt", user_message)
            send_email_alert("Hacking Attempt Detected", f"Hacking attempt: {user_message}")
            send_sms_alert(f"Hacking attempt detected: {user_message}")

        print("Message processed. No threats detected.")

if __name__ == "__main__":
    test_alert_system()