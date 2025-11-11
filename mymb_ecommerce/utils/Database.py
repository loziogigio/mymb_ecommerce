from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pymongo import MongoClient


class Database:
    def __init__(self, db_config, pool_size=5, max_overflow=10):
        self.db_config = db_config
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.engine = None
        self.session = None
        self.mongo_client = None

        self.connect()

    def connect(self):
        """Connect to the database"""
        if self.db_config['drivername'] == 'mysql':
            self.connect_mysql()
        elif self.db_config['drivername'] == 'mongodb':
            self.connect_mongodb()

    def connect_mysql(self):
        """Connect to a MySQL database with timeouts to prevent hanging and worker blocking"""
        from sqlalchemy import event

        self.engine = create_engine(
            f"{self.db_config['drivername']}://{self.db_config['username']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}",
            # Connection timeout: fail fast if B2B database is unreachable (3 seconds)
            connect_args={
                'connect_timeout': 3,
                'read_timeout': 30,
                'write_timeout': 30
            },
            # Verify connections before using them to avoid stale connections
            pool_pre_ping=True,
            # Recycle connections after 1 hour to avoid long-lived connections
            pool_recycle=3600,
            # Per-tenant pool size limits (passed from Configurations)
            pool_size=self.pool_size,
            max_overflow=self.max_overflow
        )

        # CRITICAL: Prevent one tenant's table locks from blocking all workers
        @event.listens_for(self.engine, "connect")
        def set_lock_timeout(dbapi_conn, connection_record):
            """
            Tenant Isolation: Prevent worker blocking when tables are locked.

            Problem: Tenant A locks a table → Tenants B, C, D wait → all workers blocked
            Solution: Fail fast if table is locked (3s), free the worker immediately
            """
            cursor = dbapi_conn.cursor()
            try:
                # innodb_lock_wait_timeout/lock_wait_timeout: Max time to wait if table is LOCKED by another transaction
                # If Tenant A has a lock, Tenant B fails after 3s instead of blocking worker
                cursor.execute("SET SESSION innodb_lock_wait_timeout = 3")
                cursor.execute("SET SESSION lock_wait_timeout = 3")

                # max_execution_time: Max time for ANY query to execute (prevents slow queries)
                # If a query takes >30s (even without locks), kill it to free the worker
                # This prevents: SELECT with bad JOIN, missing indexes, full table scans, etc.
                cursor.execute("SET SESSION max_execution_time = 30000")  # 30 seconds in milliseconds
            except Exception:
                # Older MySQL versions might not support these settings
                pass
            finally:
                cursor.close()

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def connect_mongodb(self):
        """Connect to a MongoDB database"""
        self.mongo_client = MongoClient(self.db_config['host'], self.db_config['port'])
        self.session = self.mongo_client[self.db_config['database']]

    def disconnect(self):
        """Disconnect from the database"""
        if self.db_config['drivername'] == 'mongodb':
            self.mongo_client.close()

    def get_session(self):
        """Get the database session"""
        return self.session
