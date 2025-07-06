from pymongo import MongoClient
import random
import os
from dotenv import load_dotenv

load_dotenv()

def connectDB():
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client["website"]

    return db

