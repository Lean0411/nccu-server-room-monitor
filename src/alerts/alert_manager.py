"""
Alert management module for NCCU Server Room Monitor.

Handles alert creation, delivery, and management including
email notifications with attachments.
"""

import asyncio
import io
import logging
import smtplib
import zipfile
from datetime import datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from src.core.exceptions import AlertException, EmailException
from src.utils.logger import get_logger, log_audit_event


class AlertLevel:
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert:
    """Represents a single alert."""
    
    def __init__(
        self,
        alert_type: str,
        message: str,
        level: str = AlertLevel.WARNING,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize alert.
        
        Args:
            alert_type: Type of alert
            message: Alert message
            level: Alert severity level
            source: Source of the alert
            metadata: Additional alert metadata
        """
        self.alert_id = self._generate_id()
        self.alert_type = alert_type
        self.message = message
        self.level = level
        self.source = source or "system"
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.sent = False
        self.sent_time: Optional[datetime] = None
        self.recipients: List[str] = []
        self.error: Optional[str] = None
        
    def _generate_id(self) -> str:
        """Generate unique alert ID."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "message": self.message,
            "level": self.level,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "sent": self.sent,
            "sent_time": self.sent_time.isoformat() if self.sent_time else None,
            "recipients": self.recipients,
            "metadata": self.metadata,
            "error": self.error
        }


class EmailSender:
    """Handles email sending for alerts."""
    
    def __init__(self, config: Any):
        """Initialize email sender.
        
        Args:
            config: Configuration object with SMTP settings
        """
        self.config = config
        self.logger = get_logger(__name__)
        
    async def send_email(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        attachments: Optional[List[bytes]] = None
    ) -> bool:
        """Send email alert.
        
        Args:
            recipients: List of email recipients
            subject: Email subject
            body: Email body
            attachments: Optional list of attachment data
            
        Returns:
            True if email sent successfully
        """
        try:
            msg = MIMEMultipart()
            msg["From"] = self.config.smtp.user
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject
            
            # Add body
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            # Add attachments
            if attachments:
                self._add_attachments(msg, attachments)
            
            # Send email
            await self._send_smtp(msg, recipients)
            
            self.logger.info(f"Email sent successfully to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            raise EmailException(f"Email sending failed: {e}", recipients=recipients)
    
    def _add_attachments(self, msg: MIMEMultipart, attachments: List[bytes]):
        """Add attachments to email.
        
        Args:
            msg: Email message object
            attachments: List of attachment data
        """
        # Create ZIP file with images
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, data in enumerate(attachments):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"alert_image_{i:03d}_{timestamp}.jpg"
                zf.writestr(filename, data)
        
        zip_buffer.seek(0)
        
        # Attach ZIP file
        part = MIMEBase("application", "zip")
        part.set_payload(zip_buffer.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename=alert_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        )
        msg.attach(part)
    
    async def _send_smtp(self, msg: MIMEMultipart, recipients: List[str]):
        """Send email via SMTP.
        
        Args:
            msg: Email message
            recipients: List of recipients
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._send_smtp_sync,
            msg,
            recipients
        )
    
    def _send_smtp_sync(self, msg: MIMEMultipart, recipients: List[str]):
        """Synchronous SMTP sending.
        
        Args:
            msg: Email message
            recipients: List of recipients
        """
        with smtplib.SMTP(self.config.smtp.host, self.config.smtp.port) as server:
            if self.config.smtp.use_tls:
                server.starttls()
            server.login(
                self.config.smtp.user,
                self.config.smtp.password.get_secret_value()
            )
            server.send_message(msg, to_addrs=recipients)


class AlertManager:
    """Manages alert creation, delivery, and tracking."""
    
    def __init__(self, config: Any):
        """Initialize alert manager.
        
        Args:
            config: System configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.email_sender = EmailSender(config)
        
        # Alert tracking
        self.alerts: List[Alert] = []
        self.cooldowns: Dict[str, datetime] = {}
        self.alert_counts: Dict[str, int] = {}
        
        # Alert queue
        self.alert_queue: asyncio.Queue = asyncio.Queue()
        self.processing = False
        
    async def send_alert(
        self,
        alert_type: str,
        message: str,
        level: str = AlertLevel.WARNING,
        images: Optional[List[bytes]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send an alert.
        
        Args:
            alert_type: Type of alert
            message: Alert message
            level: Alert severity
            images: Optional images to attach
            metadata: Optional metadata
            
        Returns:
            True if alert sent successfully
        """
        # Check cooldown
        if not self._check_cooldown(alert_type):
            self.logger.info(f"Alert {alert_type} in cooldown period")
            return False
        
        # Create alert
        alert = Alert(
            alert_type=alert_type,
            message=message,
            level=level,
            metadata=metadata
        )
        
        try:
            # Get recipients based on alert level
            recipients = self._get_recipients(level)
            if not recipients:
                self.logger.warning("No alert recipients configured")
                return False
            
            # Prepare email
            subject = self._format_subject(alert)
            body = self._format_body(alert)
            
            # Send email
            success = await self.email_sender.send_email(
                recipients=recipients,
                subject=subject,
                body=body,
                attachments=images if self.config.alerts.include_images else None
            )
            
            if success:
                alert.sent = True
                alert.sent_time = datetime.now()
                alert.recipients = recipients
                
                # Update cooldown
                self.cooldowns[alert_type] = datetime.now()
                
                # Update statistics
                self.alert_counts[alert_type] = self.alert_counts.get(alert_type, 0) + 1
                
                # Log audit event
                log_audit_event(
                    event_type="alert_sent",
                    details={
                        "alert_type": alert_type,
                        "level": level,
                        "recipients": len(recipients)
                    }
                )
            else:
                alert.error = "Failed to send email"
            
            # Store alert
            self.alerts.append(alert)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
            alert.error = str(e)
            self.alerts.append(alert)
            return False
    
    def _check_cooldown(self, alert_type: str) -> bool:
        """Check if alert type is in cooldown.
        
        Args:
            alert_type: Type of alert
            
        Returns:
            True if alert can be sent
        """
        last_sent = self.cooldowns.get(alert_type)
        if not last_sent:
            return True
        
        cooldown_delta = timedelta(minutes=self.config.alerts.cooldown_minutes)
        return datetime.now() - last_sent >= cooldown_delta
    
    def _get_recipients(self, level: str) -> List[str]:
        """Get recipients based on alert level.
        
        Args:
            level: Alert level
            
        Returns:
            List of email addresses
        """
        # For now, return all configured recipients
        # Could be extended to have different recipients per level
        return self.config.alerts.recipients
    
    def _format_subject(self, alert: Alert) -> str:
        """Format email subject.
        
        Args:
            alert: Alert object
            
        Returns:
            Formatted subject
        """
        # 根據警報等級設定主旨前綴
        level_prefix = {
            AlertLevel.INFO: "[INFO]",
            AlertLevel.WARNING: "[WARNING]",
            AlertLevel.ERROR: "[ERROR]",
            AlertLevel.CRITICAL: "[CRITICAL]"
        }
        
        prefix = level_prefix.get(alert.level, "[ALERT]")
        return f"{prefix} NCCU Monitor - {alert.alert_type}"
    
    def _format_body(self, alert: Alert) -> str:
        """Format email body.
        
        Args:
            alert: Alert object
            
        Returns:
            Formatted body
        """
        body = f"""
NCCU Server Room Monitoring System Alert
{'=' * 50}

Alert Type: {alert.alert_type}
Severity: {alert.level.upper()}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Source: {alert.source}

Message:
{alert.message}

{'=' * 50}
Location: NCCU Building 1F Server Room
System: Monitoring System v2.0

Action Required: Please investigate this alert immediately.

Contact:
- IT Department: (02) 2939-3091
- Emergency: 0958-242-580

{'=' * 50}
This is an automated message from the NCCU monitoring system.
        """
        
        # Add metadata if present
        if alert.metadata:
            body += "\n\nAdditional Information:\n"
            for key, value in alert.metadata.items():
                body += f"  {key}: {value}\n"
        
        return body.strip()
    
    def get_alert_history(
        self,
        limit: Optional[int] = None,
        alert_type: Optional[str] = None,
        level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get alert history.
        
        Args:
            limit: Maximum number of alerts to return
            alert_type: Filter by alert type
            level: Filter by alert level
            
        Returns:
            List of alert dictionaries
        """
        alerts = self.alerts
        
        # Apply filters
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        
        # Apply limit
        if limit:
            alerts = alerts[:limit]
        
        return [alert.to_dict() for alert in alerts]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics.
        
        Returns:
            Dictionary of statistics
        """
        total_alerts = len(self.alerts)
        sent_alerts = sum(1 for a in self.alerts if a.sent)
        failed_alerts = total_alerts - sent_alerts
        
        # Count by level
        level_counts = {}
        for alert in self.alerts:
            level_counts[alert.level] = level_counts.get(alert.level, 0) + 1
        
        # Count by type
        type_counts = dict(self.alert_counts)
        
        # Recent alerts (last 24 hours)
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_alerts = sum(1 for a in self.alerts if a.timestamp >= recent_cutoff)
        
        return {
            "total_alerts": total_alerts,
            "sent_alerts": sent_alerts,
            "failed_alerts": failed_alerts,
            "recent_alerts_24h": recent_alerts,
            "alerts_by_level": level_counts,
            "alerts_by_type": type_counts,
            "cooldowns": {
                k: v.isoformat() for k, v in self.cooldowns.items()
            }
        }
    
    def clear_old_alerts(self, days: int = 7):
        """Clear alerts older than specified days.
        
        Args:
            days: Number of days to keep
        """
        cutoff = datetime.now() - timedelta(days=days)
        original_count = len(self.alerts)
        
        self.alerts = [
            alert for alert in self.alerts
            if alert.timestamp >= cutoff
        ]
        
        removed = original_count - len(self.alerts)
        if removed > 0:
            self.logger.info(f"Cleared {removed} old alerts")
    
    def export_alerts(self, filepath: Path):
        """Export alerts to JSON file.
        
        Args:
            filepath: Path to export file
        """
        alerts_data = [alert.to_dict() for alert in self.alerts]
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(alerts_data, f, indent=2, default=str)
        
        self.logger.info(f"Exported {len(alerts_data)} alerts to {filepath}")