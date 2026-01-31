from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from authlib.integrations.starlette_client import OAuth
from app.core.config import settings
from app.utils.auth import get_current_user, get_or_create_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# OAuth Configuration
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login page"""
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/auth/google")
async def auth_google(request: Request):
    """Initiate Google OAuth flow"""
    return await oauth.google.authorize_redirect(request, settings.REDIRECT_URI)


@router.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle Google OAuth callback"""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        # Get or create user (returns dict)
        user = await get_or_create_user(
            email=user_info['email'],
            name=user_info.get('name'),
            picture=user_info.get('picture'),
            google_id=user_info['sub']
        )
        
        # Store user in session
        request.session['user'] = {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'picture': user['picture']
        }
        
        return RedirectResponse(url="/")
        
    except Exception as e:
        print(f"OAuth error: {e}")
        return RedirectResponse(url="/login?error=auth_failed")


@router.get("/logout")
async def logout(request: Request):
    """Logout user"""
    request.session.clear()
    return RedirectResponse(url="/login")
