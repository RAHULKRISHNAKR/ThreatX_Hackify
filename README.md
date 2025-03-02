# ThreatX Spam and Malicious Content Detection

## Overview

ThreatX is a real-time threat detection and prevention platform that protects users from:
- Spam calls
- Spam SMS messages
- Phishing emails
- Malicious content in messages and websites

The platform uses AI-powered analysis to detect threats and alert users in real-time, helping prevent cybercrime before it affects users.

## Features

- **Real-time threat detection** - Monitor and analyze incoming communications instantaneously
- **Spam call blocking** - Identify and alert about potential fraudulent calls
- **SMS/Message filtering** - Detect phishing attempts and scam messages
- **Email protection** - Flag suspicious emails and identify phishing attempts
- **Content analysis** - Scan websites and message content for malicious code or scams
- **Security dashboard** - Monitor threats and view analytics in a comprehensive dashboard
- **AI chatbot** - Get cybersecurity advice and report suspicious activity through a conversational interface

## Setup Instructions

### Prerequisites

- Python 3.8+
- Flask
- Socket.IO support
- Google Gemini API key (for AI responses)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/username/ThreatX_Hackify.git
   cd ThreatX_Hackify
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Create a `.env` file in the root directory
   - Add the following variables:
     ```
     GEMINI_API_KEY=your_api_key_here
     AI_OPTION=GEMINI
     ```

4. Run the application:
   ```bash
   cd ThreatX_web/src
   python app.py
   ```

5. Open your browser and navigate to `http://localhost:5000`

## Usage

### Chatbot Interface

The chatbot provides a user-friendly interface to:
- Report suspicious messages or calls
- Get advice on cybersecurity issues
- Check if a link or message is potentially malicious

### Real-time Notifications

The system alerts you about:
- Incoming spam calls
- Suspicious SMS messages
- Phishing email attempts
- Malicious content in websites or messages

### Security Dashboard

The dashboard provides:
- Overview of detected threats
- Threat statistics and trends
- Detailed threat information
- Source blocking capabilities

## API Reference

### Threat Detection API

```
POST /api/threats/report
```

Report external threats to the system.

**Request Body:**
```json
{
  "content": "The message or content to analyze",
  "source_info": {
    "ip": "192.168.1.1",
    "phone": "+1234567890",
    "email": "example@domain.com"
  }
}
```

**Headers:**
- `X-API-Key`: Your API key for authentication

**Response:**
```json
{
  "success": true,
  "threat_detected": true,
  "categories": {
    "spam_sms": {
      "confidence": 0.95,
      "matches": ["free", "click here"]
    }
  }
}
```

## Contributing

Contributions to ThreatX are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.