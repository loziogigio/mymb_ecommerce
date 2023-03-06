from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pymongo import MongoClient


class Database:
    def __init__(self, db_config):
        self.db_config = db_config
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
        """Connect to a MySQL database"""
        self.engine = create_engine(
            f"{self.db_config['drivername']}://{self.db_config['username']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
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
