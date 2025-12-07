import httpx
import asyncio
from datetime import datetime
from typing import List, Dict, Set
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ..models.database_models import URLModel, HealthStatusModel
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.websocket_connections: Set = set()
        self.is_running = False
        self.health_check_interval = int(os.getenv('HEALTH_CHECK_INTERVAL_MINUTES', '1'))
        self.http_timeout = float(os.getenv('HTTP_TIMEOUT_SECONDS', '5.0'))

    def add_websocket_connection(self, websocket):
        """Add a WebSocket connection for broadcasting"""
        self.websocket_connections.add(websocket)

    def remove_websocket_connection(self, websocket):
        """Remove a WebSocket connection"""
        self.websocket_connections.discard(websocket)

    async def broadcast_health_update(self, url_id: int, health_data: dict):
        """Broadcast health update to all connected WebSocket clients"""
        message = {
            "type": "health_update",
            "data": {
                "url_id": url_id,
                "status": health_data['status'],
                "response_time": health_data.get('response_time'),
                "status_code": health_data.get('status_code'),
                "checked_at": health_data['checked_at'].isoformat() if isinstance(health_data.get('checked_at'), datetime) else str(health_data.get('checked_at')),
                "error_message": health_data.get('error_message')
            }
        }

        # Remove dead connections
        dead_connections = set()
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to websocket: {e}")
                dead_connections.add(websocket)

        # Clean up dead connections
        self.websocket_connections -= dead_connections

    async def check_single_url(self, url_data: dict) -> dict:
        """Check health of a single URL"""
        url_id = url_data['id']
        url = url_data['url']
        
        health_status = {
            'url_id': url_id,
            'status': 'offline',
            'response_time': None,
            'status_code': None,
            'error_message': None
        }

        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                start_time = asyncio.get_event_loop().time()
                response = await client.get(url, follow_redirects=True)
                end_time = asyncio.get_event_loop().time()
                
                response_time_ms = int((end_time - start_time) * 1000)
                
                health_status['response_time'] = response_time_ms
                health_status['status_code'] = response.status_code
                
                if response.status_code == 200:
                    health_status['status'] = 'online'
                else:
                    health_status['status'] = 'offline'
                    health_status['error_message'] = f"HTTP {response.status_code}"
                
                logger.info(f"Checked {url}: {health_status['status']} ({response_time_ms}ms)")

        except httpx.TimeoutException:
            health_status['error_message'] = "Request timeout"
            logger.warning(f"Timeout checking {url}")
        except httpx.RequestError as e:
            health_status['error_message'] = f"Request error: {str(e)}"
            logger.error(f"Error checking {url}: {e}")
        except Exception as e:
            health_status['error_message'] = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error checking {url}: {e}")

        return health_status

    async def check_all_urls(self):
        """Check health of all URLs"""
        try:
            logger.info("Starting health check cycle...")
            
            # Get all URLs from database
            all_urls = URLModel.get_all()
            
            # Filter only URLs with health_check_enabled = True
            urls = [url for url in all_urls if url.get('health_check_enabled', True)]
            
            if not urls:
                logger.info("No URLs to check (all disabled or none available)")
                return

            logger.info(f"Checking {len(urls)} URLs (out of {len(all_urls)} total)")

            # Check all URLs concurrently
            tasks = [self.check_single_url(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Store results in database and broadcast via WebSocket
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error in health check: {result}")
                    continue

                try:
                    # Save to database
                    saved_health = HealthStatusModel.create(result)
                    
                    # Broadcast to WebSocket clients
                    await self.broadcast_health_update(result['url_id'], saved_health)
                    
                except Exception as e:
                    logger.error(f"Error saving health status: {e}")

            logger.info(f"Health check cycle completed. Checked {len(results)} URLs")

        except Exception as e:
            logger.error(f"Error in check_all_urls: {e}")

    def start(self):
        """Start the health checker scheduler"""
        if not self.is_running:
            # Schedule to run based on configured interval
            self.scheduler.add_job(
                self.check_all_urls,
                'interval',
                minutes=self.health_check_interval,
                id='health_check_job',
                replace_existing=True
            )
            
            # Run immediately on start
            self.scheduler.add_job(
                self.check_all_urls,
                'date',
                run_date=datetime.now(),
                id='initial_health_check'
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info(f"Health checker started - checking URLs every {self.health_check_interval} minute(s)")

    def stop(self):
        """Stop the health checker scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Health checker stopped")


# Global instance
health_checker = HealthChecker()