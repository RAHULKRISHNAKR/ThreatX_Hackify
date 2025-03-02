import re
import json
import logging
import time
from datetime import datetime
from collections import defaultdict, deque
from threading import Lock
import numpy as np
from hackbot.alert_system import send_email_alert, send_sms_alert, log_threat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="threat_detector.log"
)
logger = logging.getLogger("ThreatDetector")

class ThreatDetector:
    def __init__(self):
        self.threat_patterns = {
            "spam_call": [
                r"warranty",
                r"insurance claim",
                r"credit card service",
                r"tax department",
                r"\+?1?-?\d{3}-?\d{3}-?\d{4}"  # Phone number pattern
            ],
            "spam_sms": [
                r"click here",
                r"urgent",
                r"you've won",
                r"free",
                r"prize",
                r"congrats",
                r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"  # URL pattern
            ],
            "spam_email": [
                r"unsubscribe",
                r"million dollars",
                r"lottery",
                r"inheritance",
                r"investment opportunity",
                r"bank transfer"
            ],
            "malicious_content": [
                r"<script>.*?</script>",
                r"eval\s*\(",
                r"exec\s*\(",
                r"document\.cookie",
                r"DROP TABLE",
                r"SELECT.*?FROM",
                r"(?:\'|\"|\)|\}|\]|\||\<|\>|\\|\s)\s*OR\s+[\'|\"]?\s*[0-9a-zA-Z_]+\s*[\'|\"]?\s*=\s*[\'|\"]?\s*[0-9a-zA-Z_]+",  # SQL injection
                r"[\w\.-]+@[\w\.-]+"  # Email pattern (could be leaked)
            ]
        }
        
        # Frequency analysis
        self.ip_frequency = defaultdict(lambda: deque(maxlen=1000))
        self.content_frequency = defaultdict(int)
        self.frequency_lock = Lock()
        
        # Detection history
        self.detection_history = deque(maxlen=1000)
        self.notifications = []
        
        # Load known threats from database or file
        self.known_malicious_ips = self._load_known_threats('ip_blocklist.json')
        self.known_malicious_domains = self._load_known_threats('domain_blocklist.json')
        
        logger.info("ThreatDetector initialized")
    
    def _load_known_threats(self, filename):
        try:
            with open(filename, 'r') as f:
                return set(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            return set()
    
    def detect_threats(self, content, source_info=None):
        """
        Analyze content for potential threats
        
        Args:
            content (str): The content to analyze
            source_info (dict): Source information like IP, user agent, etc.
            
        Returns:
            dict: Detection results with threat categories and confidence scores
        """
        if not content:
            return {"threats_detected": False}
        
        content = str(content).lower()
        result = {
            "threats_detected": False,
            "categories": {},
            "timestamp": datetime.now().isoformat(),
            "source_info": source_info or {}
        }
        
        # Check for threats in each category
        for category, patterns in self.threat_patterns.items():
            category_score = 0
            matches = []
            
            for pattern in patterns:
                found = re.findall(pattern, content, re.IGNORECASE)
                if found:
                    matches.extend(found)
                    category_score += len(found) * 0.2  # Increase score for each match
            
            if matches:
                result["threats_detected"] = True
                result["categories"][category] = {
                    "confidence": min(category_score, 1.0),  # Cap at 1.0
                    "matches": matches[:5]  # Limit to 5 matches for brevity
                }
        
        # Check source against known threats
        if source_info:
            if source_info.get("ip") in self.known_malicious_ips:
                result["threats_detected"] = True
                result["categories"]["known_malicious_ip"] = {
                    "confidence": 1.0,
                    "matches": [source_info.get("ip")]
                }
            
            source_domain = source_info.get("domain")
            if source_domain and any(domain in source_domain for domain in self.known_malicious_domains):
                result["threats_detected"] = True
                result["categories"]["known_malicious_domain"] = {
                    "confidence": 1.0,
                    "matches": [source_domain]
                }
        
        # Record detection for frequency analysis
        if result["threats_detected"]:
            self._record_detection(result)
            
            # Send alerts for high confidence threats
            max_confidence = max([info["confidence"] for info in result["categories"].values()], default=0)
            if max_confidence > 0.7:
                self._trigger_alerts(result)
        
        return result
    
    def _record_detection(self, detection_result):
        """Record detection for pattern analysis and add to history"""
        source_ip = detection_result.get("source_info", {}).get("ip")
        
        if source_ip:
            with self.frequency_lock:
                self.ip_frequency[source_ip].append(time.time())
                
                # Check for suspicious frequency
                if len(self.ip_frequency[source_ip]) >= 5:
                    # If 5 or more requests in last 60 seconds from same IP
                    recent_count = sum(1 for t in self.ip_frequency[source_ip] 
                                      if time.time() - t < 60)
                    if recent_count >= 5:
                        detection_result["categories"]["suspicious_frequency"] = {
                            "confidence": min(recent_count / 10, 1.0),
                            "matches": [f"{recent_count} requests in last minute"]
                        }
        
        # Add to detection history
        self.detection_history.append(detection_result)
        
        # Create notification
        notification = {
            "id": str(int(time.time() * 1000)),
            "timestamp": detection_result["timestamp"],
            "message": self._create_notification_message(detection_result),
            "severity": self._calculate_severity(detection_result),
            "read": False
        }
        self.notifications.append(notification)
        
        return notification
    
    def _create_notification_message(self, detection):
        """Create a human-readable notification message"""
        categories = list(detection["categories"].keys())
        source = detection.get("source_info", {})
        source_info = f" from {source.get('ip', 'unknown IP')}" if source.get("ip") else ""
        
        if len(categories) == 1:
            return f"{categories[0].replace('_', ' ').title()} detected{source_info}"
        else:
            return f"Multiple threats detected ({', '.join(categories)}){source_info}"
    
    def _calculate_severity(self, detection):
        """Calculate severity level based on threat types and confidence"""
        max_confidence = max([info["confidence"] for info in detection["categories"].values()], default=0)
        
        if "malicious_content" in detection["categories"] and max_confidence > 0.7:
            return "critical"
        elif max_confidence > 0.8 or len(detection["categories"]) >= 2:
            return "high"
        elif max_confidence > 0.5:
            return "medium"
        else:
            return "low"
    
    def _trigger_alerts(self, detection):
        """Trigger appropriate alerts based on detection"""
        severity = self._calculate_severity(detection)
        message = self._create_notification_message(detection)
        category = next(iter(detection["categories"].keys()))
        
        # Log all threats
        log_threat(category, message)
        
        # Send email for high severity threats
        if severity in ("high", "critical"):
            send_email_alert(
                subject=f"{severity.upper()}: {message}",
                body=json.dumps(detection, indent=2)
            )
        
        # Send SMS only for critical threats
        if severity == "critical":
            send_sms_alert(message)
    
    def get_recent_detections(self, limit=50):
        """Get recent detection events"""
        return list(self.detection_history)[-limit:]
    
    def get_notifications(self, since_id=None, limit=20, include_read=False):
        """Get notifications, optionally filtering by ID and read status"""
        filtered = self.notifications
        
        if since_id:
            filtered = [n for n in filtered if int(n["id"]) > int(since_id)]
            
        if not include_read:
            filtered = [n for n in filtered if not n["read"]]
            
        return filtered[-limit:]
    
    def mark_notification_read(self, notification_id):
        """Mark a notification as read"""
        for notification in self.notifications:
            if notification["id"] == notification_id:
                notification["read"] = True
                return True
        return False
    
    def calculate_threat_statistics(self):
        """Calculate threat statistics for dashboard"""
        if not self.detection_history:
            return {
                "total_threats": 0,
                "by_category": {},
                "by_severity": {},
                "recent_trend": []
            }
            
        # Group by day for the trend (last 7 days)
        now = datetime.now()
        day_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        category_counts = defaultdict(int)
        
        for detection in self.detection_history:
            try:
                dt = datetime.fromisoformat(detection["timestamp"])
                day = dt.strftime("%Y-%m-%d")
                day_counts[day] += 1
                
                severity = self._calculate_severity(detection)
                severity_counts[severity] += 1
                
                for category in detection["categories"].keys():
                    category_counts[category] += 1
            except (ValueError, TypeError, KeyError):
                continue
        
        # Format trend data
        trend_days = sorted(day_counts.keys())[-7:]
        trend = [{"date": day, "count": day_counts.get(day, 0)} for day in trend_days]
        
        return {
            "total_threats": len(self.detection_history),
            "by_category": dict(category_counts),
            "by_severity": dict(severity_counts),
            "recent_trend": trend
        }

# Make sure this file is properly imported in your app.py
# At the top of your app.py, make sure you have:
# from hackbot.threat_detector import threat_detector

# This class will be a simple version if the full version is not working properly
class SimpleThreatDetector:
    def __init__(self):
        self.notifications = []
        
    def detect_threats(self, content, source_info=None):
        """Basic threat detection"""
        threats_detected = False
        categories = {}
        
        # Check for spam patterns
        spam_keywords = ["free", "win", "prize", "click here", "urgent", "warranty", "congrats", "claim", "credit card"]
        for keyword in spam_keywords:
            if keyword.lower() in content.lower():
                threats_detected = True
                categories["spam"] = {
                    "confidence": 0.8,
                    "matches": [keyword]
                }
                break
        
        # Check for malicious code patterns
        code_patterns = ["<script>", "document.cookie", "eval(", "DROP TABLE", "SELECT", "1=1", "OR 1=1"]
        for pattern in code_patterns:
            if pattern.lower() in content.lower():
                threats_detected = True
                categories["malicious_content"] = {
                    "confidence": 0.9,
                    "matches": [pattern]
                }
                break
        
        result = {
            "threats_detected": threats_detected,
            "categories": categories,
            "timestamp": datetime.now().isoformat(),
            "source_info": source_info or {}
        }
        
        # If threats detected, store as a notification
        if threats_detected:
            notification = {
                "id": str(int(time.time() * 1000)),
                "timestamp": datetime.now().isoformat(),
                "message": f"Detected {list(categories.keys())[0]}",
                "severity": "high" if categories.get("malicious_content") else "medium",
                "details": result
            }
            self.notifications.append(notification)
        
        return result
    
    def get_notifications(self, since_id=None, limit=20, include_read=False):
        """Get recent notifications"""
        result = self.notifications
        
        if since_id:
            result = [n for n in result if n["id"] > since_id]
        
        return result[-limit:]
    
    def mark_notification_read(self, notification_id):
        """Mark notification as read (dummy implementation)"""
        return True
    
    def get_recent_detections(self, limit=50):
        """Get recent detections"""
        return self.notifications[-limit:]
    
    def calculate_threat_statistics(self):
        """Calculate statistics"""
        return {
            "total_threats": len(self.notifications),
            "by_category": {"spam": 0, "malicious_content": 0},
            "by_severity": {"low": 0, "medium": 0, "high": 0},
            "recent_trend": []
        }

# Create a global instance for use in the app
threat_detector = SimpleThreatDetector()
