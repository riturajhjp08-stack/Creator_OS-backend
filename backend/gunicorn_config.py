"""Gunicorn configuration for production"""
import multiprocessing
import os


def _get_int(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default

# Server socket
bind = os.environ.get('BIND_ADDRESS', '127.0.0.1:5000')
backlog = 2048

# Worker processes
workers = _get_int('WORKERS', multiprocessing.cpu_count() * 2 + 1)
worker_class = os.environ.get('WORKER_CLASS', 'sync')
threads = _get_int('THREADS', 1)
worker_connections = _get_int('WORKER_CONNECTIONS', 1000)
timeout = _get_int('TIMEOUT', 120)
keepalive = _get_int('KEEPALIVE', 5)

# Logging
def _resolve_log_path(env_name, default_path):
    value = os.environ.get(env_name)
    if value:
        return value
    log_dir = os.path.dirname(default_path)
    if log_dir and not os.path.isdir(log_dir):
        return "-"
    return default_path


accesslog = _resolve_log_path('ACCESS_LOG', 'logs/access.log')
errorlog = _resolve_log_path('ERROR_LOG', 'logs/error.log')
loglevel = os.environ.get('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'creativeos_api'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed, add cert paths)
keyfile = None
certfile = None

# Application
max_requests = _get_int('MAX_REQUESTS', 1000)
max_requests_jitter = _get_int('MAX_REQUESTS_JITTER', 50)
preload_app = os.environ.get('PRELOAD_APP', 'false').lower() in {'1', 'true', 'yes'}
