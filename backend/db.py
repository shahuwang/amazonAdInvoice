import pymysql
from dbutils.pooled_db import PooledDB
from contextlib import contextmanager
from backend.config import DB_CONFIG

_db_config = {k: v for k, v in DB_CONFIG.items() if k != 'cursorclass'}

pool = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=2,
    maxcached=5,
    maxshared=3,
    blocking=True,
    maxusage=None,
    setsession=[],
    ping=1,
    cursorclass=pymysql.cursors.DictCursor,
    **_db_config
)

@contextmanager
def get_connection():
    """获取数据库连接的上下文管理器"""
    conn = pool.connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

@contextmanager
def get_cursor():
    """获取数据库游标的上下文管理器"""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
