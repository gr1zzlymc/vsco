from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
import os
import tempfile
import shutil
import zipfile
from io import BytesIO
import threading
import time
from vscoscrape.vscoscrape import Scraper
import vscoscrape.vscoscrape as vscoscrape_module

app = Flask(__name__)
app.secret_key = 'vsco-scraper-secret-key-change-in-production'

# Initialize global variables that the VSCO scraper expects
vscoscrape_module.cache = None
vscoscrape_module.latestCache = None

# Store active jobs
active_jobs = {}

# Improved Scraper class with better image downloading
class ImprovedScraper(Scraper):
    def __init__(self, username):
        super().__init__(username)
        # Update session with better headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site'
        })
    
    def download_img_normal(self, lists):
        """
        Improved image downloading with better error handling and HTTPS support
        """
        try:
            # Fix HTTP to HTTPS
            url = lists[0].replace('http://', 'https://')
            filename = str(lists[1])
            is_video = lists[2]
            
            # Set file extension
            ext = '.mp4' if is_video else '.jpg'
            full_filename = f"{filename}{ext}"
            
            # Skip if already exists
            if full_filename in os.listdir():
                return True
            
            # Download with proper headers and error handling
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()  # Raise exception for bad status codes
            
            # Check if we got actual content
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) < 100:  # Less than 100 bytes is probably an error
                print(f"Warning: Small file size for {filename}, might be an error response")
                return False
            
            # Write file
            with open(full_filename, "wb") as f:
                if is_video:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                else:
                    f.write(response.content)
            
            # Verify file was written and is not empty
            if os.path.exists(full_filename) and os.path.getsize(full_filename) > 0:
                return True
            else:
                # Remove empty file
                if os.path.exists(full_filename):
                    os.remove(full_filename)
                return False
                
        except Exception as e:
            print(f"Error downloading {lists[0]}: {str(e)}")
            # Remove partial file if it exists
            try:
                if os.path.exists(full_filename):
                    os.remove(full_filename)
            except:
                pass
            return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    username = request.form.get('username', '').strip()
    scrape_type = request.form.get('scrape_type', 'images')
    
    if not username:
        flash('Please enter a VSCO username', 'error')
        return redirect(url_for('index'))
    
    # Create a unique job ID
    job_id = f"{username}_{scrape_type}_{int(time.time())}"
    
    # Start scraping in background
    thread = threading.Thread(target=perform_scrape, args=(job_id, username, scrape_type))
    thread.daemon = True
    thread.start()
    
    active_jobs[job_id] = {
        'status': 'processing',
        'username': username,
        'type': scrape_type,
        'start_time': time.time()
    }
    
    return render_template('processing.html', job_id=job_id, username=username, scrape_type=scrape_type)

@app.route('/status/<job_id>')
def check_status(job_id):
    if job_id in active_jobs:
        return jsonify(active_jobs[job_id])
    else:
        return jsonify({'status': 'not_found'})

@app.route('/download/<job_id>')
def download(job_id):
    if job_id not in active_jobs or active_jobs[job_id]['status'] != 'completed':
        flash('Download not available', 'error')
        return redirect(url_for('index'))
    
    zip_path = active_jobs[job_id].get('zip_path')
    if zip_path and os.path.exists(zip_path):
        username = active_jobs[job_id]['username']
        scrape_type = active_jobs[job_id]['type']
        files_count = active_jobs[job_id].get('files_count', 0)
        filename = f"{username}_{scrape_type}_{files_count}files.zip"
        
        def remove_file(path):
            time.sleep(10)  # Wait 10 seconds then cleanup
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass
        
        # Schedule cleanup
        cleanup_thread = threading.Thread(target=remove_file, args=(zip_path,))
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        return send_file(zip_path, as_attachment=True, download_name=filename)
    else:
        flash('File not found', 'error')
        return redirect(url_for('index'))

@app.route('/test/<username>')
def test_scraper(username):
    """Test endpoint to check if a user exists and can be scraped"""
    try:
        import tempfile
        temp_dir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        scraper = ImprovedScraper(username)
        
        # Test if we can get basic user info
        result = {
            'username': username,
            'site_id': scraper.siteid,
            'site_collection_id': scraper.sitecollectionid,
            'media_url': scraper.mediaurl,
            'status': 'success'
        }
        
        os.chdir(original_cwd)
        shutil.rmtree(temp_dir)
        
        return jsonify(result)
        
    except Exception as e:
        try:
            os.chdir(original_cwd)
            shutil.rmtree(temp_dir)
        except:
            pass
        return jsonify({
            'username': username,
            'status': 'error',
            'error': str(e)
        })

def perform_scrape(job_id, username, scrape_type):
    temp_dir = None
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        
        # Change to temp directory
        os.chdir(temp_dir)
        
        # Initialize scraper with improved image downloading
        scraper = ImprovedScraper(username)
        
        # Perform scraping based on type
        if scrape_type == 'images':
            scraper.getImages()
        elif scrape_type == 'journal':
            scraper.getJournal()
        elif scrape_type == 'collection':
            scraper.getCollection()
        elif scrape_type == 'profile':
            scraper.getProfile()
        elif scrape_type == 'all':
            scraper.run_all()
        
        # Create zip file only if we have files
        zip_path = os.path.join(tempfile.gettempdir(), f"{job_id}.zip")
        files_added = 0
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            user_dir = os.path.join(temp_dir, username)
            if os.path.exists(user_dir):
                for root, dirs, files in os.walk(user_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Only add files that are not empty
                        if os.path.getsize(file_path) > 0:
                            arc_name = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arc_name)
                            files_added += 1
        
        # Check if we actually downloaded any files
        if files_added == 0:
            active_jobs[job_id].update({
                'status': 'error',
                'error': 'No images found or user profile is private/doesn\'t exist',
                'end_time': time.time()
            })
            return
        
        # Update job status
        active_jobs[job_id].update({
            'status': 'completed',
            'zip_path': zip_path,
            'files_count': files_added,
            'end_time': time.time()
        })
        
        # Change back to original directory
        os.chdir(original_cwd)
        
    except Exception as e:
        # Update job status with error
        active_jobs[job_id].update({
            'status': 'error',
            'error': str(e),
            'end_time': time.time()
        })
        
        # Change back to original directory
        try:
            os.chdir(original_cwd)
        except:
            pass
    
    finally:
        # Cleanup temp directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False) 
