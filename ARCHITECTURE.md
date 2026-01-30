# 🏗️ Application Architecture

## Project Structure

```
whook2/
├── app/                          # Main application package
│   ├── __init__.py              # Package initialization
│   ├── core/                    # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration settings
│   │   ├── database.py         # Database connection
│   │   └── redis_client.py     # Redis connection
│   ├── models/                  # Database models
│   │   ├── __init__.py
│   │   ├── base.py             # SQLAlchemy base
│   │   ├── user.py             # User model
│   │   └── webhook.py          # Webhook models
│   ├── routes/                  # API routes
│   │   ├── __init__.py
│   │   ├── auth.py             # Authentication routes
│   │   ├── webhooks.py         # Webhook routes
│   │   └── websocket.py        # WebSocket routes
│   └── utils/                   # Utility functions
│       ├── __init__.py
│       ├── auth.py             # Auth helpers
│       └── websocket.py        # WebSocket manager
├── static/                      # Static files
│   ├── css/                    # Stylesheets
│   │   ├── index.css
│   │   ├── login.css
│   │   └── webhook_details.css
│   └── js/                     # JavaScript files
│       ├── index.js
│       └── webhook_details.js
├── templates/                   # HTML templates
│   ├── index.html
│   ├── login.html
│   ├── settings.html
│   └── webhook_details.html
├── main.py                      # Application entry point
├── worker.py                    # Background worker
├── init_db.py                   # Database initialization
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables
├── docker-compose.yml           # Docker services
└── README.md                    # Documentation
```

## Module Descriptions

### 📦 app/core/

**Purpose:** Core application configuration and connections

#### config.py
- Loads environment variables
- Defines application settings
- Centralizes configuration management

```python
from app.core.config import settings

# Access settings
database_url = settings.DATABASE_URL
debug_mode = settings.DEBUG
```

#### database.py
- Creates SQLAlchemy engine
- Configures connection pooling
- Provides database session dependency

```python
from app.core import SessionLocal, get_db

# Use in routes
db = SessionLocal()
# or
def my_route(db: Session = Depends(get_db)):
    pass
```

#### redis_client.py
- Initializes Redis connection
- Creates RQ queue
- Sets up pub/sub for WebSocket

```python
from app.core import redis_conn, queue, pubsub

# Enqueue job
job = queue.enqueue('worker.function', args)

# Publish message
redis_conn.publish('channel', message)
```

### 📊 app/models/

**Purpose:** Database models and schemas

#### base.py
- SQLAlchemy declarative base
- Shared by all models

#### user.py
- User model
- Google OAuth integration
- User-webhook relationship

```python
from app.models import User

user = User(
    email="user@example.com",
    google_id="123456",
    name="John Doe"
)
```

#### webhook.py
- Webhook model
- WebhookRequest model
- Destination model
- Relationships and indexes

```python
from app.models import Webhook, WebhookRequest, Destination

webhook = Webhook(
    name="My Webhook",
    url="abc123",
    user_id=1
)
```

### 🛣️ app/routes/

**Purpose:** API endpoints and route handlers

#### auth.py
- Login page
- Google OAuth flow
- Callback handling
- Logout

**Routes:**
- `GET /login` - Login page
- `GET /auth/google` - Initiate OAuth
- `GET /auth/callback` - OAuth callback
- `GET /logout` - Logout

#### webhooks.py
- Webhook CRUD operations
- Webhook request handling
- Settings management
- Request details

**Routes:**
- `GET /` - Dashboard
- `POST /add_webhook` - Create webhook
- `POST /pause` - Toggle webhook status
- `POST /delete` - Delete webhook
- `POST /{path}` - Receive webhook
- `GET /{path}` - View webhook details
- `GET /settings/{id}` - Webhook settings

#### websocket.py
- WebSocket connection management
- Real-time updates
- Redis pub/sub listener

**Routes:**
- `WS /ws` - WebSocket endpoint

### 🔧 app/utils/

**Purpose:** Helper functions and utilities

#### auth.py
- `get_current_user()` - Get user from session
- `require_auth()` - Require authentication
- `get_or_create_user()` - User management

```python
from app.utils.auth import require_auth

@router.get("/protected")
def protected_route(request: Request):
    user = require_auth(request)
    # user is authenticated
```

#### websocket.py
- `ConnectionManager` - WebSocket connection pool
- `connect()` - Accept connection
- `disconnect()` - Remove connection
- `broadcast()` - Send to all clients

```python
from app.utils.websocket import ConnectionManager

manager = ConnectionManager()
await manager.connect(websocket)
await manager.broadcast({"type": "update"})
```

## Data Flow

### 1. Incoming Webhook Request

```
External Service
    ↓
POST /{webhook_url}
    ↓
webhooks.py: handle_webhook()
    ↓
Verify webhook exists
    ↓
Enqueue to Redis/RQ
    ↓
Return 202 Accepted
    ↓
worker.py: process_webhook_in_background()
    ↓
Save to database
    ↓
Publish to Redis pub/sub
    ↓
websocket.py: redis_listener()
    ↓
Broadcast to WebSocket clients
    ↓
Frontend updates in real-time
```

### 2. User Authentication

```
User visits /
    ↓
Check session
    ↓
No session? → Redirect to /login
    ↓
Click "Continue with Google"
    ↓
auth.py: auth_google()
    ↓
Redirect to Google OAuth
    ↓
User grants permission
    ↓
Google redirects to /auth/callback
    ↓
auth.py: auth_callback()
    ↓
Get user info from Google
    ↓
utils/auth.py: get_or_create_user()
    ↓
Store user in session
    ↓
Redirect to dashboard
```

### 3. Creating a Webhook

```
User clicks "Create Webhook"
    ↓
Enter webhook name
    ↓
POST /add_webhook
    ↓
webhooks.py: add_webhook()
    ↓
require_auth() - verify user
    ↓
Generate random URL
    ↓
Create Webhook in database
    ↓
Link to user_id
    ↓
Return webhook URL
    ↓
Frontend displays new webhook
```

## Database Schema

### User Table
```sql
CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture VARCHAR(500),
    google_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP DEFAULT NOW()
);
```

### Webhook Table
```sql
CREATE TABLE webhook (
    id SERIAL PRIMARY KEY,
    url VARCHAR(200) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    status BOOLEAN DEFAULT TRUE,
    transformation_script TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    user_id INTEGER REFERENCES "user"(id) ON DELETE CASCADE
);
```

### WebhookRequest Table
```sql
CREATE TABLE webhook_request (
    id SERIAL PRIMARY KEY,
    webhook_id INTEGER REFERENCES webhook(id) ON DELETE CASCADE,
    headers TEXT NOT NULL,
    body TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

### Destination Table
```sql
CREATE TABLE destination (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) NOT NULL,
    webhook_id INTEGER REFERENCES webhook(id) ON DELETE CASCADE
);
```

## Configuration

### Environment Variables

All configuration is managed through `.env` file:

```env
# Database
DATABASE_URL=postgresql://user:pass@host:port/db
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://localhost:6379/0

# Application
APP_HOST=0.0.0.0
APP_PORT=5000
DEBUG=True

# Security
SECRET_KEY=your-secret-key

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
REDIRECT_URI=http://localhost:5000/auth/callback

# Data Retention
WEBHOOK_RETENTION_DAYS=30
```

### Accessing Configuration

```python
from app.core.config import settings

# Use settings anywhere
if settings.DEBUG:
    print("Debug mode enabled")

database_url = settings.DATABASE_URL
```

## Dependency Injection

### Database Session

```python
from fastapi import Depends
from app.core import get_db
from sqlalchemy.orm import Session

@router.get("/example")
def example_route(db: Session = Depends(get_db)):
    # db is automatically provided and closed
    webhooks = db.query(Webhook).all()
    return webhooks
```

### Authentication

```python
from app.utils.auth import require_auth

@router.post("/protected")
def protected_route(request: Request):
    user = require_auth(request)
    # user is guaranteed to be authenticated
    return {"user_id": user['id']}
```

## Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Test fixtures
├── test_auth.py             # Authentication tests
├── test_webhooks.py         # Webhook tests
└── test_models.py           # Model tests
```

## Development Workflow

### 1. Start Development Environment

```bash
# Start services
docker-compose up -d

# Initialize database
python init_db.py

# Start application
python main.py

# Start worker (separate terminal)
python worker.py
```

### 2. Making Changes

1. **Models:** Edit files in `app/models/`
2. **Routes:** Edit files in `app/routes/`
3. **Config:** Edit `app/core/config.py`
4. **Templates:** Edit files in `templates/`
5. **Styles:** Edit files in `static/css/`

### 3. Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False` in `.env`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure production database
- [ ] Set up HTTPS
- [ ] Configure OAuth for production domain
- [ ] Set up monitoring
- [ ] Configure logging
- [ ] Set up backups
- [ ] Configure rate limiting
- [ ] Enable CORS if needed

### Docker Deployment

```bash
# Build image
docker build -t whook:latest .

# Run container
docker run -d \
  --name whook \
  -p 5000:5000 \
  --env-file .env \
  whook:latest
```

## Monitoring

### Logging

```python
import logging

logger = logging.getLogger(__name__)
logger.info("Webhook received")
logger.error("Error processing webhook", exc_info=True)
```

### Metrics

- Request count per webhook
- Response times
- Error rates
- Active WebSocket connections
- Queue length

## Security

### Authentication
- Session-based with secure cookies
- Google OAuth 2.0
- CSRF protection (built into Starlette)

### Authorization
- User ownership verification
- Route-level authentication
- Resource-level access control

### Data Protection
- User data isolation
- Cascade deletes
- SQL injection prevention (SQLAlchemy)
- XSS prevention (Jinja2 auto-escaping)

## Performance

### Optimizations
- Connection pooling (20 base + 40 overflow)
- Composite indexes on frequently queried columns
- Redis caching for hot data
- Background job processing
- Pagination on list endpoints

### Scaling
- Horizontal: Add more workers
- Vertical: Increase pool size
- Database: Read replicas
- Redis: Redis Cluster

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Make sure you're in the project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Database Connection:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Test connection
psql -h localhost -U webhook_user -d webhooks_db
```

**Redis Connection:**
```bash
# Check if Redis is running
docker-compose ps redis

# Test connection
redis-cli ping
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes following the architecture
4. Add tests
5. Submit pull request

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Redis Documentation](https://redis.io/documentation)
- [RQ Documentation](https://python-rq.org/)
