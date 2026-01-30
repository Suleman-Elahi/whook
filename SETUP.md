# 🚀 PostgreSQL Setup Guide

## Quick Start with Docker (Recommended)

### 1. Start PostgreSQL and Redis
```bash
# Start all services (PostgreSQL, Redis, pgAdmin)
docker-compose up -d

# Check if services are running
docker-compose ps

# View logs
docker-compose logs -f postgres
```

### 2. Install Python Dependencies
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize Database
```bash
# Create tables and indexes
python init_db.py
```

### 4. Start the Application
```bash
# Terminal 1: Start FastAPI server
python app.py

# Terminal 2: Start RQ worker
python worker.py
```

### 5. Access the Application
- **Webhook Manager**: http://localhost:5000
- **pgAdmin** (Database UI): http://localhost:5050
  - Email: `admin@webhooks.local`
  - Password: `admin`

---

## Manual PostgreSQL Setup (Without Docker)

### 1. Install PostgreSQL
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql@16
brew services start postgresql@16

# Windows
# Download from: https://www.postgresql.org/download/windows/
```

### 2. Create Database and User
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Run these commands in psql:
CREATE DATABASE webhooks_db;
CREATE USER webhook_user WITH PASSWORD 'webhook_pass';
GRANT ALL PRIVILEGES ON DATABASE webhooks_db TO webhook_user;
\q
```

### 3. Update .env File
```bash
# Edit .env file with your database credentials
DATABASE_URL=postgresql://webhook_user:webhook_pass@localhost:5432/webhooks_db
```

### 4. Initialize Database
```bash
python init_db.py
```

---

## Configuration

### Environment Variables (.env)

```env
# Database
DATABASE_URL=postgresql://webhook_user:webhook_pass@localhost:5432/webhooks_db
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://localhost:6379/0

# Application
APP_HOST=0.0.0.0
APP_PORT=5000
DEBUG=True

# Data Retention
WEBHOOK_RETENTION_DAYS=30
```

---

## Database Management

### Using pgAdmin (Docker)
1. Open http://localhost:5050
2. Login with credentials above
3. Add server:
   - Name: `Webhooks DB`
   - Host: `postgres` (or `localhost` if not using Docker)
   - Port: `5432`
   - Database: `webhooks_db`
   - Username: `webhook_user`
   - Password: `webhook_pass`

### Using psql Command Line
```bash
# Connect to database
psql -h localhost -U webhook_user -d webhooks_db

# Useful commands:
\dt              # List tables
\d webhook       # Describe webhook table
\di              # List indexes
SELECT COUNT(*) FROM webhook_request;  # Count requests
```

---

## Performance Tuning

### PostgreSQL Configuration
Edit `postgresql.conf` for better performance:

```conf
# Memory Settings
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
work_mem = 16MB

# Connection Settings
max_connections = 100

# Write Performance
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

### Create Additional Indexes (if needed)
```sql
-- For faster webhook lookups by URL
CREATE INDEX CONCURRENTLY idx_webhook_url ON webhook(url);

-- For faster request filtering by timestamp
CREATE INDEX CONCURRENTLY idx_request_timestamp ON webhook_request(timestamp DESC);

-- For faster request counts
CREATE INDEX CONCURRENTLY idx_request_webhook_id ON webhook_request(webhook_id);
```

---

## Backup and Restore

### Backup Database
```bash
# Full backup
pg_dump -h localhost -U webhook_user webhooks_db > backup.sql

# Compressed backup
pg_dump -h localhost -U webhook_user webhooks_db | gzip > backup.sql.gz

# Docker backup
docker exec webhooks_postgres pg_dump -U webhook_user webhooks_db > backup.sql
```

### Restore Database
```bash
# Restore from backup
psql -h localhost -U webhook_user webhooks_db < backup.sql

# Docker restore
docker exec -i webhooks_postgres psql -U webhook_user webhooks_db < backup.sql
```

---

## Troubleshooting

### Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps postgres
# or
sudo systemctl status postgresql

# Check if port 5432 is open
netstat -an | grep 5432

# Test connection
psql -h localhost -U webhook_user -d webhooks_db -c "SELECT 1;"
```

### Reset Database
```bash
# Stop application
# Drop and recreate database
docker-compose down -v
docker-compose up -d
python init_db.py
```

### View Logs
```bash
# Docker logs
docker-compose logs -f postgres

# System PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-16-main.log
```

---

## Migration from SQLite

If you have existing SQLite data:

```bash
# 1. Export SQLite data
sqlite3 webhooks.db .dump > sqlite_dump.sql

# 2. Convert to PostgreSQL format (manual editing needed)
# Remove SQLite-specific syntax
# Adjust data types

# 3. Import to PostgreSQL
psql -h localhost -U webhook_user webhooks_db < converted_dump.sql
```

---

## Production Recommendations

1. **Use connection pooling** (already configured)
2. **Enable SSL** for database connections
3. **Set up replication** for high availability
4. **Configure automated backups**
5. **Monitor query performance** with pg_stat_statements
6. **Set up proper indexes** based on query patterns
7. **Use environment-specific .env files**
8. **Enable query logging** for debugging

---

## Next Steps

- ✅ Database is ready!
- 🔧 Configure data retention policies
- 📊 Set up monitoring (Prometheus + Grafana)
- 🔒 Add authentication and rate limiting
- 🚀 Deploy to production

For questions or issues, check the logs or open an issue on GitHub.
