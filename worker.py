import os
import json
import requests
import logging
from datetime import datetime
from redis import Redis
from rq import Worker, Queue
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import full_write_guard
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models only
from app.models import Webhook, WebhookRequest

# Get config from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///wh.db')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '10'))

# Create worker's own database engine with proper connection handling
if DATABASE_URL.startswith("sqlite"):
    worker_engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30},
        echo=False
    )
else:
    # MySQL/MariaDB or PostgreSQL - use smaller pool for worker
    worker_pool_size = max(2, DB_POOL_SIZE // 4)  # Use 1/4 of main pool
    worker_max_overflow = max(5, DB_MAX_OVERFLOW // 4)
    
    worker_engine = create_engine(
        DATABASE_URL,
        pool_size=worker_pool_size,
        max_overflow=worker_max_overflow,
        pool_pre_ping=True,  # Test connections before using
        pool_recycle=300,    # Recycle connections every 5 minutes
        pool_timeout=30,     # Wait up to 30 seconds for a connection
        echo=False
    )
    logger.info(f"Worker DB pool: size={worker_pool_size}, max_overflow={worker_max_overflow}")

WorkerSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=worker_engine)

# Set up Redis connections
conn = Redis.from_url(REDIS_URL, decode_responses=False)
pubsub_conn = Redis.from_url(REDIS_URL, decode_responses=True)

# Create a queue
queue = Queue(connection=conn)


def forward_to_destination(dest_url, transformed_body, headers):
    """Forward webhook to a single destination"""
    try:
        forward_headers = {k: v for k, v in headers.items() if k.lower() not in ['host', 'content-length']}
        if 'content-type' not in [k.lower() for k in forward_headers.keys()]:
            forward_headers['Content-Type'] = 'application/json'
        
        logger.info(f"Forwarding to {dest_url}")
        resp = requests.post(dest_url, data=transformed_body, headers=forward_headers, timeout=10)
        logger.info(f"Forwarded to {dest_url} - Status: {resp.status_code}")
        return {'url': dest_url, 'status': resp.status_code, 'success': True}
    except requests.RequestException as e:
        logger.error(f"Failed to forward to {dest_url}: {e}")
        return {'url': dest_url, 'error': str(e), 'success': False}


def process_webhook_in_background(webhook_id, headers, body, query_params=None):
    """Background task to process webhook request"""
    logger.info(f"Starting to process webhook ID: {webhook_id}, query_params: {query_params}")
    
    from sqlalchemy.orm import joinedload
    from contextlib import contextmanager
    
    @contextmanager
    def get_db_session():
        """Context manager for database sessions"""
        session = WorkerSessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    try:
        with get_db_session() as db:
            # --- 0. Get webhook with destinations eagerly loaded ---
            webhook = db.query(Webhook).options(joinedload(Webhook.destinations)).filter(Webhook.id == webhook_id).first()
            
            if not webhook:
                logger.error(f"Webhook with ID {webhook_id} not found.")
                return None
            
            logger.info(f"Found webhook: {webhook.name} (ID: {webhook.id})")
            
            # --- 1. Save the original request ---
            query_params_json = None
            if query_params:
                try:
                    query_params_json = json.dumps(query_params)
                except Exception as e:
                    logger.error(f"Error serializing query_params: {e}")
            
            new_request = WebhookRequest(
                webhook_id=webhook_id,
                headers=json.dumps(headers),
                body=body,
                query_params=query_params_json,
                timestamp=datetime.utcnow()
            )
            db.add(new_request)
            db.flush()  # Get the ID without committing yet
            
            request_id = new_request.id
            webhook_url = webhook.url
            request_timestamp = new_request.timestamp.isoformat()
            
            # Get destinations before closing session
            destination_urls = [dest.url for dest in webhook.destinations]
            transformation_script = webhook.transformation_script
            
            logger.info(f"Saved request with ID: {request_id}")

        # --- 2. Notify clients via Redis pub/sub (outside db session) ---
        try:
            notification = {
                'type': 'new_webhook_request',
                'webhook_id': webhook_id,
                'webhook_url': webhook_url,
                'request_id': request_id,
                'timestamp': request_timestamp
            }
            pubsub_conn.publish('webhook_events', json.dumps(notification))
        except Exception as e:
            logger.error(f"Error publishing notification: {e}")

        # --- 3. Process transformation ---
        transformed_body = body
        if transformation_script and transformation_script.strip():
            try:
                data = json.loads(body)
                
                script_globals = safe_globals.copy()
                script_globals['_write_'] = full_write_guard

                byte_code = compile_restricted(transformation_script, '<string>', 'exec')
                local_env = {}
                exec(byte_code, script_globals, local_env)
                
                transform_func = local_env.get('transform')
                
                if callable(transform_func):
                    transformed_data = transform_func(data)
                    transformed_body = json.dumps(transformed_data)

            except json.JSONDecodeError:
                logger.warning("Request body is not valid JSON. Skipping transformation.")
            except Exception as e:
                logger.error(f"Error executing transformation script: {e}")
        
        # --- 4. Queue forwarding to each destination URL ---
        logger.info(f"Webhook has {len(destination_urls)} destinations: {destination_urls}")
        
        for dest_url in destination_urls:
            try:
                job = queue.enqueue(
                    'worker.forward_to_destination',
                    dest_url,
                    transformed_body,
                    headers,
                    job_timeout=30,
                    result_ttl=3600
                )
                logger.info(f"Queued forwarding job {job.id} for destination: {dest_url}")
            except Exception as e:
                logger.error(f"Failed to queue forwarding to {dest_url}: {e}")

        return request_id

    except Exception as e:
        logger.exception(f"Error processing webhook: {e}")
        return None


if __name__ == '__main__':
    # Start a worker with the default queue
    # Log failed jobs for debugging
    from rq import SimpleWorker
    
    worker = Worker(
        [queue], 
        connection=conn,
        log_job_description=True
    )
    worker.work(with_scheduler=False)
