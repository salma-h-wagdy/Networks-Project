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
        try:
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            logging.info("============================================================")
            logging.info(f"CacheManager initialized with cache_dir={cache_dir} and max_age={max_age}")
        except Exception as e:
            logging.error(f"Failed to create cache directory {cache_dir}: {e}")
            raise
    def _sanitize_path(self, path):
        return path.replace('/', '_').replace('\\', '_')

    def is_cached(self, path):
        cached_path = os.path.join(self.cache_dir, self._sanitize_path(path))
        # cached_path = os.path.join(self.cache_dir, path.lstrip('/'))
         
        if os.path.exists(cached_path):
            age = time.time() - os.path.getmtime(cached_path)
            if age < self.max_age :
                logging.info("=5============================================================")
                logging.info(f"Cache hit for path: {path}")
                return True
            else:
                logging.info("=6============================================================")
                logging.info(f"Cache expired for path: {path}")
        logging.info("=7============================================================")
        logging.info(f"Cache miss for path: {path}")
        return False

    def load_from_cache(self, path):
        cached_path = os.path.join(self.cache_dir, self._sanitize_path(path))
        if os.path.exists(cached_path):
            logging.info("=8============================================================")
            logging.info(f"Loading from cache: {path}")
            with open(cached_path, 'rb') as f:
                return f.read()
        logging.info("=1============================================================")
        logging.warning(f"Cache file not found for path: {path}")
        return None

    def save_to_cache(self, path, content):
        try:
            sanitized_path = self._sanitize_path(path)
            cached_path = os.path.join(self.cache_dir, sanitized_path)
            with open(cached_path, 'wb') as cache_file:
                cache_file.write(content)
            logging.warning("=2============================================================")
            logging.info(f"Saved content to cache for path: {path}")
        except Exception as e:
            logging.error(f"Failed to save content to cache for path {path}: {e}")
            raise



        # cached_path = os.path.join(self.cache_dir, path.lstrip('/'))
        # os.makedirs(os.path.dirname(cached_path), exist_ok=True)
        # with open(cached_path, 'wb') as f:
        #     f.write(content)
        # os.utime(cached_path, (time.time(), time.time() + self.max_age))
        # logging.warning("=2============================================================")
        # logging.info(f"Saved to cache: {path}")

    def cleanup_expired_files(self):
        while True:
            time.sleep(300)  # Run cleanup every 5 minutes
            for root, _, files in os.walk(self.cache_dir):
                for file in files:
                    cached_path = os.path.join(root, file)
                    age = time.time() - os.path.getmtime(cached_path)
                    if age > self.max_age:
                        os.remove(cached_path)
                        logging.warning("=3============================================================")
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