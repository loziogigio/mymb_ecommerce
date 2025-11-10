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
        """Connect to a MySQL database with timeouts to prevent hanging"""
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
