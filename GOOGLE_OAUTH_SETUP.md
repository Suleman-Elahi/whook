# 🔐 Google OAuth Setup Guide

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name: `Webhook Manager`
4. Click "Create"

## Step 2: Enable Google+ API

1. In the left sidebar, go to "APIs & Services" → "Library"
2. Search for "Google+ API"
3. Click on it and click "Enable"

## Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select "External" (unless you have Google Workspace)
3. Click "Create"

### Fill in the required information:

**App information:**
- App name: `Webhook Manager`
- User support email: Your email
- App logo: (Optional)

**App domain:**
- Application home page: `http://localhost:5000`
- Application privacy policy link: (Optional for testing)
- Application terms of service link: (Optional for testing)

**Authorized domains:**
- Add: `localhost` (for development)

**Developer contact information:**
- Email addresses: Your email

4. Click "Save and Continue"
5. On "Scopes" page, click "Add or Remove Scopes"
6. Select these scopes:
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `openid`
7. Click "Update" → "Save and Continue"
8. On "Test users" page (if in testing mode):
   - Click "Add Users"
   - Add your email address
   - Click "Save and Continue"
9. Click "Back to Dashboard"

## Step 4: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Select "Web application"
4. Name: `Webhook Manager Web Client`

### Authorized JavaScript origins:
```
http://localhost:5000
http://127.0.0.1:5000
```

### Authorized redirect URIs:
```
http://localhost:5000/auth/callback
http://127.0.0.1:5000/auth/callback
```

5. Click "Create"
6. Copy the **Client ID** and **Client Secret**

## Step 5: Update .env File

Edit your `.env` file and add the credentials:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
SECRET_KEY=generate-a-random-secret-key-here
REDIRECT_URI=http://localhost:5000/auth/callback
```

### Generate a Secret Key:

```python
# Run this in Python to generate a secure secret key
import secrets
print(secrets.token_urlsafe(32))
```

Or use this command:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step 6: Test the Setup

1. Start your application:
```bash
python app.py
```

2. Open browser and go to: `http://localhost:5000`
3. You should be redirected to the login page
4. Click "Continue with Google"
5. Select your Google account
6. Grant permissions
7. You should be redirected back to the dashboard

## Production Setup

### For Production Deployment:

1. **Update OAuth Consent Screen:**
   - Change from "Testing" to "In Production"
   - Complete verification process if required

2. **Update Authorized Domains:**
   - Add your production domain (e.g., `webhooks.yourdomain.com`)

3. **Update Redirect URIs:**
   ```
   https://webhooks.yourdomain.com/auth/callback
   ```

4. **Update .env for Production:**
   ```env
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   SECRET_KEY=your-production-secret-key
   REDIRECT_URI=https://webhooks.yourdomain.com/auth/callback
   ```

5. **Enable HTTPS:**
   - Use Let's Encrypt or your SSL certificate
   - Update all URLs to use `https://`

## Troubleshooting

### Error: redirect_uri_mismatch
- Make sure the redirect URI in your `.env` matches exactly what's in Google Console
- Check for trailing slashes
- Verify the protocol (http vs https)

### Error: invalid_client
- Double-check your Client ID and Client Secret
- Make sure there are no extra spaces
- Regenerate credentials if needed

### Error: access_denied
- User denied permission
- Check if user is added to test users (if in testing mode)

### Can't see login page
- Make sure session middleware is configured
- Check if SECRET_KEY is set in .env
- Verify all dependencies are installed

## Security Best Practices

1. **Never commit .env file to git**
   - Already in .gitignore
   - Use .env.example as template

2. **Use strong SECRET_KEY**
   - At least 32 characters
   - Random and unique
   - Different for each environment

3. **Rotate credentials regularly**
   - Change SECRET_KEY periodically
   - Regenerate OAuth credentials if compromised

4. **Use HTTPS in production**
   - Never use HTTP for OAuth in production
   - Enable HSTS headers

5. **Limit OAuth scopes**
   - Only request necessary permissions
   - Currently: email, profile, openid

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)
- [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)

## Support

If you encounter issues:
1. Check the application logs
2. Verify all steps above
3. Check Google Cloud Console for error messages
4. Open an issue on GitHub with error details
