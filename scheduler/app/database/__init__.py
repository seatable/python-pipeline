import os
from urllib.parse import quote

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWD = os.getenv('DB_PASSWD', '')
DB_HOST = os.getenv('DB_HOST', 'seatable-mysql')
DB_PORT = os.getenv('DB_PORT', '3306')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'scheduler')

# DBSession for flask and scheduler
db_url = 'mysql+pymysql://%s:%s@%s:%s/%s?charset=utf8mb4' % \
    (quote(DB_USER), quote(DB_PASSWD),
     quote(DB_HOST), quote(DB_PORT), quote(DATABASE_NAME))
db_kwargs = dict(pool_recycle=300, echo=False, echo_pool=False)

engine = create_engine(db_url, **db_kwargs)
Base = declarative_base()
DBSession = sessionmaker(bind=engine)
