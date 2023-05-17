import os
import logging

# curPath = os.path.abspath(os.path.dirname(__file__))
# root_path = os.path.split(curPath)[0]

LOG_FORMAT = '[%(asctime)s] [%(filename)s] [line %(lineno)s] %(levelname)s: %(funcName)s(%(message)s)'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
formatter = logging.Formatter(LOG_FORMAT)

if not os.path.exists('./log'):
    os.mkdir('./log')

# running
logger_running = logging.getLogger("running")
filehandler_server = logging.FileHandler(
    './log/running.log', encoding="utf-8")
filehandler_server.setFormatter(formatter)
logger_running.addHandler(filehandler_server)

# mysql
logger_mysql = logging.getLogger("logger_mysql")
filehandler_server = logging.FileHandler(
    './log/mysql.log', encoding="utf-8")
filehandler_server.setFormatter(formatter)
logger_mysql.addHandler(filehandler_server)