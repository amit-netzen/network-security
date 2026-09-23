
from pymongo import MongoClient

uri = "mongodb+srv://mehtamit8406_db_user:pMQOqtO6w5z3vN1H@cluster0.n5t5ws3.mongodb.net/?appName=Cluster0"

# Create a new client and connect to the server
client = MongoClient(uri)

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)