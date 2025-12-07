from ..config.database import get_db_cursor, get_schema_name
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import os
import logging

# Get schema name from config
SCHEMA = get_schema_name()
logger = logging.getLogger(__name__)

class URLModel:
    @staticmethod
    def create(url_data: dict) -> dict:
        """Create a new URL"""
        import json
        
        # Convert alert_emails list to JSON
        alert_emails = url_data.get('alert_emails', [])
        if isinstance(alert_emails, str):
            alert_emails = [alert_emails] if alert_emails else []
        
        query = f"""
            INSERT INTO {SCHEMA}.urls (project_name, url, environment, project_category,
                            server_id, health_check_status, description, alert_emails)
            VALUES (%(project_name)s, %(url)s, %(environment)s, %(project_category)s,
                    %(server_id)s, COALESCE(%(health_check_status)s, 'YES'), %(description)s, %(alert_emails)s::jsonb)
            RETURNING id, project_name, url, environment, project_category,
                      server_id, health_check_status, description, alert_emails, created_at, updated_at
        """
        url_data['alert_emails'] = json.dumps(alert_emails)
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, url_data)
            return dict(cursor.fetchone())

    @staticmethod
    def get_all() -> List[dict]:
        """Get all URLs"""
        query = f"SELECT * FROM {SCHEMA}.urls ORDER BY created_at DESC"
        with get_db_cursor() as cursor:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(url_id: int) -> Optional[dict]:
        """Get URL by ID"""
        query = f"SELECT * FROM {SCHEMA}.urls WHERE id = %s"
        with get_db_cursor() as cursor:
            cursor.execute(query, (url_id,))
            result = cursor.fetchone()
            return dict(result) if result else None

    @staticmethod
    def get_by_environment(environment: str) -> List[dict]:
        """Get URLs by environment"""
        query = f"SELECT * FROM {SCHEMA}.urls WHERE environment = %s ORDER BY project_name"
        with get_db_cursor() as cursor:
            cursor.execute(query, (environment,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def update(url_id: int, url_data: dict) -> Optional[dict]:
        """Update URL"""
        import json
        
        # Convert alert_emails list to JSON if present
        if 'alert_emails' in url_data:
            alert_emails = url_data.get('alert_emails', [])
            if isinstance(alert_emails, str):
                alert_emails = [alert_emails] if alert_emails else []
            url_data['alert_emails'] = json.dumps(alert_emails)
        
        query = f"""
            UPDATE {SCHEMA}.urls
            SET project_name = %(project_name)s,
                url = %(url)s,
                environment = %(environment)s,
                project_category = %(project_category)s,
                server_id = %(server_id)s,
                health_check_status = COALESCE(%(health_check_status)s, health_check_status),
                description = %(description)s,
                alert_emails = COALESCE(%(alert_emails)s::jsonb, alert_emails)
            WHERE id = %(id)s
            RETURNING id, project_name, url, environment, project_category,
                      server_id, health_check_status, description, alert_emails, created_at, updated_at
        """
        url_data['id'] = url_id
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, url_data)
            result = cursor.fetchone()
            return dict(result) if result else None

    @staticmethod
    def delete(url_id: int) -> bool:
        """Delete URL"""
        query = f"DELETE FROM {SCHEMA}.urls WHERE id = %s RETURNING id"
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, (url_id,))
            return cursor.fetchone() is not None
    
    @staticmethod
    def toggle_health_check(url_id: int, status: str) -> Optional[dict]:
        """Toggle health check status for a URL (YES/NO)"""
        if status not in ['YES', 'NO']:
            raise ValueError("Health check status must be 'YES' or 'NO'")
        
        query = f"""
            UPDATE {SCHEMA}.urls
            SET health_check_status = %s
            WHERE id = %s
            RETURNING id, project_name, url, environment, project_category,
                      server_id, health_check_status, description, alert_emails, created_at, updated_at
        """
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, (status, url_id))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    @staticmethod
    def update_alert_emails(url_id: int, alert_emails: List[str]) -> Optional[dict]:
        """Update alert emails for a URL"""
        import json
        
        query = f"""
            UPDATE {SCHEMA}.urls
            SET alert_emails = %s::jsonb, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, project_name, url, environment, project_category,
                      server_id, health_check_status, description, alert_emails, created_at, updated_at
        """
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, (json.dumps(alert_emails), url_id))
            result = cursor.fetchone()
            return dict(result) if result else None


class HealthStatusModel:
    @staticmethod
    def create(health_data: dict) -> dict:
        """Create health status record"""
        query = f"""
            INSERT INTO {SCHEMA}.health_status (url_id, status, response_time, status_code, error_message)
            VALUES (%(url_id)s, %(status)s, %(response_time)s, %(status_code)s, %(error_message)s)
            RETURNING id, url_id, status, response_time, status_code, error_message, checked_at
        """
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, health_data)
            return dict(cursor.fetchone())

    @staticmethod
    def get_latest_by_url(url_id: int) -> Optional[dict]:
        """Get latest health status for a URL"""
        query = f"""
            SELECT * FROM {SCHEMA}.health_status 
            WHERE url_id = %s 
            ORDER BY checked_at DESC 
            LIMIT 1
        """
        with get_db_cursor() as cursor:
            cursor.execute(query, (url_id,))
            result = cursor.fetchone()
            return dict(result) if result else None

    @staticmethod
    def get_history(url_id: int, minutes: int = 20) -> List[dict]:
        """Get health status history for last N minutes"""
        query = f"""
            SELECT * FROM {SCHEMA}.health_status 
            WHERE url_id = %s 
            AND checked_at >= NOW() - INTERVAL '%s minutes'
            ORDER BY checked_at DESC
        """
        with get_db_cursor() as cursor:
            cursor.execute(query, (url_id, minutes))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_all_latest() -> List[dict]:
        """Get latest health status for all URLs"""
        query = f"""
            SELECT DISTINCT ON (url_id) *
            FROM {SCHEMA}.health_status
            ORDER BY url_id, checked_at DESC
        """
        with get_db_cursor() as cursor:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]


class ProjectModel:
    @staticmethod
    def create(name: str) -> dict:
        """Create a new project"""
        query = f"""
            INSERT INTO {SCHEMA}.projects (name)
            VALUES (%s)
            ON CONFLICT (name) DO NOTHING
            RETURNING id, name, created_at
        """
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, (name,))
            result = cursor.fetchone()
            if result:
                return dict(result)
            # If conflict, fetch existing
            cursor.execute(f"SELECT * FROM {SCHEMA}.projects WHERE name = %s", (name,))
            return dict(cursor.fetchone())

    @staticmethod
    def get_all() -> List[dict]:
        """Get all projects"""
        query = f"SELECT * FROM {SCHEMA}.projects ORDER BY name"
        with get_db_cursor() as cursor:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def delete(project_id: int) -> bool:
        """Delete project"""
        query = f"DELETE FROM {SCHEMA}.projects WHERE id = %s RETURNING id"
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, (project_id,))
            return cursor.fetchone() is not None


class ServerModel:
    @staticmethod
    def create(server_data: dict) -> dict:
        """Create a new server"""
        query = f"""
            INSERT INTO {SCHEMA}.servers (server_name, port, server_location)
            VALUES (%(server_name)s, %(port)s, %(server_location)s)
            RETURNING id, server_name, port, server_location, created_at, updated_at
        """
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, server_data)
            return dict(cursor.fetchone())

    @staticmethod
    def get_all() -> List[dict]:
        """Get all servers"""
        query = f"SELECT * FROM {SCHEMA}.servers ORDER BY server_name"
        with get_db_cursor() as cursor:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(server_id: int) -> Optional[dict]:
        """Get server by ID"""
        query = f"SELECT * FROM {SCHEMA}.servers WHERE id = %s"
        with get_db_cursor() as cursor:
            cursor.execute(query, (server_id,))
            result = cursor.fetchone()
            return dict(result) if result else None

    @staticmethod
    def update(server_id: int, server_data: dict) -> Optional[dict]:
        """Update server"""
        query = f"""
            UPDATE {SCHEMA}.servers
            SET server_name = %(server_name)s,
                port = %(port)s,
                server_location = %(server_location)s
            WHERE id = %(id)s
            RETURNING id, server_name, port, server_location, created_at, updated_at
        """
        server_data['id'] = server_id
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, server_data)
            result = cursor.fetchone()
            return dict(result) if result else None

    @staticmethod
    def delete(server_id: int) -> bool:
        """Delete server"""
        query = f"DELETE FROM {SCHEMA}.servers WHERE id = %s RETURNING id"
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, (server_id,))
            return cursor.fetchone() is not None


class StatsModel:
    @staticmethod
    def get_overall_stats() -> dict:
        """Get overall statistics"""
        with get_db_cursor() as cursor:
            # Total URLs
            cursor.execute(f"SELECT COUNT(*) as count FROM {SCHEMA}.urls")
            total_urls = cursor.fetchone()['count']

            # Get latest status for each URL
            cursor.execute(f"""
                SELECT DISTINCT ON (url_id) status
                FROM {SCHEMA}.health_status
                ORDER BY url_id, checked_at DESC
            """)
            statuses = [row['status'] for row in cursor.fetchall()]
            
            online_urls = statuses.count('online')
            offline_urls = statuses.count('offline')

            # Total health checks
            cursor.execute(f"SELECT COUNT(*) as count FROM {SCHEMA}.health_status")
            total_checks = cursor.fetchone()['count']

            return {
                'total_urls': total_urls,
                'online_urls': online_urls,
                'offline_urls': offline_urls,
                'total_checks': total_checks
            }


class GPUMetricsModel:
    @staticmethod
    def get_latest_metrics() -> List[dict]:
        """Get latest GPU metrics for each host and GPU with their processes"""
        query = f"""
            WITH latest_metrics AS (
                SELECT DISTINCT ON (host, gpu_index)
                    id, host, timestamp, gpu_index, gpu_name,
                    gpu_memory_total_mib, gpu_memory_used_mib, gpu_memory_free_mib,
                    gpu_utilization_pct, host_memory_total_mib, host_memory_used_mib,
                    host_memory_free_mib, host_disk_total_mib, host_disk_used_mib,
                    host_disk_free_mib, host_disk_usage_pct
                FROM {SCHEMA}.gpu_metrics
                ORDER BY host, gpu_index, timestamp DESC
            )
            SELECT 
                lm.*,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'pid', pm.pid,
                            'process_name', pm.process_name,
                            'cmd', pm.cmd,
                            'used_mem_mib', pm.used_mem_mib,
                            'process_ram_mib', COALESCE(pm.process_ram_mib, 0)
                        ) ORDER BY pm.used_mem_mib DESC
                    ) FILTER (WHERE pm.id IS NOT NULL),
                    '[]'::json
                ) as processes
            FROM latest_metrics lm
            LEFT JOIN {SCHEMA}.pid_metrics pm ON lm.id = pm.gpu_metrics_id
            GROUP BY lm.id, lm.host, lm.timestamp, lm.gpu_index, lm.gpu_name,
                     lm.gpu_memory_total_mib, lm.gpu_memory_used_mib, lm.gpu_memory_free_mib,
                     lm.gpu_utilization_pct, lm.host_memory_total_mib, lm.host_memory_used_mib,
                     lm.host_memory_free_mib, lm.host_disk_total_mib, lm.host_disk_used_mib,
                     lm.host_disk_free_mib, lm.host_disk_usage_pct
            ORDER BY lm.host, lm.gpu_index
        """
        with get_db_cursor() as cursor:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_metrics_by_host(host: str) -> List[dict]:
        """Get latest GPU metrics for a specific host with their processes"""
        query = f"""
            WITH latest_metrics AS (
                SELECT DISTINCT ON (gpu_index)
                    id, host, timestamp, gpu_index, gpu_name,
                    gpu_memory_total_mib, gpu_memory_used_mib, gpu_memory_free_mib,
                    gpu_utilization_pct, host_memory_total_mib, host_memory_used_mib,
                    host_memory_free_mib, host_disk_total_mib, host_disk_used_mib,
                    host_disk_free_mib, host_disk_usage_pct
                FROM {SCHEMA}.gpu_metrics
                WHERE host = %s
                ORDER BY gpu_index, timestamp DESC
            )
            SELECT 
                lm.*,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'pid', pm.pid,
                            'process_name', pm.process_name,
                            'cmd', pm.cmd,
                            'used_mem_mib', pm.used_mem_mib,
                            'process_ram_mib', COALESCE(pm.process_ram_mib, 0)
                        ) ORDER BY pm.used_mem_mib DESC
                    ) FILTER (WHERE pm.id IS NOT NULL),
                    '[]'::json
                ) as processes
            FROM latest_metrics lm
            LEFT JOIN {SCHEMA}.pid_metrics pm ON lm.id = pm.gpu_metrics_id
            GROUP BY lm.id, lm.host, lm.timestamp, lm.gpu_index, lm.gpu_name,
                     lm.gpu_memory_total_mib, lm.gpu_memory_used_mib, lm.gpu_memory_free_mib,
                     lm.gpu_utilization_pct, lm.host_memory_total_mib, lm.host_memory_used_mib,
                     lm.host_memory_free_mib, lm.host_disk_total_mib, lm.host_disk_used_mib,
                     lm.host_disk_free_mib, lm.host_disk_usage_pct
            ORDER BY lm.gpu_index
        """
        with get_db_cursor() as cursor:
            cursor.execute(query, (host,))
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_overall_metrics_by_gpu_name() -> List[dict]:
        """Get overall aggregated metrics grouped by GPU name"""
        query = f"""
            WITH latest_metrics AS (
                SELECT DISTINCT ON (host, gpu_index)
                    id, host, timestamp, gpu_index, gpu_name,
                    gpu_memory_total_mib, gpu_memory_used_mib, gpu_memory_free_mib,
                    gpu_utilization_pct, host_memory_total_mib, host_memory_used_mib,
                    host_memory_free_mib, host_disk_total_mib, host_disk_used_mib,
                    host_disk_free_mib, host_disk_usage_pct
                FROM {SCHEMA}.gpu_metrics
                ORDER BY host, gpu_index, timestamp DESC
            )
            SELECT 
                gpu_name,
                COUNT(*) as gpu_count,
                ROUND(AVG(gpu_utilization_pct)::numeric, 1) as avg_gpu_utilization_pct,
                SUM(gpu_memory_total_mib) as total_gpu_memory_total_mib,
                SUM(gpu_memory_used_mib) as total_gpu_memory_used_mib,
                SUM(gpu_memory_free_mib) as total_gpu_memory_free_mib,
                ROUND((SUM(gpu_memory_used_mib)::numeric / NULLIF(SUM(gpu_memory_total_mib), 0) * 100), 1) as gpu_memory_usage_pct,
                SUM(host_memory_used_mib) as total_host_memory_used_mib,
                MAX(host_memory_total_mib) as max_host_memory_total_mib,
                ROUND((SUM(host_memory_used_mib)::numeric / NULLIF(MAX(host_memory_total_mib), 0) * 100), 1) as host_memory_usage_pct,
                -- Host disk metrics (same for all GPUs on same host, so use MAX to get one value)
                MAX(host_disk_total_mib) as host_disk_total_mib,
                MAX(host_disk_used_mib) as host_disk_used_mib,
                MAX(host_disk_free_mib) as host_disk_free_mib,
                MAX(host_disk_usage_pct) as host_disk_usage_pct
            FROM latest_metrics
            GROUP BY gpu_name
            ORDER BY gpu_name
        """
        with get_db_cursor() as cursor:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_all_hosts() -> List[str]:
        """Get all unique hosts"""
        query = f"""
            SELECT DISTINCT host 
            FROM {SCHEMA}.gpu_metrics
            ORDER BY host
        """
        with get_db_cursor() as cursor:
            cursor.execute(query)
            return [row['host'] for row in cursor.fetchall()]
    
    @staticmethod
    def insert_metric(metric_data: dict) -> int:
        """Insert a GPU metric and return the ID"""
        query = f"""
            INSERT INTO {SCHEMA}.gpu_metrics (
                host, gpu_index, gpu_name, gpu_memory_total_mib,
                gpu_memory_used_mib, gpu_memory_free_mib, gpu_utilization_pct,
                host_memory_total_mib, host_memory_used_mib, host_memory_free_mib,
                host_disk_total_mib, host_disk_used_mib, host_disk_free_mib, host_disk_usage_pct
            )
            VALUES (
                %(host)s, %(gpu_index)s, %(gpu_name)s, %(gpu_memory_total_mib)s,
                %(gpu_memory_used_mib)s, %(gpu_memory_free_mib)s, %(gpu_utilization_pct)s,
                %(host_memory_total_mib)s, %(host_memory_used_mib)s, %(host_memory_free_mib)s,
                %(host_disk_total_mib)s, %(host_disk_used_mib)s, %(host_disk_free_mib)s, %(host_disk_usage_pct)s
            )
            RETURNING id
        """
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute(query, metric_data)
                result = cursor.fetchone()
                if result:
                    return result['id']
                else:
                    raise Exception("No ID returned from insert")
        except Exception as e:
            print(f"Error inserting GPU metric: {e}")
            print(f"Metric data: {metric_data}")
            raise


class PidMetricsModel:
    @staticmethod
    def insert_process(process_data: dict) -> dict:
        """Insert a process metric"""
        query = f"""
            INSERT INTO {SCHEMA}.pid_metrics (
                gpu_metrics_id, pid, process_name, cmd, used_mem_mib
            )
            VALUES (
                %(gpu_metrics_id)s, %(pid)s, %(process_name)s, %(cmd)s, %(used_mem_mib)s
            )
            RETURNING id, gpu_metrics_id, pid, process_name, cmd, used_mem_mib, timestamp
        """
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, process_data)
            return dict(cursor.fetchone())
    
    @staticmethod
    def insert_processes_batch(processes: List[dict]) -> int:
        """Insert multiple process metrics in a batch"""
        if not processes:
            return 0
        
        query = f"""
            INSERT INTO {SCHEMA}.pid_metrics (
                gpu_metrics_id, pid, process_name, cmd, used_mem_mib, process_ram_mib
            )
            VALUES (
                %(gpu_metrics_id)s, %(pid)s, %(process_name)s, %(cmd)s, %(used_mem_mib)s, %(process_ram_mib)s
            )
        """
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.executemany(query, processes)
                inserted_count = cursor.rowcount
                return inserted_count
        except Exception as e:
            print(f"Error inserting processes batch: {e}")
            raise
    
    @staticmethod
    def get_by_gpu_metrics_id(gpu_metrics_id: int) -> List[dict]:
        """Get all processes for a specific GPU metric"""
        query = f"""
            SELECT id, gpu_metrics_id, pid, process_name, cmd, used_mem_mib, timestamp
            FROM {SCHEMA}.pid_metrics
            WHERE gpu_metrics_id = %s
            ORDER BY used_mem_mib DESC
        """
        with get_db_cursor() as cursor:
            cursor.execute(query, (gpu_metrics_id,))
            return [dict(row) for row in cursor.fetchall()]


class GPUServerModel:
    @staticmethod
    def create(server_data: dict) -> dict:
        """Create a new GPU server - encrypt and store RSA key content in DB"""
        from cryptography.fernet import Fernet
        
        # Get encryption key from environment
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            raise Exception("ENCRYPTION_KEY not found in environment! Please set it in .env file")
        
        cipher = Fernet(encryption_key.encode())
        
        # Get RSA key content (exact content from uploaded file)
        rsa_key_content = server_data['rsa_key']
        
        # Encrypt the RSA key content
        encrypted_rsa_key = cipher.encrypt(rsa_key_content.encode()).decode()
        logger.info(f"RSA key encrypted and will be stored in database (length: {len(rsa_key_content)} chars)")
        
        # Handle optional passphrase - encrypt if provided
        passphrase = server_data.get('rsa_key_passphrase')
        if passphrase and passphrase != 'None':
            encrypted_passphrase = cipher.encrypt(passphrase.encode()).decode()
        else:
            encrypted_passphrase = None
        
        import json
        
        # Convert alert_emails list to JSON
        alert_emails = server_data.get('alert_emails', [])
        if isinstance(alert_emails, str):
            alert_emails = [alert_emails] if alert_emails else []
        
        query = f"""
            INSERT INTO {SCHEMA}.gpu_server (server_ip, server_name, gpu_name, username, port, rsa_key,
                                            rsa_key_passphrase, server_location,
                                            usage_limit, alert_emails)
            VALUES (%(server_ip)s, %(server_name)s, %(gpu_name)s, %(username)s, %(port)s, %(rsa_key)s,
                    %(rsa_key_passphrase)s, %(server_location)s,
                    %(usage_limit)s, %(alert_emails)s::jsonb)
            RETURNING id, server_ip, server_name, gpu_name, username, port, server_location,
                      usage_limit, alert_emails, created_at, last_updated_at
        """
        data = {
            'server_ip': server_data['server_ip'],
            'server_name': server_data['server_name'],
            'gpu_name': server_data.get('gpu_name'),
            'username': server_data['username'],
            'port': server_data['port'],
            'rsa_key': encrypted_rsa_key,  # Store encrypted content in DB
            'rsa_key_passphrase': encrypted_passphrase,  # Store encrypted passphrase
            'server_location': server_data.get('server_location'),
            'usage_limit': server_data.get('usage_limit', 80),
            'alert_emails': json.dumps(alert_emails)
        }
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, data)
            return dict(cursor.fetchone())

    @staticmethod
    def get_all() -> List[dict]:
        """Get all GPU servers (without decrypted keys)"""
        query = f"""
            SELECT id, server_ip, server_name, gpu_name, username, port, server_location,
                   usage_limit, alert_emails, created_at, last_updated_at
            FROM {SCHEMA}.gpu_server
            ORDER BY server_name
        """
        with get_db_cursor() as cursor:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_all_with_keys() -> List[dict]:
        """Get all GPU servers (includes encrypted keys for monitoring service)"""
        query = f"""
            SELECT id, server_ip, server_name, gpu_name, username, port, server_location,
                   usage_limit, alert_emails, created_at, last_updated_at
            FROM {SCHEMA}.gpu_server
            ORDER BY server_name
        """
        with get_db_cursor() as cursor:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(server_id: int, decrypt_keys: bool = False) -> Optional[dict]:
        """Get GPU server by ID - decrypt RSA key content if requested"""
        if decrypt_keys:
            query = f"""
                SELECT id, server_ip, server_name, gpu_name, username, port, rsa_key, rsa_key_passphrase,
                       server_location, usage_limit, alert_emails, created_at, last_updated_at
                FROM {SCHEMA}.gpu_server WHERE id = %s
            """
        else:
            query = f"""
                SELECT id, server_ip, server_name, gpu_name, username, port, server_location,
                       usage_limit, alert_emails, created_at, last_updated_at
                FROM {SCHEMA}.gpu_server WHERE id = %s
            """
        
        with get_db_cursor() as cursor:
            cursor.execute(query, (server_id,))
            result = cursor.fetchone()
            if not result:
                return None
            
            server_dict = dict(result)
            
            # Decrypt RSA key and passphrase if requested
            if decrypt_keys and 'rsa_key' in server_dict:
                from cryptography.fernet import Fernet
                
                encryption_key = os.getenv('ENCRYPTION_KEY')
                if not encryption_key:
                    logger.error("ENCRYPTION_KEY not found in environment!")
                    server_dict['rsa_key'] = None
                    return server_dict
                
                try:
                    cipher = Fernet(encryption_key.encode())
                    
                    # Decrypt RSA key content
                    encrypted_key = server_dict['rsa_key']
                    decrypted_key = cipher.decrypt(encrypted_key.encode()).decode()
                    server_dict['rsa_key'] = decrypted_key
                    logger.debug(f"RSA key decrypted successfully (length: {len(decrypted_key)} chars)")
                    
                    # Decrypt passphrase if exists
                    if server_dict.get('rsa_key_passphrase'):
                        encrypted_pass = server_dict['rsa_key_passphrase']
                        decrypted_pass = cipher.decrypt(encrypted_pass.encode()).decode()
                        server_dict['rsa_key_passphrase'] = decrypted_pass
                    else:
                        server_dict['rsa_key_passphrase'] = None
                        
                except Exception as e:
                    logger.error(f"Failed to decrypt RSA key: {e}")
                    server_dict['rsa_key'] = None
            
            return server_dict

    @staticmethod
    def update(server_id: int, server_data: dict) -> Optional[dict]:
        """Update GPU server"""
        from cryptography.fernet import Fernet
        import os
        
        # Build update fields dynamically
        update_fields = []
        data = {'id': server_id}
        
        if 'server_ip' in server_data:
            update_fields.append("server_ip = %(server_ip)s")
            data['server_ip'] = server_data['server_ip']
        
        if 'server_name' in server_data:
            update_fields.append("server_name = %(server_name)s")
            data['server_name'] = server_data['server_name']
        
        if 'gpu_name' in server_data:
            update_fields.append("gpu_name = %(gpu_name)s")
            data['gpu_name'] = server_data['gpu_name']
        
        if 'username' in server_data:
            update_fields.append("username = %(username)s")
            data['username'] = server_data['username']
        
        if 'port' in server_data:
            update_fields.append("port = %(port)s")
            data['port'] = server_data['port']
        
        if 'server_location' in server_data:
            update_fields.append("server_location = %(server_location)s")
            data['server_location'] = server_data['server_location']
        
        if 'usage_limit' in server_data:
            update_fields.append("usage_limit = %(usage_limit)s")
            data['usage_limit'] = server_data['usage_limit']
        
        if 'alert_emails' in server_data:
            import json
            alert_emails = server_data['alert_emails']
            if isinstance(alert_emails, str):
                alert_emails = [alert_emails] if alert_emails else []
            update_fields.append("alert_emails = %(alert_emails)s::jsonb")
            data['alert_emails'] = json.dumps(alert_emails)
        
        # Handle RSA key update - encrypt and store content in DB
        if 'rsa_key' in server_data:
            rsa_key_content = server_data['rsa_key']
            
            encryption_key = os.getenv('ENCRYPTION_KEY')
            if not encryption_key:
                raise Exception("ENCRYPTION_KEY not found in environment!")
            
            cipher = Fernet(encryption_key.encode())
            encrypted_rsa_key = cipher.encrypt(rsa_key_content.encode()).decode()
            
            logger.info(f"Updated RSA key encrypted and stored in database")
            
            update_fields.append("rsa_key = %(rsa_key)s")
            data['rsa_key'] = encrypted_rsa_key
        
        if 'rsa_key_passphrase' in server_data:
            passphrase = server_data['rsa_key_passphrase']
            
            if passphrase and passphrase != 'None':
                encryption_key = os.getenv('ENCRYPTION_KEY')
                cipher = Fernet(encryption_key.encode())
                encrypted_passphrase = cipher.encrypt(passphrase.encode()).decode()
                update_fields.append("rsa_key_passphrase = %(rsa_key_passphrase)s")
                data['rsa_key_passphrase'] = encrypted_passphrase
            else:
                update_fields.append("rsa_key_passphrase = %(rsa_key_passphrase)s")
                data['rsa_key_passphrase'] = None
        
        if not update_fields:
            return GPUServerModel.get_by_id(server_id)
        
        query = f"""
            UPDATE {SCHEMA}.gpu_server
            SET {', '.join(update_fields)}
            WHERE id = %(id)s
            RETURNING id, server_ip, server_name, gpu_name, username, port, server_location,
                      usage_limit, alert_emails, created_at, last_updated_at
        """
        
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, data)
            result = cursor.fetchone()
            return dict(result) if result else None

    @staticmethod
    def delete(server_id: int) -> bool:
        """Delete GPU server"""
        query = f"DELETE FROM {SCHEMA}.gpu_server WHERE id = %s RETURNING id"
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, (server_id,))
            return cursor.fetchone() is not None
    
    @staticmethod
    def get_by_gpu_name(gpu_name: str) -> List[dict]:
        """Get all servers with a specific GPU name"""
        query = f"""
            SELECT id, server_ip, server_name, gpu_name, username, port, server_location,
                   usage_limit, alert_emails, created_at, last_updated_at
            FROM {SCHEMA}.gpu_server
            WHERE gpu_name = %s
            ORDER BY server_name
        """
        with get_db_cursor() as cursor:
            cursor.execute(query, (gpu_name,))
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def update_usage_limit(server_id: int, usage_limit: int) -> Optional[dict]:
        """Update usage limit for a server"""
        query = f"""
            UPDATE {SCHEMA}.gpu_server
            SET usage_limit = %s, last_updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, server_ip, server_name, gpu_name, username, port, server_location,
                      usage_limit, alert_emails, created_at, last_updated_at
        """
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, (usage_limit, server_id))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    @staticmethod
    def update_alert_emails(server_id: int, alert_emails: List[str]) -> Optional[dict]:
        """Update alert emails for a server"""
        import json
        
        query = f"""
            UPDATE {SCHEMA}.gpu_server
            SET alert_emails = %s::jsonb, last_updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, server_ip, server_name, gpu_name, username, port, server_location,
                      usage_limit, alert_emails, created_at, last_updated_at
        """
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, (json.dumps(alert_emails), server_id))
            result = cursor.fetchone()
            return dict(result) if result else None