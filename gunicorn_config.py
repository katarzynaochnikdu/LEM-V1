import multiprocessing
import os

base_dir = os.path.dirname(os.path.abspath(__file__))

bind = "0.0.0.0:8000"
workers = max(2, multiprocessing.cpu_count())
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
errorlog = os.path.join(base_dir, "logs", "error.log")
accesslog = os.path.join(base_dir, "logs", "access.log")
loglevel = "info"
