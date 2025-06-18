# VSCO Scraper Web App Deployment

This project has been converted from a CLI tool to a web application that can be deployed on platforms like Render.com, Heroku, or Railway.

## Features

- **Web Interface**: Beautiful, responsive web UI for scraping VSCO profiles
- **Background Processing**: Scraping happens in the background with real-time status updates
- **ZIP Downloads**: All scraped content is packaged into a downloadable ZIP file
- **Multiple Content Types**: Support for images, journals, collections, profile pictures, or everything

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the Flask app:
```bash
python app.py
```

3. Open http://localhost:5000 in your browser

## Deploy to Render.com (Free)

1. **Fork/Upload this repository** to GitHub
2. **Connect to Render.com**:
   - Go to [render.com](https://render.com)
   - Sign up/login with your GitHub account
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

3. **Configure the service**:
   - **Name**: `vsco-scraper` (or any name you prefer)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Select "Free" (0$/month)

4. **Deploy**: Click "Create Web Service"

The app will be live at `https://your-app-name.onrender.com`

## Deploy to Other Platforms

### Heroku
- The `Procfile` is already configured
- Just push to Heroku with Python buildpack

### Railway
- Connect your GitHub repo
- Railway will auto-detect the Python app

### Vercel/Netlify
- These are more suitable for static sites, use Render.com instead

## Environment Variables

No special environment variables are required for basic functionality.

## Usage

1. Visit your deployed web app
2. Enter a VSCO username (e.g., `johndoe`)
3. Select content type (images, journals, collections, etc.)
4. Click "Start Scraping"
5. Wait for processing to complete
6. Download the ZIP file with all content

## Technical Details

- **Framework**: Flask
- **Background Jobs**: Threading (suitable for free tier limitations)
- **File Storage**: Temporary files with automatic cleanup
- **File Serving**: Direct download with scheduled cleanup
- **Frontend**: Bootstrap 5 with modern design

## Limitations on Free Hosting

- **Processing Time**: Free tiers may have request timeouts (usually 30-60 seconds)
- **Storage**: Temporary files only (automatically cleaned up)
- **Concurrent Users**: Limited by free tier resources
- **Bandwidth**: May be limited on free plans

For heavy usage, consider upgrading to paid plans on your hosting platform. 