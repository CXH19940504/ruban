from os import environ


def __set_from_environ():
    config = globals()
    for k, v in config.items():
        if k not in environ:
            continue
        v_type = type(v)
        if v_type == bool and str(environ[k]).lower() == 'false':
            config[k] = False
        else:
            config[k] = v_type(environ[k])


DEBUG = True

APP_NAME = "ruban"

FLASK_ENV = 'dev'
FLASK_PORT = 8081
FLASK_HOST = '0.0.0.0'
SQLALCHEMY_TRACK_MODIFICATIONS = True
SQLALCHEMY_DATABASE_URI = "mysql+pymysql://api_test:APItest123@rm-bp1l6ove2344qcbw5eo.mysql.rds.aliyuncs.com:3306/digikey_db"
# SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"

SQL_DEBUG = False
FILENAME = 'ruban_server'
LOGGER_PATH = '../logs'


__set_from_environ()
