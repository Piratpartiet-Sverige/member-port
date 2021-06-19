from app.config import Config
from app.logger import setup_logger_worker
from app.web.web_server import WebAppOptions
from celery import Celery


config = Config().get_config()
broker_url = config.get("TaskQueue", "broker_url")

app = Celery('tasks', broker=broker_url, include=['app.tasks.tasks'])

admin = config.get("Email", "admin")

options = WebAppOptions()
options.db_username = config.get("PostgreSQL", "username")
options.db_password = config.get("PostgreSQL", "password")
options.db_hostname = config.get("PostgreSQL", "hostname")
options.dbname = config.get("PostgreSQL", "dbname")


if __name__ == '__main__':
    debug = config.getboolean("WebServer", "debug", fallback=False)
    setup_logger_worker(debug)

    app.start()
