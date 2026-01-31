from redis import Redis
from rq import Queue
from .config import settings

# Initialize Redis connection
redis_conn = Redis.from_url(settings.REDIS_URL, decode_responses=True)

# Initialize the queue (needs bytes for RQ)
queue_conn = Redis.from_url(settings.REDIS_URL, decode_responses=False)
queue = Queue(connection=queue_conn)

# Redis pubsub for worker communication - subscribe lazily
pubsub = None

def get_pubsub():
    """Get or create pubsub instance"""
    global pubsub
    if pubsub is None:
        pubsub = redis_conn.pubsub()
        pubsub.subscribe('webhook_events')
    return pubsub
