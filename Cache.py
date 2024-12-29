# Cache Manager Class
import hashlib
import logging
import os
import time
from datetime import datetime


class CacheManager:
    def __init__(self, cache_dir="cache", max_age=3600):
        self.cache_dir = cache_dir
        self.max_age = max_age  # Cache expiration in seconds
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def is_cached(self, path):
        cached_path = os.path.join(self.cache_dir, path.lstrip('/'))
        if os.path.exists(cached_path):
            age = time.time() - os.path.getmtime(cached_path)
            return age < self.max_age
        return False

    def load_from_cache(self, path):
        cached_path = os.path.join(self.cache_dir, path.lstrip('/'))
        if os.path.exists(cached_path):
            with open(cached_path, 'rb') as f:
                return f.read()
        return None

    def save_to_cache(self, path, content):
        cached_path = os.path.join(self.cache_dir, path.lstrip('/'))
        os.makedirs(os.path.dirname(cached_path), exist_ok=True)
        with open(cached_path, 'wb') as f:
            f.write(content)
        os.utime(cached_path, (time.time(), time.time() + self.max_age))

    def cleanup_expired_files(self):
        while True:
            time.sleep(300)  # Run cleanup every 5 minutes
            for root, _, files in os.walk(self.cache_dir):
                for file in files:
                    cached_path = os.path.join(root, file)
                    age = time.time() - os.path.getmtime(cached_path)
                    if age > self.max_age:
                        os.remove(cached_path)
                        logging.info(f"Removed expired cache file: {cached_path}")


# Utility Functions
def generate_etag(content):
    return hashlib.sha256(content).hexdigest()


def get_last_modified_time(path):
    try:
        last_modified_timestamp = os.path.getmtime(path)
        return datetime.fromtimestamp(last_modified_timestamp).strftime('%a, %d %b %Y %H:%M:%S GMT')
    except FileNotFoundError:
        return None