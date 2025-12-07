import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..config.database import get_db_cursor, get_schema_name
from ..services.email_service import email_service
import os

logger = logging.getLogger(__name__)
SCHEMA = get_schema_name()

class AlertService:
    """Service for managing GPU memory alerts with cooldown periods"""
    
    def __init__(self):
        """Initialize alert service with configurable cooldown period"""
        # Get cooldown period from environment variable (default: 5 minutes)
        self.cooldown_minutes = int(os.getenv('ALERT_COOLDOWN_MINUTES', '5'))
        logger.info(f"Alert service initialized with {self.cooldown_minutes} minute cooldown period")
    
    def check_and_send_alerts(
        self,
        server_id: int,
        server_name: str,
        server_ip: str,
        gpu_index: int,
        gpu_name: str,
        gpu_memory_used_mib: int,
        gpu_memory_total_mib: int,
        usage_limit: int,
        alert_emails: List[str]
    ) -> bool:
        """
        Check if alert should be sent and send if conditions are met
        
        Args:
            server_id: GPU server database ID
            server_name: Name of the server
            server_ip: IP address of the server
            gpu_index: GPU index number
            gpu_name: GPU model name
            gpu_memory_used_mib: Current GPU memory used in MiB
            gpu_memory_total_mib: Total GPU memory in MiB
            usage_limit: Alert threshold percentage (0-100)
            alert_emails: List of email addresses to notify
            
        Returns:
            bool: True if alert was sent, False otherwise
        """
        # Calculate current usage percentage
        if gpu_memory_total_mib <= 0:
            logger.warning(f"Invalid GPU memory total: {gpu_memory_total_mib}")
            return False
        
        current_usage_pct = (gpu_memory_used_mib / gpu_memory_total_mib) * 100
        
        # Check if usage exceeds limit
        if current_usage_pct < usage_limit:
            logger.debug(f"GPU {gpu_index} usage ({current_usage_pct:.1f}%) below threshold ({usage_limit}%)")
            return False
        
        logger.info(f"GPU {gpu_index} on {server_name} usage ({current_usage_pct:.1f}%) exceeds threshold ({usage_limit}%)")
        
        # Check cooldown period
        if self._is_in_cooldown(server_id, gpu_index):
            logger.info(f"Alert in cooldown period for {server_name} GPU {gpu_index}")
            return False
        
        # Send alert email
        success = email_service.send_gpu_memory_alert(
            server_name=server_name,
            server_ip=server_ip,
            gpu_index=gpu_index,
            gpu_name=gpu_name,
            current_usage_pct=current_usage_pct,
            usage_limit=usage_limit,
            memory_used_mib=gpu_memory_used_mib,
            memory_total_mib=gpu_memory_total_mib,
            recipient_emails=alert_emails
        )
        
        if success:
            # Record alert in database
            self._record_alert(
                server_id=server_id,
                gpu_index=gpu_index,
                usage_pct=current_usage_pct,
                memory_used_mib=gpu_memory_used_mib,
                memory_total_mib=gpu_memory_total_mib,
                threshold_pct=usage_limit,
                recipient_emails=alert_emails
            )
            logger.info(f"Alert sent successfully for {server_name} GPU {gpu_index}")
        
        return success
    
    def _is_in_cooldown(self, server_id: int, gpu_index: int) -> bool:
        """
        Check if an alert for this server/GPU is in cooldown period
        
        Args:
            server_id: GPU server database ID
            gpu_index: GPU index number
            
        Returns:
            bool: True if in cooldown, False otherwise
        """
        try:
            cooldown_threshold = datetime.now() - timedelta(minutes=self.cooldown_minutes)
            
            query = f"""
                SELECT sent_at
                FROM {SCHEMA}.gpu_alert_history
                WHERE server_id = %s AND gpu_index = %s
                ORDER BY sent_at DESC
                LIMIT 1
            """
            
            with get_db_cursor() as cursor:
                cursor.execute(query, (server_id, gpu_index))
                result = cursor.fetchone()
                
                if result:
                    last_alert_time = result['sent_at']
                    if last_alert_time > cooldown_threshold:
                        remaining_seconds = (last_alert_time - cooldown_threshold).total_seconds()
                        logger.debug(f"Cooldown active: {remaining_seconds:.0f} seconds remaining")
                        return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error checking cooldown: {e}", exc_info=True)
            # On error, assume no cooldown to avoid missing critical alerts
            return False
    
    def _record_alert(
        self,
        server_id: int,
        gpu_index: int,
        usage_pct: float,
        memory_used_mib: int,
        memory_total_mib: int,
        threshold_pct: int,
        recipient_emails: List[str]
    ) -> Optional[int]:
        """
        Record alert in database
        
        Args:
            server_id: GPU server database ID
            gpu_index: GPU index number
            usage_pct: Usage percentage at time of alert
            memory_used_mib: Memory used in MiB
            memory_total_mib: Total memory in MiB
            threshold_pct: Alert threshold percentage
            recipient_emails: List of recipients
            
        Returns:
            Optional[int]: Alert ID if successful, None otherwise
        """
        try:
            import json
            
            query = f"""
                INSERT INTO {SCHEMA}.gpu_alert_history 
                (server_id, gpu_index, usage_pct, memory_used_mib, memory_total_mib, 
                 threshold_pct, recipient_emails, sent_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            with get_db_cursor(commit=True) as cursor:
                cursor.execute(query, (
                    server_id,
                    gpu_index,
                    round(usage_pct, 2),
                    memory_used_mib,
                    memory_total_mib,
                    threshold_pct,
                    json.dumps(recipient_emails),
                    datetime.now()
                ))
                result = cursor.fetchone()
                return result['id'] if result else None
                
        except Exception as e:
            logger.error(f"Error recording alert: {e}", exc_info=True)
            return None
    
    def get_alert_history(
        self,
        server_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get alert history, optionally filtered by server
        
        Args:
            server_id: Optional server ID to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of alert history records
        """
        try:
            if server_id:
                query = f"""
                    SELECT ah.*, gs.server_name, gs.server_ip
                    FROM {SCHEMA}.gpu_alert_history ah
                    JOIN {SCHEMA}.gpu_server gs ON ah.server_id = gs.id
                    WHERE ah.server_id = %s
                    ORDER BY ah.sent_at DESC
                    LIMIT %s
                """
                params = (server_id, limit)
            else:
                query = f"""
                    SELECT ah.*, gs.server_name, gs.server_ip
                    FROM {SCHEMA}.gpu_alert_history ah
                    JOIN {SCHEMA}.gpu_server gs ON ah.server_id = gs.id
                    ORDER BY ah.sent_at DESC
                    LIMIT %s
                """
                params = (limit,)
            
            with get_db_cursor() as cursor:
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error fetching alert history: {e}", exc_info=True)
            return []

# Global instance
alert_service = AlertService()

