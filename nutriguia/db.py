import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

load_dotenv()


def get_db() -> Database:
    uri = os.environ["MONGO_URI"]
    db_name = os.environ.get("MONGO_DB", "nutriguia")
    client = MongoClient(uri)
    return client[db_name]
