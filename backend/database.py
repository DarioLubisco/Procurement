import os
import pyodbc
from dotenv import load_dotenv
import threading
import queue
import contextvars
import logging

load_dotenv()

DB_SERVER = os.getenv("DB_SERVER", "amc.sql\\efficacis3")
DB_DATABASE = os.getenv("DB_DATABASE", "EnterpriseAdmin_AMC")
DB_USERNAME = os.getenv("DB_USERNAME", "sa")
# Never hardcode secrets — set DB_PASSWORD in .env (see .env.example)
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

pyodbc.pooling = False

# ContextVar for tracking connections per request
request_db_connections = contextvars.ContextVar('request_db_connections', default=None)

class PooledConnectionWrapper:
    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn
        self._closed = False
        
    def cursor(self):
        return self._conn.cursor()
        
    def commit(self):
        self._conn.commit()
        
    def rollback(self):
        self._conn.rollback()
        
    def close(self):
        if not getattr(self, '_closed', False):
            self._pool.release_connection(self._conn)
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)

class PyODBCPool:
    def __init__(self, max_connections=50):
        self.max_connections = max_connections
        self.pool = queue.Queue(maxsize=max_connections)
        self.current_connections = 0
        self.lock = threading.Lock()

    def _create_connection(self):
        available = pyodbc.drivers()
        driver_name = os.getenv("DRIVER", "ODBC Driver 18 for SQL Server").strip("{}")
        if driver_name not in available:
            if "ODBC Driver 18 for SQL Server" in available:
                driver_name = "ODBC Driver 18 for SQL Server"
            elif "ODBC Driver 17 for SQL Server" in available:
                driver_name = "ODBC Driver 17 for SQL Server"
            elif "SQL Server" in available:
                driver_name = "SQL Server"

        conn_str = (
            f"DRIVER={{{driver_name}}};"
            f"SERVER={DB_SERVER};"
            f"DATABASE={DB_DATABASE};"
            f"UID={DB_USERNAME};"
            f"PWD={DB_PASSWORD};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=yes;"
            f"LoginTimeout=5;"
        )
        conn = pyodbc.connect(conn_str)
        conn.timeout = 30
        return conn

    def get_connection(self):
        while True:
            try:
                conn = self.pool.get_nowait()
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                    cursor.close()
                    wrapper = PooledConnectionWrapper(self, conn)
                    conns_list = request_db_connections.get()
                    if conns_list is not None:
                        conns_list.append(wrapper)
                    return wrapper
                except Exception:
                    try:
                        conn.close()
                    except:
                        pass
                    with self.lock:
                        self.current_connections -= 1
            except queue.Empty:
                break
                
        with self.lock:
            if self.current_connections < self.max_connections:
                self.current_connections += 1
                try:
                    conn = self._create_connection()
                    wrapper = PooledConnectionWrapper(self, conn)
                    conns_list = request_db_connections.get()
                    if conns_list is not None:
                        conns_list.append(wrapper)
                    return wrapper
                except Exception as e:
                    self.current_connections -= 1
                    raise e
                    
        conn = self.pool.get(timeout=30)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            wrapper = PooledConnectionWrapper(self, conn)
            conns_list = request_db_connections.get()
            if conns_list is not None:
                conns_list.append(wrapper)
            return wrapper
        except Exception:
            try:
                conn.close()
            except:
                pass
            with self.lock:
                self.current_connections -= 1
            return self.get_connection()

    def release_connection(self, conn):
        try:
            self.pool.put_nowait(conn)
        except queue.Full:
            try:
                conn.close()
            except:
                pass

db_pool = PyODBCPool(max_connections=50)
scraper_pool = PyODBCPool(max_connections=30)

def get_db_connection():
    return db_pool.get_connection()

def get_scraper_db_connection():
    return scraper_pool.get_connection()
