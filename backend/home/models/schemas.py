from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime

# URL Schemas
class URLBase(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1)
    environment: Literal['production', 'development', 'staging']
    project_category: Optional[str] = None
    server_id: Optional[int] = None
    health_check_status: Optional[Literal['YES', 'NO']] = 'YES'
    description: Optional[str] = None
    alert_emails: List[str] = Field(default_factory=list)

class URLCreate(URLBase):
    pass

class URLUpdate(URLBase):
    pass

class URLResponse(URLBase):
    id: int
    health_check_status: Literal['YES', 'NO']
    description: Optional[str] = None
    alert_emails: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class HealthCheckToggle(BaseModel):
    status: Literal['YES', 'NO']

# Health Status Schemas
class HealthStatusBase(BaseModel):
    url_id: int
    status: Literal['online', 'offline']
    response_time: Optional[int] = None
    status_code: Optional[int] = None
    error_message: Optional[str] = None

class HealthStatusCreate(HealthStatusBase):
    pass

class HealthStatusResponse(HealthStatusBase):
    id: int
    checked_at: datetime

    class Config:
        from_attributes = True

# Project Schemas
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Server Schemas
class ServerBase(BaseModel):
    server_name: str = Field(..., min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    server_location: Literal['India', 'Estonia']

class ServerCreate(ServerBase):
    pass

class ServerUpdate(ServerBase):
    pass

class ServerResponse(ServerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Statistics Schema
class StatsResponse(BaseModel):
    total_urls: int
    online_urls: int
    offline_urls: int
    total_checks: int

# WebSocket Message Schema
class WebSocketMessage(BaseModel):
    type: str
    data: dict

# GPU Metrics Schemas
class GPUProcess(BaseModel):
    pid: int
    process_name: str
    cmd: str
    used_mem_mib: int

class GPUMetricsResponse(BaseModel):
    id: int
    host: str
    timestamp: datetime
    gpu_index: int
    gpu_name: str
    gpu_memory_total_mib: int
    gpu_memory_used_mib: int
    gpu_memory_free_mib: int
    gpu_utilization_pct: int
    host_memory_total_mib: int
    host_memory_used_mib: int
    host_memory_free_mib: int
    host_disk_total_mib: Optional[int] = None
    host_disk_used_mib: Optional[int] = None
    host_disk_free_mib: Optional[int] = None
    host_disk_usage_pct: Optional[float] = None
    processes: List[Dict[str, Any]]

    class Config:
        from_attributes = True

# PID Metrics Schemas
class PidMetricsBase(BaseModel):
    gpu_metrics_id: int
    pid: int
    process_name: str = Field(..., max_length=500)
    cmd: Optional[str] = None
    used_mem_mib: int

class PidMetricsCreate(PidMetricsBase):
    pass

class PidMetricsResponse(PidMetricsBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# User Schemas
class User(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    azure_user_id: str
    role: str
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime


class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class Role(BaseModel):
    id: int
    role_name: str
    display_name: str
    description: Optional[str] = None
    can_view_urls: bool
    can_add_urls: bool
    can_edit_urls: bool
    can_delete_urls: bool
    can_view_servers: bool
    can_add_servers: bool
    can_edit_servers: bool
    can_delete_servers: bool
    can_view_gpu_stats: bool
    can_manage_email_alerts: bool
    can_manage_users: bool


# GPU Server Schemas
class GPUServerBase(BaseModel):
    server_ip: str = Field(..., min_length=1, max_length=45)
    server_name: str = Field(..., min_length=1, max_length=255)
    gpu_name: Optional[str] = Field(None, max_length=255)
    username: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    rsa_key: str = Field(..., min_length=1)
    rsa_key_passphrase: Optional[str] = None
    server_location: Optional[str] = Field(None, max_length=100)
    usage_limit: int = Field(default=80, ge=0, le=100)
    alert_emails: List[str] = Field(default_factory=list)


class GPUServerCreate(GPUServerBase):
    pass


class GPUServerUpdate(BaseModel):
    server_ip: Optional[str] = Field(None, min_length=1, max_length=45)
    server_name: Optional[str] = Field(None, min_length=1, max_length=255)
    gpu_name: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    rsa_key: Optional[str] = Field(None, min_length=1)
    rsa_key_passphrase: Optional[str] = None
    server_location: Optional[str] = Field(None, max_length=100)
    usage_limit: Optional[int] = Field(None, ge=0, le=100)
    alert_emails: Optional[List[str]] = None


class GPUServerResponse(BaseModel):
    id: int
    server_ip: str
    server_name: str
    gpu_name: Optional[str] = None
    username: str
    port: int
    server_location: Optional[str] = None
    usage_limit: int
    alert_emails: List[str] = Field(default_factory=list)
    created_at: datetime
    last_updated_at: datetime

    class Config:
        from_attributes = True