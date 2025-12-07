# Monitor Tool

A comprehensive monitoring system for URL health checks, server management, and GPU metrics tracking with real-time updates via WebSocket. Features Azure AD authentication and role-based access control.

## 🏗️ Architecture Overview

This system follows a client-server architecture with a FastAPI backend and React frontend. The backend provides RESTful APIs and WebSocket support for real-time monitoring updates.

```
┌─────────────────┐
│   React Frontend │
│   (Port 3000)   │
└────────┬────────┘
         │
         │ HTTP/WebSocket
         │
         ▼
┌─────────────────┐
│  FastAPI Backend│
│   (Port 8080)   │
└────────┬────────┘
         │
         ├──────────────┐
         │              │
         ▼              ▼
┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │  Background  │
│   Database   │  │   Services   │
└──────────────┘  └──────────────┘
```

## 📦 Components

### Backend Services

#### 1. **FastAPI Backend** (`backend/`)
- **Purpose**: RESTful API server for monitoring management
- **Technology**: Python, FastAPI, PostgreSQL, WebSocket
- **Port**: 8080 (configurable via `API_PORT`)
- **Key Features**:
  - URL health monitoring with automated checks
  - Server management and monitoring
  - GPU metrics collection and tracking
  - User management with Azure AD integration
  - Real-time updates via WebSocket
  - Email alert notifications
  - Database cleanup services
  - Role-based access control (admin, owner, editor, viewer)

#### 2. **Background Services**
- **Health Checker**: Automatically checks URL health every minute
- **GPU Monitor**: Collects GPU metrics from configured servers
- **Database Cleanup**: Automatically cleans up old health check records

### Frontend Application

#### 3. **React Frontend** (`frontend/`)
- **Purpose**: User interface for monitoring dashboard
- **Technology**: React, Azure MSAL, WebSocket
- **Port**: 3000 (development), 8081 (production)
- **Key Features**:
  - Azure AD authentication
  - Real-time health status updates
  - URL management (CRUD operations)
  - Server management
  - GPU statistics and monitoring
  - User management interface
  - Environment-based filtering (production, development, staging)
  - Project category filtering
  - Email alert configuration
  - Responsive design

## 🗄️ Database Schema

The system uses PostgreSQL with the following main tables:

- `urls` - URL monitoring configurations
- `health_checks` - Health check history and status
- `servers` - Server information and configurations
- `gpu_servers` - GPU server configurations
- `gpu_metrics` - GPU metrics data
- `users` - User accounts and roles
- `projects` - Project categories
- `email_alerts` - Email alert configurations

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Node.js 18+
- PostgreSQL 12+
- Azure AD App Registration (for authentication)

### Environment Setup

#### Backend Configuration

Create a `.env` file in the `backend/` directory:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=monitor_tool
DB_USER=postgres
DB_PASSWORD=your_password

# API Configuration
API_PORT=8080
ENVIRONMENT=development

# Azure AD Configuration
AZURE_CLIENT_ID=your_azure_client_id
AZURE_CLIENT_SECRET=your_azure_client_secret
AZURE_TENANT_ID=your_azure_tenant_id

# Email Configuration (for alerts)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_password
SENDER_EMAIL=noreply@example.com
```

#### Frontend Configuration

Create a `.env` file in the `frontend/` directory:

```env
REACT_APP_API_URL=http://localhost:8080
REACT_APP_WS_URL=ws://localhost:8080
```

Update `frontend/src/authConfig.js` with your Azure AD configuration:
- `clientId`: Your Azure App Client ID
- `authority`: Your Azure Tenant ID

### Installation

#### 1. Database Setup

```bash
# Create database
createdb monitor_tool

# Or using psql
psql -U postgres
CREATE DATABASE monitor_tool;
\q
```

#### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python home/database/init_db.py
```

#### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### Running the Application

#### Development Mode

**Backend:**
```bash
cd backend
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host localhost --port 8080
```

**Frontend:**
```bash
cd frontend
npm start
```

The application will be available at:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8080`
- API Documentation: `http://localhost:8080/docs`

#### Production Mode (Docker)

```bash
docker-compose up -d
```

This will start:
- Backend on port 8080
- Frontend on port 8081

## 📊 API Endpoints

### URLs
- `POST /api/urls` - Create new URL
- `GET /api/urls` - Get all URLs
- `GET /api/urls/{id}` - Get specific URL
- `PUT /api/urls/{id}` - Update URL
- `DELETE /api/urls/{id}` - Delete URL
- `GET /api/urls/environment/{env}` - Get URLs by environment
- `PATCH /api/urls/{id}/alert-emails` - Update alert emails

### Health Status
- `GET /api/health/url/{id}` - Get current health status
- `GET /api/health/url/{id}/history?minutes=20` - Get health history
- `GET /api/health/all-latest` - Get latest status for all URLs
- `GET /api/health/stats` - Get overall statistics

### Servers
- `GET /api/servers` - Get all servers
- `POST /api/servers` - Create server
- `GET /api/servers/{id}` - Get specific server
- `PUT /api/servers/{id}` - Update server
- `DELETE /api/servers/{id}` - Delete server

### GPU Metrics
- `GET /api/gpu/metrics` - Get latest GPU metrics
- `GET /api/gpu/metrics/{host}` - Get metrics by host
- `GET /api/gpu/hosts` - Get all hosts
- `GET /api/gpu/metrics/overall/by-gpu-name` - Get overall metrics by GPU name

### GPU Servers
- `GET /api/gpu-servers` - Get all GPU servers
- `POST /api/gpu-servers` - Create GPU server
- `GET /api/gpu-servers/{id}` - Get specific GPU server
- `PUT /api/gpu-servers/{id}` - Update GPU server
- `DELETE /api/gpu-servers/{id}` - Delete GPU server
- `PATCH /api/gpu-servers/{id}/usage-limit` - Update usage limit
- `PATCH /api/gpu-servers/{id}/alert-emails` - Update alert emails

### Users
- `GET /api/users/me` - Get current user
- `GET /api/users/` - Get all users
- `GET /api/users/roles` - Get available roles
- `POST /api/users/` - Create user
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user

### Azure Users
- `GET /api/azure/users/all` - Get all Azure users
- `GET /api/azure/users/search` - Search Azure users
- `GET /api/azure/users/by-email/{email}` - Get user by email
- `GET /api/azure/users/{id}/photo` - Get user photo

### Projects
- `GET /api/projects` - Get all project categories
- `POST /api/projects` - Create project category
- `DELETE /api/projects/{id}` - Delete project category

### WebSocket
- `ws://localhost:8080/ws` - WebSocket connection for real-time updates

## 🔐 Authentication

The application uses Azure AD (Microsoft Entra ID) for authentication:

1. **Azure AD Setup**:
   - Register an application in Azure Portal
   - Configure redirect URIs
   - Set up API permissions
   - Get Client ID and Tenant ID

2. **User Roles**:
   - **admin**: Full access to all features
   - **owner**: Full access to all features
   - **editor**: Can create, edit, and delete resources
   - **viewer**: Read-only access

3. **Token Management**:
   - Tokens are automatically managed by MSAL
   - Stored in sessionStorage
   - Automatically refreshed when needed

## 📡 WebSocket Messages

### Health Update Message
```json
{
  "type": "health_update",
  "data": {
    "url_id": 1,
    "status": "online",
    "response_time": 245,
    "status_code": 200,
    "checked_at": "2025-01-15T10:30:00",
    "error_message": null
  }
}
```

### GPU Update Message
```json
{
  "type": "gpu_update",
  "data": {
    "host": "localhost",
    "gpu_name": "NVIDIA GeForce RTX 3090",
    "utilization": 85,
    "memory_used": 2048,
    "memory_total": 24576,
    "temperature": 75
  }
}
```

## 🛠️ Development

### Project Structure

```
monitor-tool/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── requirements.txt        # Python dependencies
│   ├── home/
│   │   ├── auth/               # Azure AD authentication
│   │   ├── config/             # Configuration
│   │   ├── database/           # Database initialization
│   │   ├── models/             # Data models and schemas
│   │   ├── routes/             # API routes
│   │   └── services/           # Background services
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── services/           # API and WebSocket services
│   │   ├── styles/             # CSS styles
│   │   ├── App.js              # Main app component
│   │   └── authConfig.js       # Azure AD config
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

### Key Technologies

- **Backend**: FastAPI, Python, PostgreSQL, WebSocket, APScheduler
- **Frontend**: React, Azure MSAL, WebSocket
- **Authentication**: Azure AD (Microsoft Entra ID)
- **Database**: PostgreSQL
- **Real-time**: WebSocket for live updates

## 🐛 Troubleshooting

### Database Connection Error

**Error**: `Error connecting to database`

**Solution**: 
- Verify PostgreSQL is running
- Check database credentials in `.env`
- Ensure database exists

### Authentication Issues

**Error**: `401 Unauthorized` or `403 Forbidden`

**Solution**:
- Verify Azure AD configuration in `authConfig.js`
- Check that user has proper role assigned
- Ensure redirect URI matches Azure AD configuration

### WebSocket Connection Failed

**Error**: `WebSocket connection failed`

**Solution**:
- Verify backend is running on correct port
- Check `REACT_APP_WS_URL` in frontend `.env`
- Ensure firewall allows WebSocket connections

### Port Already in Use

**Error**: `Address already in use`

**Solution**: 
- Change port in `.env` file
- Or stop the process using the port:
  ```bash
  # Find process
  lsof -i :8080
  # Kill process
  kill -9 <PID>
  ```

## 📝 Example API Requests

### Create URL

```bash
curl -X POST "http://localhost:8080/api/urls" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "project_name": "My API",
    "url": "https://api.example.com",
    "environment": "production",
    "project_category": "Backend",
    "server_ip": "localhost",
    "port": 443,
    "server_location": "India"
  }'
```

### Get Health History

```bash
curl "http://localhost:8080/api/health/url/1/history?minutes=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Statistics

```bash
curl "http://localhost:8080/api/health/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📄 License

[Specify your license here]

## 👥 Contributors

[Add contributor information]

## 📧 Support

For issues and questions, please create an issue or contact the development team.
