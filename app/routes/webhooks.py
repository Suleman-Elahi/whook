from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.models import Webhook, WebhookRequest, Destination
from app.core import SessionLocal, queue
from app.utils.auth import get_current_user, require_auth
import random
import string
import json

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home page - requires authentication"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    print("\n=== Rendering index page ===")
    try:
        db = SessionLocal()
        webhooks = db.query(Webhook).filter(Webhook.user_id == user['id']).all()
        print(f"Found {len(webhooks)} webhooks for user {user['email']}")
        
        for webhook in webhooks:
            count = db.query(WebhookRequest).filter(WebhookRequest.webhook_id == webhook.id).count()
            webhook.request_count = count
            
            # Get the most recent request timestamp
            last_request = db.query(WebhookRequest.timestamp)\
                .filter(WebhookRequest.webhook_id == webhook.id)\
                .order_by(WebhookRequest.timestamp.desc())\
                .first()
            webhook.last_activity = last_request[0] if last_request else None
            
            print(f"Webhook {webhook.id} ({webhook.name}): {count} requests, last activity: {webhook.last_activity}")
        
        db.close()
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "webhooks": webhooks,
            "user": user
        })
        
    except Exception as e:
        import traceback
        print(f"Error in index route: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add_webhook")
async def add_webhook(request: Request):
    user = require_auth(request)
    
    data = await request.json()
    webhook_name = data.get("name")
    random_string = "".join(random.choices(string.ascii_letters + string.digits, k=10))
    webhook_url = f"http://127.1.1.0:5000/{random_string}"
    
    db = SessionLocal()
    new_webhook = Webhook(
        url=random_string, 
        name=webhook_name,
        user_id=user['id']
    )
    db.add(new_webhook)
    db.commit()
    db.close()
    
    return JSONResponse({"url": webhook_url, "name": webhook_name}, status_code=201)


@router.post("/pause")
async def pause_webhook(request: Request):
    user = require_auth(request)
    data = await request.json()
    webhook_url = data["url"]
    
    db = SessionLocal()
    webhook = db.query(Webhook).filter(
        Webhook.url == webhook_url,
        Webhook.user_id == user['id']
    ).first()
    
    if webhook:
        webhook.status = not webhook.status
        db.commit()
        result = {
            "message": "Webhook status updated successfully",
            "status": webhook.status,
        }
        db.close()
        return JSONResponse(result, status_code=200)
    else:
        db.close()
        raise HTTPException(status_code=404, detail="Webhook not found")


@router.post("/delete")
async def delete_webhook(request: Request):
    user = require_auth(request)
    data = await request.json()
    webhook_url = data["url"]
    
    db = SessionLocal()
    webhook = db.query(Webhook).filter(
        Webhook.url == webhook_url,
        Webhook.user_id == user['id']
    ).first()
    
    if webhook:
        db.query(WebhookRequest).filter(WebhookRequest.webhook_id == webhook.id).delete()
        db.delete(webhook)
        db.commit()
        db.close()
        return JSONResponse({"message": "Webhook deleted successfully"}, status_code=200)
    else:
        db.close()
        raise HTTPException(status_code=404, detail="Webhook not found")


@router.post("/delete_request")
async def delete_webhook_request(request: Request):
    user = require_auth(request)
    data = await request.json()
    wbhk_id = data["id"]
    
    db = SessionLocal()
    webhookRequest = db.query(WebhookRequest).filter(WebhookRequest.id == wbhk_id).first()
    
    if webhookRequest:
        # Verify ownership
        webhook = db.query(Webhook).filter(
            Webhook.id == webhookRequest.webhook_id,
            Webhook.user_id == user['id']
        ).first()
        
        if not webhook:
            db.close()
            raise HTTPException(status_code=403, detail="Forbidden")
        
        db.delete(webhookRequest)
        db.commit()
        db.close()
        return JSONResponse({"message": "Webhook request deleted successfully"}, status_code=200)
    else:
        db.close()
        raise HTTPException(status_code=404, detail="Webhook request not found")


@router.post("/webhooks/delete_all")
async def delete_all_webhooks(request: Request):
    user = require_auth(request)
    data = await request.json()
    webhook_url = data["webhook_id"]
    
    db = SessionLocal()
    webhook = db.query(Webhook).filter(
        Webhook.url == webhook_url,
        Webhook.user_id == user['id']
    ).first()
    
    if not webhook:
        db.close()
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    try:
        num_deleted = db.query(WebhookRequest).filter(WebhookRequest.webhook_id == webhook.id).delete()
        db.commit()
        db.close()
        return JSONResponse({"message": f"Successfully deleted {num_deleted} webhook requests."}, status_code=200)
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


@router.get("/settings/{webhook_id}", response_class=HTMLResponse)
async def webhook_settings_get(webhook_id: str, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    db = SessionLocal()
    webhook = db.query(Webhook).filter(
        Webhook.url == webhook_id,
        Webhook.user_id == user['id']
    ).first()
    
    if not webhook:
        db.close()
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    destinations = ", ".join([d.url for d in webhook.destinations])
    db.close()
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "webhook": webhook,
        "destinations": destinations,
        "user": user
    })


@router.post("/settings/{webhook_id}")
async def webhook_settings_post(webhook_id: str, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    db = SessionLocal()
    webhook = db.query(Webhook).filter(
        Webhook.url == webhook_id,
        Webhook.user_id == user['id']
    ).first()
    
    if not webhook:
        db.close()
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    form_data = await request.form()
    
    db.query(Destination).filter(Destination.webhook_id == webhook.id).delete()
    
    # Handle URLs separated by commas or newlines
    raw_urls = form_data.get("destination_urls", "")
    # Replace newlines with commas, then split
    urls = raw_urls.replace('\n', ',').replace('\r', '').split(',')
    for url in urls:
        url = url.strip()
        if url:
            new_destination = Destination(url=url, webhook_id=webhook.id)
            db.add(new_destination)
    
    webhook.transformation_script = form_data.get("transformation_script")
    db.commit()
    db.close()
    return RedirectResponse(url=f"/settings/{webhook_id}?saved=true", status_code=303)


@router.post("/{path:path}")
async def handle_webhook(path: str, request: Request):
    """Handle incoming webhook - no auth required"""
    print(f"\n=== New Webhook Request ===")
    print(f"Path: {path}")
    print(f"Headers: {dict(request.headers)}")
    print(f"Query params: {dict(request.query_params)}")
    
    db = SessionLocal()
    
    webhook = db.query(Webhook).filter(Webhook.url == path).first()
    if not webhook:
        print(f"Webhook not found for path: {path}")
        db.close()
        raise HTTPException(status_code=404, detail="Webhook not found")
        
    print(f"Found webhook: {webhook.name} (ID: {webhook.id}, Active: {webhook.status})")
    
    if not webhook.status:
        print("Webhook is paused")
        db.close()
        return JSONResponse({"message": "Webhook is paused"}, status_code=200)
    
    try:
        headers = {k: v for k, v in request.headers.items()}
        query_params = dict(request.query_params)
        body = await request.body()
        body_text = body.decode('utf-8') if body else ""
        
        print(f"Request body: {body_text}")

        job = queue.enqueue(
            'worker.process_webhook_in_background',
            webhook.id,
            headers,
            body_text,
            query_params,
            job_timeout=30,
            result_ttl=3600
        )
        
        print(f"Enqueued job {job.id} for webhook {webhook.id}")
        
        db.close()
        
        return JSONResponse({
            "message": "Webhook received and queued for processing",
            "job_id": job.id,
            "status": "queued"
        }, status_code=202)
        
    except Exception as e:
        import traceback
        print(f"Error enqueuing webhook: {str(e)}")
        traceback.print_exc()
        db.close()
        raise HTTPException(status_code=500, detail="Failed to process webhook")


@router.get("/{path}")
async def show_webhook(path: str, request: Request):
    # Ignore favicon requests
    if path == "favicon.ico":
        raise HTTPException(status_code=404, detail="Not found")
    
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    print(f"\n=== Showing webhook details for path: {path} ===")
    try:
        db = SessionLocal()
        
        webhook = db.query(Webhook).filter(
            Webhook.url == path,
            Webhook.user_id == user['id']
        ).first()
        
        if not webhook:
            print(f"Webhook not found for path: {path} or user doesn't own it")
            db.close()
            raise HTTPException(status_code=404, detail="Webhook not found")
            
        print(f"Found webhook: {webhook.name} (ID: {webhook.id})")
        
        # Get total count
        total_requests = db.query(WebhookRequest)\
                          .filter(WebhookRequest.webhook_id == webhook.id)\
                          .count()
        
        # Get latest 100 requests
        requests_list = db.query(WebhookRequest)\
                          .filter(WebhookRequest.webhook_id == webhook.id)\
                          .order_by(WebhookRequest.timestamp.desc())\
                          .limit(100)\
                          .all()
        
        print(f"Found {len(requests_list)}/{total_requests} requests for webhook {webhook.id}")
        
        for req in requests_list:
            try:
                req.headers = json.loads(req.headers)
                print(f"Request {req.id} headers: {req.headers}")
            except json.JSONDecodeError:
                req.headers = {}
        
        db.close()
        return templates.TemplateResponse("webhook_details.html", {
            "request": request,
            "webhook": webhook,
            "requests": requests_list,
            "total_requests": total_requests,
            "user": user
        })
                             
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in show_webhook: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/webhook/{webhook_url}/requests")
async def get_webhook_requests(webhook_url: str, request: Request, offset: int = 0, limit: int = 100):
    """API endpoint to get paginated webhook requests"""
    user = require_auth(request)
    
    db = SessionLocal()
    try:
        webhook = db.query(Webhook).filter(
            Webhook.url == webhook_url,
            Webhook.user_id == user['id']
        ).first()
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        # Get total count
        total = db.query(WebhookRequest).filter(
            WebhookRequest.webhook_id == webhook.id
        ).count()
        
        # Get paginated requests
        requests_list = db.query(WebhookRequest)\
            .filter(WebhookRequest.webhook_id == webhook.id)\
            .order_by(WebhookRequest.timestamp.desc())\
            .offset(offset)\
            .limit(min(limit, 100))\
            .all()
        
        result = {
            "requests": [
                {
                    "id": req.id,
                    "timestamp": req.timestamp.isoformat() + "Z" if req.timestamp else None,
                    "body_length": len(req.body) if req.body else 0,
                }
                for req in requests_list
            ],
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(requests_list) < total
        }
        return JSONResponse(result)
    finally:
        db.close()


@router.get("/webhook/request/{request_id}")
async def show_request(request_id: int, request: Request):
    user = require_auth(request)
    
    db = SessionLocal()
    req = db.query(WebhookRequest).get(request_id)
    
    if not req:
        db.close()
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Verify ownership
    webhook = db.query(Webhook).filter(
        Webhook.id == req.webhook_id,
        Webhook.user_id == user['id']
    ).first()
    
    if not webhook:
        db.close()
        raise HTTPException(status_code=403, detail="Forbidden")
    
    result = {
        "headers": json.loads(req.headers),
        "body": req.body,
        "query_params": json.loads(req.query_params) if req.query_params else {},
        "timestamp": req.timestamp.isoformat() if req.timestamp else None,
    }
    db.close()
    return JSONResponse(result)


@router.get("/results/{job_id}")
async def get_results(job_id: str):
    from app.core import queue
    job = queue.fetch_job(job_id)
    
    if job:
        print(type(job), job)
        return JSONResponse({"status": "completed", "job": str(job)})
    else:
        return JSONResponse({"status": "pending"}, status_code=202)


@router.get('/debug/db-status')
async def debug_db_status():
    """Debug endpoint to check database status"""
    try:
        from sqlalchemy import inspect
        from app.core import engine
        
        db = SessionLocal()
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        webhook_count = db.query(Webhook).count()
        request_count = db.query(WebhookRequest).count()
        
        db.close()
        
        return JSONResponse({
            'tables': tables,
            'webhook_count': webhook_count,
            'request_count': request_count,
            'database': str(engine.url)
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/debug/failed-jobs')
async def debug_failed_jobs():
    """Debug endpoint to check failed RQ jobs"""
    try:
        from redis import Redis
        from rq import Queue
        from rq.registry import FailedJobRegistry, StartedJobRegistry
        from app.core.config import settings
        
        # Use raw bytes connection for RQ
        raw_conn = Redis.from_url(settings.REDIS_URL, decode_responses=False)
        q = Queue(connection=raw_conn)
        failed_registry = FailedJobRegistry(queue=q)
        started_registry = StartedJobRegistry(queue=q)
        
        failed_job_ids = failed_registry.get_job_ids()
        started_job_ids = started_registry.get_job_ids()
        pending_job_ids = q.job_ids
        
        failed_jobs = []
        for job_id in failed_job_ids[:10]:
            job = q.fetch_job(job_id)
            if job:
                failed_jobs.append({
                    'id': job_id,
                    'func': str(job.func_name) if job.func_name else None,
                    'exc_info': str(job.exc_info)[:500] if job.exc_info else None,
                })
        
        raw_conn.close()
        
        return JSONResponse({
            'queue_length': len(pending_job_ids),
            'pending_jobs': pending_job_ids[:10],
            'started_count': len(started_job_ids),
            'started_jobs': started_job_ids[:10],
            'failed_count': len(failed_job_ids),
            'failed_jobs': failed_jobs
        })
        
    except Exception as e:
        import traceback
        return JSONResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        })
