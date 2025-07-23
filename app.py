from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_cors import CORS, cross_origin
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.registry import StartedJobRegistry
from datetime import datetime
import random
import os, string, json

db = SQLAlchemy()
socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    
    # App configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///webhooks.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config['RQ_REDIS_URL'] = 'redis://localhost:6379/0'
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    
    # Initialize extensions
    db.init_app(app)
    
    # Configure Socket.IO with CORS and logging
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        logger=True,
        engineio_logger=True,
        async_mode='threading'
    )
    
    # Add Socket.IO event handlers
    @socketio.on('connect')
    def handle_connect():
        print('Client connected:', request.sid)
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected:', request.sid)
    
    return app

app = create_app()

# Initialize Redis connection
redis_conn = Redis.from_url('redis://localhost:6379')

# Initialize the queue
queue = Queue(connection=redis_conn)

# Initialize job registry
job_registry = StartedJobRegistry('default', connection=redis_conn)

class Webhook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.Boolean, default=True, nullable=False)
    transformation_script = db.Column(db.Text, nullable=True)
    requests = db.relationship(
        "WebhookRequest", cascade="all, delete-orphan", backref="webhook"
    )
    destinations = db.relationship(
        "Destination", cascade="all, delete-orphan", backref="webhook"
    )

class Destination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    webhook_id = db.Column(db.Integer, db.ForeignKey("webhook.id"), nullable=False)


class WebhookRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    webhook_id = db.Column(db.Integer, db.ForeignKey("webhook.id"), nullable=False)
    headers = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now().replace(microsecond=0))



with app.app_context():
    db.create_all()

@app.get("/")
def index():
    print("\n=== Rendering index page ===")
    try:
        webhooks = Webhook.query.all()
        print(f"Found {len(webhooks)} webhooks")
        
        for webhook in webhooks:
            count = WebhookRequest.query.filter_by(webhook_id=webhook.id).count()
            webhook.request_count = count
            print(f"Webhook {webhook.id} ({webhook.name}): {count} requests")
            
        return render_template("index.html", webhooks=webhooks)
        
    except Exception as e:
        import traceback
        print(f"Error in index route: {str(e)}")
        traceback.print_exc()
        return str(e), 500

@app.route("/add_webhook", methods=["POST"])
def add_webhook():
    data = request.json
    webhook_name = data.get("name")
    random_string = "".join(random.choices(string.ascii_letters + string.digits, k=10))
    webhook_url = f"http://127.1.1.0:5000/{random_string}"
    new_webhook = Webhook(url=random_string, name=webhook_name)

    with app.app_context():
        db.session.add(new_webhook)
        db.session.commit()

    return jsonify({"url": webhook_url, "name": webhook_name}), 201



@app.route("/<path:path>", methods=["POST"])
@cross_origin()
def handle_webhook(path):
    print(f"\n=== New Webhook Request ===")
    print(f"Path: {path}")
    print(f"Headers: {dict(request.headers)}")
    
    # Find the webhook
    webhook = Webhook.query.filter(Webhook.url == path).first()
    if not webhook:
        print(f"Webhook not found for path: {path}")
        return jsonify({"message": "Webhook not found"}), 404
        
    print(f"Found webhook: {webhook.name} (ID: {webhook.id}, Active: {webhook.status})")
    
    if not webhook.status:
        print("Webhook is paused")
        return jsonify({"message": "Webhook is paused"}), 200
    
    try:
        # Get request data
        headers = {k: v for k, v in request.headers.items()}
        body = request.get_data(as_text=True) or ""
        
        print(f"Request body: {body}")

        # Enqueue the background task
        job = queue.enqueue(
            'worker.process_webhook_in_background',
            webhook.id,
            headers,
            body,
            job_timeout=30,  # 30 seconds timeout
            result_ttl=3600  # Keep results for 1 hour
        )
        
        print(f"Enqueued job {job.id} for webhook {webhook.id}")
        
        # Return immediately with 202 Accepted
        return jsonify({
            "message": "Webhook received and queued for processing",
            "job_id": job.id,
            "status": "queued"
        }), 202
        
    except Exception as e:
        import traceback
        print(f"Error enqueuing webhook: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "Failed to process webhook"}), 500


@app.route("/settings/<string:webhook_id>", methods=["GET", "POST"])
def webhook_settings(webhook_id):
    webhook = Webhook.query.filter_by(url=webhook_id).first_or_404()
    if request.method == "POST":
        # Clear existing destinations
        Destination.query.filter_by(webhook_id=webhook.id).delete()

        # Add new destinations
        urls = request.form.get("destination_urls").split(',')
        for url in urls:
            if url.strip():
                new_destination = Destination(url=url.strip(), webhook_id=webhook.id)
                db.session.add(new_destination)

        # Update transformation script
        webhook.transformation_script = request.form.get("transformation_script")
        db.session.commit()
        return redirect(url_for("webhook_settings", webhook_id=webhook.url))

    destinations = ", ".join([d.url for d in webhook.destinations])
    return render_template("settings.html", webhook=webhook, destinations=destinations)

@app.route("/<string:path>")
def show_webhook(path):
    print(f"\n=== Showing webhook details for path: {path} ===")
    try:
        # Find the webhook by exact URL match
        webhook = Webhook.query.filter_by(url=path).first()
        if not webhook:
            print(f"Webhook not found for path: {path}")
            return "Webhook not found", 404
            
        print(f"Found webhook: {webhook.name} (ID: {webhook.id})")
        
        # Get all requests for this webhook
        requests = WebhookRequest.query.filter_by(webhook_id=webhook.id)\
                                    .order_by(WebhookRequest.timestamp.desc())\
                                    .all()
        
        print(f"Found {len(requests)} requests for webhook {webhook.id}")
        
        # Parse headers for display
        for req in requests:
            try:
                req.headers = json.loads(req.headers)
                print(f"Request {req.id} headers: {req.headers}")
            except json.JSONDecodeError:
                req.headers = {}
        
        return render_template("webhook_details.html", 
                             webhook=webhook, 
                             requests=requests)
                             
    except Exception as e:
        import traceback
        print(f"Error in show_webhook: {str(e)}")
        traceback.print_exc()
        return f"Error: {str(e)}", 500

@app.route("/webhook/request/<int:request_id>")
def show_request(request_id):
    req = WebhookRequest.query.get_or_404(request_id)
    return jsonify(
        {
            "headers": json.loads(req.headers),
            "body": req.body,
            "timestamp": req.timestamp,
        }
    )

@app.route("/pause", methods=["POST"])
def pause_webhook():
    data = request.json
    webhook_url = data["url"]
    webhook = Webhook.query.filter_by(url=webhook_url).first()
    if webhook:
        webhook.status = not webhook.status
        db.session.commit()
        return (
            jsonify(
                {
                    "message": "Webhook status updated successfully",
                    "status": webhook.status,
                }
            ),
            200,
        )
    else:
        return jsonify({"message": "Webhook not found"}), 404

@app.route("/delete", methods=["POST"])
def delete_webhook():
    data = request.json
    webhook_url = data["url"]
    webhook = Webhook.query.filter_by(url=webhook_url).first()
    print(webhook.id)
    webhookRequests = WebhookRequest.query.filter_by(webhook_id=webhook.id).delete()
    if webhook:
        db.session.delete(webhook)
        db.session.commit()
        return jsonify({"message": "Webhook deleted successfully"}), 200
    else:
        return jsonify({"message": "Webhook not found"}), 404

@app.route("/delete_request", methods=["POST"])
def delete_webhook_request():
    data = request.json
    wbhk_id = data["id"]
    webhookRequest = WebhookRequest.query.filter_by(id=wbhk_id).first()
    if webhookRequest:
        db.session.delete(webhookRequest)
        db.session.commit()
        return jsonify({"message": "Webhook deleted successfully"}), 200
    else:
        return jsonify({"message": "Webhook not found"}), 404

@app.route("/webhooks/delete_all", methods=["POST"])
def delete_all_webhooks():
    data = request.json
    webhook_url = data["webhook_id"]
    webhook = Webhook.query.filter_by(url=webhook_url).first()
    if not webhook:
        return jsonify({"message": "Webhook not found"}), 404
    try:
        num_deleted = WebhookRequest.query.filter_by(webhook_id=webhook.id).delete()
        db.session.commit()
        return jsonify({"message": f"Successfully deleted {num_deleted} webhooks."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {e}"}), 500

import json

@app.route("/results/<job_id>", methods=['GET'])
def get_results(job_id):

    job = queue.fetch_job(job_id)

    if job:
        print(type(job), job)

    else:
        return "Not yet finished", 202

@app.route('/debug/db-status')
def debug_db_status():
    """Debug endpoint to check database status"""
    try:
        # Check if tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        # Get webhook and request counts
        webhook_count = Webhook.query.count()
        request_count = WebhookRequest.query.count()
        
        return jsonify({
            'tables': tables,
            'webhook_count': webhook_count,
            'request_count': request_count,
            'database': app.config['SQLALCHEMY_DATABASE_URI']
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


