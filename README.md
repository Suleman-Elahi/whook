-----

# 📖 Whook: Self-Hosted Webhook Manager

Whook is a high-performance, self-hosted webhook management system built with **FastAPI** and **PostgreSQL**. Designed to handle millions of webhooks with real-time monitoring, background processing, Google SSO authentication, and multi-user support.

-----

## ✨ Features

  * **Google SSO Authentication:** Secure login with Google accounts
  * **Multi-User Support:** Each user has their own isolated webhooks
  * **High Performance:** PostgreSQL backend with connection pooling for millions of webhooks
  * **Real-time Updates:** WebSocket support for live webhook monitoring
  * **Background Processing:** Redis + RQ for async webhook handling
  * **Modern UI:** Clean, professional interface with Shoelace components
  * **Advanced Filtering:** Filter webhooks by status code and date range
  * **Payload Logging:** Stores all incoming webhook payloads for review and debugging
  * **Payload Forwarding:** Route received webhooks to multiple destination URLs
  * **JSON Transformation:** Customize webhook payloads before forwarding using user-defined code
  * **Data Retention:** Automatic cleanup of old webhook data
  * **Self-Hosted:** Full control over your data and environment

-----

## 🚀 Quick Start

### Automated Setup (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd whook2

# Run the setup script
./start.sh

# Start the application (in separate terminals)
python app.py      # Terminal 1
python worker.py   # Terminal 2
```

### Manual Setup

See [SETUP.md](SETUP.md) for detailed PostgreSQL setup instructions.

-----

## 📋 Requirements

  * Python 3.9+
  * Docker & Docker Compose (for PostgreSQL and Redis)
  * OR manually installed PostgreSQL 12+ and Redis 6+

-----

## 🔧 Configuration

Edit `.env` file to configure:

```env
DATABASE_URL=postgresql://webhook_user:webhook_pass@localhost:5432/webhooks_db
REDIS_URL=redis://localhost:6379/0
APP_PORT=5000
WEBHOOK_RETENTION_DAYS=30
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

-----

## 🛠️ Usage

### Creating a Webhook Endpoint

1. Click "Create New Webhook" button
2. Enter a descriptive name
3. Copy the generated unique URL
4. Use the URL to receive webhooks from external services

### Viewing Webhook Requests

1. Click on a webhook name from the dashboard
2. View all incoming requests in real-time
3. Filter by status code (200, 201, 400, 404, 500)
4. Filter by date range (Today, Yesterday, Last 7 days, Last 30 days)
5. Click on any request to see full details (headers, body, raw data)

### Configuring Payload Forwarding

1. Click the settings icon (⚙️) on a webhook
2. Add destination URLs (comma-separated for multiple destinations)
3. Optionally add a transformation script
4. Save settings

### JSON Transformation

Define custom Python functions to transform incoming JSON payloads before forwarding:

```python
def transform(data):
    # Create a new dictionary with selected data
    new_payload = {
        'event_type': data.get('type'),
        'user_id': data.get('user', {}).get('id'),
        'processed_at': datetime.now().isoformat(),
        'processed_by_script': True
    }
    
    # Add a summary field
    if 'message' in data:
        new_payload['summary'] = data['message'][:50] + '...'
    
    return new_payload
```

-----

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
│  (Browser)  │
└──────┬──────┘
       │ WebSocket
       ▼
┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│ PostgreSQL  │
│   Server    │     │  Database   │
│  (Port 5000)│     │ (Port 5432) │
└──────┬──────┘     └─────────────┘
       │
       │ Enqueue
       ▼
┌─────────────┐     ┌─────────────┐
│    Redis    │────▶│  RQ Worker  │
│    Queue    │     │ (Background)│
│ (Port 6379) │     │ Processing  │
└─────────────┘     └─────────────┘
       │
       │ Pub/Sub
       └──────────────┐
                      │
                      ▼
              ┌─────────────┐
              │  WebSocket  │
              │  Broadcast  │
              └─────────────┘
```

-----

## 📊 Performance & Scalability

Optimized for high throughput:

- **Connection Pooling:** 20 base connections, 40 overflow
- **Indexed Queries:** Composite indexes on webhook_id + timestamp
- **Redis Caching:** Hot data cached for fast access
- **Background Jobs:** Non-blocking webhook processing
- **Data Retention:** Automatic cleanup of old data (configurable)
- **Horizontal Scaling:** Add more workers for increased throughput

**Capacity:**
- Single server: 100K-500K webhooks/day
- With optimizations: 1M+ webhooks/day
- Multi-server: Unlimited (with load balancer)

-----

## 🔒 Security Recommendations

Before deploying to production:

- ✅ Change default passwords in `.env`
- ✅ Use SSL/TLS for database connections
- ✅ Implement authentication for web interface
- ✅ Add rate limiting for webhook endpoints
- ✅ Enable HTTPS with valid certificates
- ✅ Set up firewall rules
- ✅ Regular security updates

-----

## 🛠️ Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
python init_db.py

# Start development server
python app.py

# Start worker
python worker.py
```

-----

## 📝 Services

When running with Docker Compose:

- **Webhook Manager:** http://localhost:5000
- **pgAdmin:** http://localhost:5050 (admin@webhooks.local / admin)
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

-----



## 🤝 Contributing

Contributions are welcome\! If you'd like to contribute, please follow these steps:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/AmazingFeature`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
5.  Push to the branch (`git push origin feature/AmazingFeature`).
6.  Open a Pull Request.

-----

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

-----

## ❓ Support

If you have any questions or encounter issues, please open an issue on the GitHub repository.

-----
