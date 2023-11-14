import logging
from faas_scheduler import DBSession
from datetime import datetime
from sqlalchemy import text

logger = logging.getLogger(__name__)

clean_script_logs = "DELETE FROM `script_log` WHERE `started_at` < DATE_SUB(NOW(), INTERVAL 30 DAY)"

if __name__ == '__main__':
    db_session = DBSession()
    try:
        result = db_session.execute(text(clean_script_logs))
        db_session.commit()
        msg = '[%s] Clean %d script logs' % (datetime.now(), result.rowcount)
        logger.info(msg)
        print(msg)

    except Exception as e:
        logger.exception(e)
    finally:
        db_session.close()
