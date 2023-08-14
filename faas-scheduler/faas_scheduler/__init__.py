from urllib.parse import quote

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import faas_scheduler.settings as settings


# DBSession for flask and scheduler
db_url = 'mysql+pymysql://%s:%s@%s:%s/%s?charset=utf8mb4' % \
    (quote(settings.MYSQL_USER), quote(settings.MYSQL_PASSWORD),
     quote(settings.MYSQL_HOST), quote(settings.MYSQL_PORT), quote(settings.DATABASE_NAME))
db_kwargs = dict(pool_recycle=300, echo=False, echo_pool=False)

engine = create_engine(db_url, **db_kwargs)
Base = declarative_base()
DBSession = sessionmaker(bind=engine)
