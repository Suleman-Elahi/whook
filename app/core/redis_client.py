from redis import Redis
from rq import Queue
from .config import settings

# Initialize Redis connection
redis_conn = Redis.from_url(settings.REDIS_URL, decode_responses=False)

# Initialize the queue
queue = Queue(connection=redis_conn)

# Redis pubsub for worker communication
pubsub = redis_conn.pubsub()
pubsub.subscribe('webhook_events')
