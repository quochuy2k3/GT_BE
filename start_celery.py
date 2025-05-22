#!/usr/bin/env python
"""
Script to start Celery worker with proper initialization.
"""
import os
import subprocess
from config.config import Settings

def start_celery_worker():
    settings = Settings()
    
    # Set environment variables for Celery
    os.environ['CELERY_BROKER_URL'] = settings.REDIS_URL
    os.environ['CELERY_RESULT_BACKEND'] = settings.REDIS_URL
    
    # Start celery worker with proper settings
    cmd = [
        'celery',
        '-A', 'database.celery_worker.celery_app',
        'worker',
        '--loglevel=info',
        '--concurrency=2',  # Adjust based on your server capacity
    ]
    
    subprocess.run(cmd)

if __name__ == "__main__":
    print("Starting Celery worker...")
    start_celery_worker() 