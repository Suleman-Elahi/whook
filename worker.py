import os
import json
import requests
from datetime import datetime
from redis import Redis
from rq import Worker, Queue
from flask_socketio import SocketIO
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import full_write_guard

# Import necessary components from your Flask app
from app import create_app, db, Webhook, WebhookRequest

# Get Redis connection URL from environment or use default
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Set up the connection
conn = Redis.from_url(redis_url)

# Create a queue
listen = ['default']
queue = Queue(connection=conn)

# Create a Socket.IO instance for the worker
socketio = SocketIO(message_queue=redis_url)

def process_webhook_in_background(webhook_id, headers, body):
    """Background task to process webhook request"""
    app = create_app()
    with app.app_context():
        try:
            # --- 1. Save the original request ---
            print(f"[Background] Processing webhook ID: {webhook_id}")
            new_request = WebhookRequest(
                webhook_id=webhook_id,
                headers=json.dumps(headers),
                body=body,
                timestamp=datetime.now().replace(microsecond=0)
            )
            db.session.add(new_request)
            db.session.commit()
            print(f"[Background] Saved original request with ID: {new_request.id}")

            # --- 2. Notify clients via Socket.IO ---
            socketio.emit('new_webhook_request', {
                'webhook_id': webhook_id,
                'request_id': new_request.id,
                'timestamp': datetime.now().isoformat()
            })
            print("[Background] Sent socket.io notification")

            # --- 3. Process transformation and forwarding ---
            webhook = Webhook.query.get(webhook_id)
            if not webhook:
                print(f"[Background] Webhook with ID {webhook_id} not found.")
                return

            transformed_body = body
            # Execute transformation script if it exists
            if webhook.transformation_script and webhook.transformation_script.strip():
                print("[Background] Transformation script found.")
                try:
                    print(f"[Background] Original body: {body}")
                    data = json.loads(body)
                    
                    # Set up the safe environment
                    script_globals = safe_globals.copy()
                    script_globals['_write_'] = full_write_guard

                    byte_code = compile_restricted(webhook.transformation_script, '<string>', 'exec')
                    local_env = {}
                    exec(byte_code, script_globals, local_env)
                    
                    transform_func = local_env.get('transform')
                    
                    if callable(transform_func):
                        print("[Background] 'transform' function found. Calling it.")
                        transformed_data = transform_func(data)
                        transformed_body = json.dumps(transformed_data)
                        print(f"[Background] Transformed body: {transformed_body}")
                    else:
                        print("[Background] 'transform' function not found or not callable in script. Skipping transformation.")

                except json.JSONDecodeError:
                    print("[Background] Warning: Request body is not valid JSON. Cannot apply transformation.")
                except Exception as e:
                    print(f"[Background] Error executing transformation script: {e}")
            else:
                print("[Background] No transformation script found. Skipping transformation.")
            
            # Forward to destination URLs if they exist
            if webhook.destinations:
                print(f"[Background] Forwarding to {len(webhook.destinations)} destinations.")
                for dest in webhook.destinations:
                    try:
                        # Forward original headers, but the transformed body
                        # Set a default content-type if not present
                        forward_headers = headers.copy()
                        if 'Content-Type' not in forward_headers:
                            forward_headers['Content-Type'] = 'application/json'
                            
                        requests.post(dest.url, data=transformed_body, headers=forward_headers, timeout=10)
                        print(f"[Background] Forwarded to {dest.url}")
                    except requests.RequestException as e:
                        print(f"[Background] Failed to forward to {dest.url}: {e}")

            return new_request.id

        except Exception as e:
            import traceback
            print(f"[Background] Error processing webhook: {str(e)}")
            traceback.print_exc()
            db.session.rollback()
            return None
        finally:
            db.session.remove()

if __name__ == '__main__':
    # Start a worker with the default queue
    worker = Worker([queue], connection=conn)
    worker.work()
