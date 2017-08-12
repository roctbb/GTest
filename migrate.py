from pymongo import  MongoClient

from_connection = MongoClient("mongodb://GoTo:GoTo@ds143532.mlab.com:43532/gtest")
from_database = from_connection["gtest"]
from_questions_collection = from_database["Questions"]

to_connection = MongoClient("mongodb://localhost:27017/quizer")
to_database = to_connection["quizer"]
to_questions_collection = to_database["Questions"]
to_users_collection = to_database["Students"]

to_questions_collection.remove()
to_users_collection.remove()

records = list(from_questions_collection.find())
print(records)
to_questions_collection.insert(records)

