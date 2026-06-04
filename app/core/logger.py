import logging
import os
import json
from logging.handlers import RotatingFileHandler

os.makedirs("loggs", exist_ok=True)

class logJsonFormatter(logging.Formatter):

    def format(self, record):
        log_data = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage()
        }

        if hasattr(record, "request_id"):
            log_data["request_id"] == record.request_id
        if hasattr(record, "user"):
            log_data["user"] = record.user

        if hasattr(record, "path"):
            log_data["path"] = record.path

        if hasattr(record, "method"):
            log_data["method"] = record.method

        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code

        if hasattr(record, "duration"):
            log_data["duration"] = record.duration

        return json.dumps(log_data, ensure_ascii=False)
    
logger = logging.setLogger("NLP_server")
logger.setLevel(logging.INFO)
fomatter = logJsonFormatter()

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(fomatter)

file_handler = logging.FileHandler("loggs/app.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
file_handler.setFormatter(fomatter)


logger.addHandler(stream_handler)
logger.addHandler(file_handler)