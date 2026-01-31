#!/usr/bin/env python3
"""
Test script to verify webhook processing reliability.
Sends N requests to a webhook URL and checks how many were saved to DB.
"""

import argparse
import requests
import time
import sys
import concurrent.futures
from threading import Lock
from dotenv import load_dotenv

load_dotenv()

# Thread-safe counters
success_count = 0
fail_count = 0
counter_lock = Lock()


def send_single_request(args):
    """Send a single request (for use with ThreadPoolExecutor)"""
    global success_count, fail_count
    webhook_url, request_num, total = args
    
    try:
        payload = {"test": True, "request_number": request_num}
        resp = requests.post(
            webhook_url,
            json=payload,
            params={"test_id": request_num},
            timeout=30
        )
        with counter_lock:
            if resp.status_code in [200, 201, 202]:
                success_count += 1
                if request_num % 100 == 0 or request_num == total:
                    print(f"  ✓ Request {request_num}/{total} - Status: {resp.status_code}")
                return True
            else:
                fail_count += 1
                print(f"  ✗ Request {request_num}/{total} - Status: {resp.status_code}")
                return False
    except Exception as e:
        with counter_lock:
            fail_count += 1
        print(f"  ✗ Request {request_num}/{total} - Error: {e}")
        return False


def send_requests(webhook_url: str, count: int, delay: float = 0.1, threads: int = 1):
    """Send N requests to the webhook URL"""
    global success_count, fail_count
    success_count = 0
    fail_count = 0
    
    print(f"\n📤 Sending {count} requests to {webhook_url}...")
    if threads > 1:
        print(f"   Using {threads} concurrent threads")
    
    if threads == 1:
        # Sequential mode
        for i in range(count):
            send_single_request((webhook_url, i + 1, count))
            if delay > 0 and i < count - 1:
                time.sleep(delay)
    else:
        # Concurrent mode
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            args_list = [(webhook_url, i + 1, count) for i in range(count)]
            list(executor.map(send_single_request, args_list))
    
    print(f"\n📊 Send Results: {success_count} successful, {fail_count} failed")
    return success_count


def check_db_count(webhook_path: str) -> int:
    """Check how many requests are in the database for this webhook"""
    from app.core import SessionLocal
    from app.models import Webhook, WebhookRequest
    
    db = SessionLocal()
    try:
        webhook = db.query(Webhook).filter(Webhook.url == webhook_path).first()
        if not webhook:
            print(f"❌ Webhook not found: {webhook_path}")
            return -1
        
        count = db.query(WebhookRequest).filter(
            WebhookRequest.webhook_id == webhook.id
        ).count()
        return count
    finally:
        db.close()


def check_queue_status():
    """Check RQ queue status"""
    from redis import Redis
    from rq import Queue
    from rq.registry import FailedJobRegistry, StartedJobRegistry
    from app.core.config import settings
    
    conn = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    q = Queue(connection=conn)
    
    pending = len(q.job_ids)
    failed_registry = FailedJobRegistry(queue=q)
    started_registry = StartedJobRegistry(queue=q)
    
    failed = len(failed_registry.get_job_ids())
    started = len(started_registry.get_job_ids())
    
    conn.close()
    
    return {
        'pending': pending,
        'started': started,
        'failed': failed
    }


def main():
    parser = argparse.ArgumentParser(description='Test webhook processing reliability')
    parser.add_argument('webhook_url', help='Full webhook URL (e.g., http://localhost:5000/abc123)')
    parser.add_argument('count', type=int, help='Number of requests to send')
    parser.add_argument('--delay', type=float, default=0.1, help='Delay between requests in seconds (default: 0.1, ignored with --threads)')
    parser.add_argument('--wait', type=int, default=5, help='Seconds to wait for processing (default: 5)')
    parser.add_argument('--threads', type=int, default=1, help='Number of concurrent threads (default: 1)')
    
    args = parser.parse_args()
    
    # Extract webhook path from URL
    webhook_path = args.webhook_url.rstrip('/').split('/')[-1]
    if '?' in webhook_path:
        webhook_path = webhook_path.split('?')[0]
    
    print(f"🔗 Webhook URL: {args.webhook_url}")
    print(f"📍 Webhook path: {webhook_path}")
    print(f"🔢 Requests: {args.count}")
    if args.threads > 1:
        print(f"🧵 Threads: {args.threads}")
    
    # Get initial count
    initial_count = check_db_count(webhook_path)
    if initial_count < 0:
        sys.exit(1)
    print(f"📊 Initial DB count: {initial_count}")
    
    # Check initial queue status
    queue_before = check_queue_status()
    print(f"📋 Queue before: pending={queue_before['pending']}, started={queue_before['started']}, failed={queue_before['failed']}")
    
    # Send requests
    start_time = time.time()
    sent = send_requests(args.webhook_url, args.count, args.delay, args.threads)
    send_duration = time.time() - start_time
    print(f"⏱️  Send duration: {send_duration:.2f}s ({args.count / send_duration:.1f} req/s)")
    
    # Wait for processing
    print(f"\n⏳ Waiting up to {args.wait} seconds for jobs to process...")
    for i in range(args.wait):
        time.sleep(1)
        queue_status = check_queue_status()
        current_count = check_db_count(webhook_path)
        processed = current_count - initial_count
        print(f"  {i + 1}s: DB={processed}/{sent}, Queue: pending={queue_status['pending']}, started={queue_status['started']}, failed={queue_status['failed']}")
        
        # If all processed and queue empty, we're done
        if processed >= sent and queue_status['pending'] == 0 and queue_status['started'] == 0:
            break
    
    # Final count
    final_count = check_db_count(webhook_path)
    processed = final_count - initial_count
    queue_after = check_queue_status()
    
    print(f"\n{'=' * 50}")
    print(f"📊 RESULTS")
    print(f"{'=' * 50}")
    print(f"  Requests sent:      {sent}")
    print(f"  Requests in DB:     {processed}")
    print(f"  Missing:            {sent - processed}")
    print(f"  Queue pending:      {queue_after['pending']}")
    print(f"  Queue started:      {queue_after['started']}")
    print(f"  Queue failed:       {queue_after['failed']}")
    print(f"  Send rate:          {args.count / send_duration:.1f} req/s")
    print(f"{'=' * 50}")
    
    if processed == sent:
        print("✅ SUCCESS: All requests were processed!")
        return 0
    elif processed < sent:
        print(f"❌ FAILURE: {sent - processed} requests were lost!")
        return 1
    else:
        print(f"⚠️  UNEXPECTED: More requests in DB than sent (concurrent requests?)")
        return 0


if __name__ == '__main__':
    sys.exit(main())
