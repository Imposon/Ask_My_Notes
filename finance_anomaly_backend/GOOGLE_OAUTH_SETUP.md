# Google OAuth Setup Guide

## 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the following APIs:
   - Google People API
   - Google OAuth2 API

## 2. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth 2.0 Client IDs**
3. Select **Web application**
4. Add authorized redirect URIs:
   - `http://localhost:8502` (for local development)
   - `https://askmynotes-96w2ccwsyucbwolzuixqzq.streamlit.app` (for production)
5. Copy the **Client ID** and **Client Secret**

## 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here

# For local development:
GOOGLE_REDIRECT_URI=http://localhost:8502
# For production (uncomment the line below):
# GOOGLE_REDIRECT_URI=https://askmynotes-96w2ccwsyucbwolzuixqzq.streamlit.app

# OpenAI API Key (optional, for AI insights)
OPENAI_API_KEY=your-openai-api-key-here
```

## 4. Test the OAuth Flow

1. Start the backend server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

2. Start the Streamlit frontend:
   ```bash
   streamlit run streamlit_app.py --server.port 8502
   ```

3. Open http://localhost:8502 in your browser

4. Click "Sign in with Google" to test the OAuth flow

## 5. API Endpoints

The following OAuth endpoints are available:

- `POST /auth/google` - Authenticate with Google OAuth token
- `GET /auth/me` - Get current authenticated user (requires Bearer token)

## 6. Database Schema Updates

The User model now includes:
- `google_id` - Google user ID (unique)
- `picture` - Profile picture URL

## 7. Security Notes

- In production, implement proper JWT token verification
- Use HTTPS for all OAuth redirects
- Store secrets securely (use environment variables)
- Consider implementing refresh tokens for better security

## 8. Troubleshooting

**Common Issues:**

1. **Redirect URI mismatch (Error 400)**: 
   - Ensure the redirect URI in Google Console matches exactly:
     - Local: `http://localhost:8502`
     - Production: `https://askmynotes-96w2ccwsyucbwolzuixqzq.streamlit.app`
   - Check for trailing slashes or extra characters

2. **Invalid client credentials**: Double-check Client ID and Secret

3. **Port conflicts**: Change the port if 8502 is already in use

4. **CORS issues**: The backend allows all origins for development

5. **Missing APIs**: Ensure Google People API and OAuth2 API are enabled

**Debug Mode:**

Enable debug logging by setting:
```bash
export STREAMLIT_LOG_LEVEL=debug
```

**Environment Variables Check:**

Verify your `.env` file has the correct redirect URI for your environment:
- Local development: `GOOGLE_REDIRECT_URI=http://localhost:8502`
- Production: `GOOGLE_REDIRECT_URI=https://askmynotes-96w2ccwsyucbwolzuixqzq.streamlit.app`
