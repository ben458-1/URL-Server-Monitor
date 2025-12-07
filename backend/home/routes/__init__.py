from .urls import router as urls_router
from .health import router as health_router, projects_router
from .servers import router as servers_router
from .gpu_metrics import router as gpu_router
from .gpu_servers import router as gpu_servers_router
from .users import router as users_router

__all__ = ['urls_router', 'health_router', 'projects_router', 'servers_router', 'gpu_router', 'gpu_servers_router', 'users_router']