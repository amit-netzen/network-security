import os, pymongo
from dotenv import load_dotenv
load_dotenv()

uri = os.getenv("MONGODB_URI")
client = pymongo.MongoClient(uri)

# List all databases and collections to see what actually exists
print("Databases:", client.list_database_names())

db_name = "mehtaAI"
coll_name = "NetworkData"

db = client[db_name]
print(f"Collections in '{db_name}':", db.list_collection_names())

coll = db[coll_name]
print(f"Document count in '{coll_name}':", coll.count_documents({}))
print("Sample doc:", coll.find_one())