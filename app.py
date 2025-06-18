from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
import os
import tempfile
import shutil
import zipfile
from io import BytesIO
import threading
import time
from vscoscrape.vscoscrape import Scraper

app = Flask(__name__)
app.secret_key = 'vsco-scraper-secret-key-change-in-production'

# Store active jobs
active_jobs = {}

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
        filename = f"{username}_{scrape_type}.zip"
        
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

def perform_scrape(job_id, username, scrape_type):
    temp_dir = None
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        
        # Change to temp directory
        os.chdir(temp_dir)
        
        # Initialize scraper
        scraper = Scraper(username)
        
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
        
        # Create zip file
        zip_path = os.path.join(tempfile.gettempdir(), f"{job_id}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            user_dir = os.path.join(temp_dir, username)
            if os.path.exists(user_dir):
                for root, dirs, files in os.walk(user_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arc_name)
        
        # Update job status
        active_jobs[job_id].update({
            'status': 'completed',
            'zip_path': zip_path,
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