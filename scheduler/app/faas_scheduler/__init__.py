import os
from urllib.parse import quote

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

MYSQL_USER = os.getenv('DB_ROOT_USER', 'root')
MYSQL_PASSWORD = os.getenv('DB_ROOT_PASSWD', '')
MYSQL_HOST = os.getenv('DB_HOST', 'seatable-mysql')
MYSQL_PORT = os.getenv('DB_PORT', '3306')
MYSQL_DATABASE_NAME = 'faas-scheduler'

# DBSession for flask and scheduler
db_url = 'mysql+pymysql://%s:%s@%s:%s/%s?charset=utf8mb4' % \
    (quote(MYSQL_USER), quote(MYSQL_PASSWORD),
     quote(MYSQL_HOST), quote(MYSQL_PORT), quote(MYSQL_DATABASE_NAME))
db_kwargs = dict(pool_recycle=300, echo=False, echo_pool=False)

engine = create_engine(db_url, **db_kwargs)
Base = declarative_base()
DBSession = sessionmaker(bind=engine)
