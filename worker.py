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
import time
import csv

load_dotenv()

logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from app.models import Webhook, WebhookRequest

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///wh.db')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '10'))

if DATABASE_URL.startswith("sqlite"):
    worker_engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30},
        echo=False
    )
else:
    worker_pool_size = max(2, DB_POOL_SIZE // 4)
    worker_max_overflow = max(5, DB_MAX_OVERFLOW // 4)
    worker_engine = create_engine(
        DATABASE_URL,
        pool_size=worker_pool_size,
        max_overflow=worker_max_overflow,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_timeout=30,
        echo=False
    )

WorkerSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=worker_engine)

conn = Redis.from_url(REDIS_URL, decode_responses=False)
pubsub_conn = Redis.from_url(REDIS_URL, decode_responses=True)
queue = Queue(connection=conn)


def forward_to_destination(dest_url, transformed_body, headers):
    """Forward webhook to a single destination"""
    try:
        forward_headers = {k: v for k, v in headers.items() if k.lower() not in ['host', 'content-length']}
        if 'content-type' not in [k.lower() for k in forward_headers.keys()]:
            forward_headers['Content-Type'] = 'application/json'
        
        resp = requests.post(dest_url, data=transformed_body, headers=forward_headers, timeout=10)
        return {'url': dest_url, 'status': resp.status_code, 'success': True}
    except requests.RequestException as e:
        logger.error(f"Forward failed: {dest_url} - {e}")
        return {'url': dest_url, 'error': str(e), 'success': False}


def process_webhook_in_background(webhook_id, headers, body, query_params=None):
    """Background task to process webhook request"""
    from sqlalchemy.orm import joinedload
    from contextlib import contextmanager
    
    @contextmanager
    def get_db_session():
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
            webhook = db.query(Webhook).options(joinedload(Webhook.destinations)).filter(Webhook.id == webhook_id).first()
            
            if not webhook:
                logger.error(f"Webhook {webhook_id} not found")
                return None
            
            query_params_json = json.dumps(query_params) if query_params else None
            
            new_request = WebhookRequest(
                webhook_id=webhook_id,
                headers=json.dumps(headers),
                body=body,
                query_params=query_params_json,
                timestamp=datetime.utcnow()
            )
            db.add(new_request)
            db.flush()
            
            request_id = new_request.id
            webhook_url = webhook.url
            request_timestamp = new_request.timestamp.isoformat()
            destination_urls = [dest.url for dest in webhook.destinations]
            transformation_script = webhook.transformation_script

        # Notify clients
        try:
            notification = {
                'type': 'new_webhook_request',
                'webhook_id': webhook_id,
                'webhook_url': webhook_url,
                'request_id': request_id,
                'timestamp': request_timestamp,
                'body_length': len(body) if body else 0
            }
            pubsub_conn.publish('webhook_events', json.dumps(notification))
        except Exception:
            pass

        # Transform body if script exists
        transformed_body = body
        if transformation_script and transformation_script.strip():
            try:
                data = json.loads(body)
                script_globals = safe_globals.copy()
                script_globals.update({'json': json, 'time': time, 'csv': csv})
                script_globals['_write_'] = full_write_guard

                byte_code = compile_restricted(transformation_script, '<string>', 'exec')
                local_env = {}
                exec(byte_code, script_globals, local_env)
                
                transform_func = local_env.get('transform')
                if callable(transform_func):
                    transformed_data = transform_func(data)
                    transformed_body = json.dumps(transformed_data)
            except Exception as e:
                logger.warning(f"Transform error: {e}")
        
        # Queue forwarding jobs
        for dest_url in destination_urls:
            try:
                queue.enqueue(
                    'worker.forward_to_destination',
                    dest_url,
                    transformed_body,
                    headers,
                    job_timeout=30,
                    result_ttl=3600
                )
            except Exception as e:
                logger.error(f"Queue forward failed: {e}")

        return request_id

    except Exception as e:
        logger.error(f"Process webhook error: {e}")
        return None


if __name__ == '__main__':
    worker = Worker([queue], connection=conn, log_job_description=False)
    worker.work(with_scheduler=False)
