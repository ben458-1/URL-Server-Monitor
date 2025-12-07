import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ..config.database import get_db_cursor, get_schema_name
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get schema from config
SCHEMA = get_schema_name()

class DatabaseCleanupService:
    """Service to automatically clean up old records from database tables"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        # Retention period in days (default: 1 day)
        self.retention_days = int(os.getenv('DB_RETENTION_DAYS', '1'))
        
    async def cleanup_old_records(self):
        """Delete records older than retention period from all tracked tables"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            logger.info(f"Starting database cleanup - removing records older than {cutoff_date}")
            
            # Count and delete from each table
            deleted_counts = {}
            
            # 1. Clean up health_status table
            deleted_counts['health_status'] = self._cleanup_table(
                'health_status',
                'checked_at',
                cutoff_date
            )
            
            # 2. Clean up pid_metrics table (must be before gpu_metrics due to foreign key)
            deleted_counts['pid_metrics'] = self._cleanup_table(
                'pid_metrics',
                'timestamp',
                cutoff_date
            )
            
            # 3. Clean up gpu_metrics table
            deleted_counts['gpu_metrics'] = self._cleanup_table(
                'gpu_metrics',
                'timestamp',
                cutoff_date
            )
            
            # Log summary
            total_deleted = sum(deleted_counts.values())
            logger.info(f"Database cleanup completed - Total records deleted: {total_deleted}")
            logger.info(f"  - health_status: {deleted_counts['health_status']}")
            logger.info(f"  - pid_metrics: {deleted_counts['pid_metrics']}")
            logger.info(f"  - gpu_metrics: {deleted_counts['gpu_metrics']}")
            
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}", exc_info=True)
    
    def _cleanup_table(self, table_name: str, timestamp_column: str, cutoff_date: datetime) -> int:
        """Delete old records from a specific table"""
        try:
            query = f"""
                DELETE FROM {SCHEMA}.{table_name}
                WHERE {timestamp_column} < %s
            """
            
            with get_db_cursor(commit=True) as cursor:
                cursor.execute(query, (cutoff_date,))
                deleted_count = cursor.rowcount
                logger.info(f"Deleted {deleted_count} records from {table_name} older than {cutoff_date}")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning up {table_name}: {e}")
            return 0
    
    def start(self):
        """Start the database cleanup scheduler"""
        if not self.is_running:
            # Schedule daily cleanup at 6:00 AM
            self.scheduler.add_job(
                self.cleanup_old_records,
                'cron',
                hour=6,
                minute=0,
                id='db_cleanup_job',
                replace_existing=True
            )
            
            # Optionally run immediately on start (commented out by default)
            # Uncomment the following to run cleanup on service start
            # self.scheduler.add_job(
            #     self.cleanup_old_records,
            #     'date',
            #     run_date=datetime.now(),
            #     id='initial_cleanup'
            # )
            
            self.scheduler.start()
            self.is_running = True
            logger.info(f"Database cleanup service started - will run daily at 2:00 AM")
            logger.info(f"Retention period: {self.retention_days} day(s)")
    
    def stop(self):
        """Stop the database cleanup scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Database cleanup service stopped")


# Global instance
db_cleanup_service = DatabaseCleanupService()

