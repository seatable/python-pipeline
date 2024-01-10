import os
from urllib.parse import quote

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_ROOT_USER = os.getenv('DB_ROOT_USER', 'root')
DB_ROOT_PASSWD = os.getenv('DB_ROOT_PASSWD')
DB_USER = os.getenv('DB_USER')
DB_PASSWD = os.getenv('DB_PASSWD')
db_user = ''
db_passwd = ''
if DB_ROOT_USER and DB_ROOT_PASSWD is not None:
    db_user = 'root'
    db_passwd = DB_ROOT_PASSWD
elif DB_USER and DB_PASSWD:
    db_user = DB_USER
    db_passwd = DB_PASSWD
else:
    db_user = 'root'
    db_passwd = ''

DB_HOST = os.getenv('DB_HOST', 'seatable-mysql')
DB_PORT = os.getenv('DB_PORT', '3306')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'scheduler')

# DBSession for flask and scheduler
db_url = 'mysql+pymysql://%s:%s@%s:%s/%s?charset=utf8mb4' % \
    (quote(db_user), quote(db_passwd),
     quote(DB_HOST), quote(DB_PORT), quote(DATABASE_NAME))
db_kwargs = dict(pool_recycle=300, echo=False, echo_pool=False)

engine = create_engine(db_url, **db_kwargs)
Base = declarative_base()
DBSession = sessionmaker(bind=engine)
