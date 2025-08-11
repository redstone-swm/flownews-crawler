from pymongo import MongoClient
import os
import logging


class MongoDBConnector:
    def __init__(self):
        self.uri = os.getenv('MONGODB_URI')
        self.db_name = os.getenv('MONGODB_DB')
        self.collection_name = os.getenv('MONGODB_COL')

        if not self.uri or not self.db_name or not self.collection_name:
            raise ValueError("MongoDB environment variables are not set")

        try:
            self.client = MongoClient(self.uri)
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            logging.info("Successfully connected to MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    def is_duplicate(self, url: str) -> bool:
        return self.collection.find_one({"url": url}) is not None

    def save_articles(self, articles: list) -> list:
        new_ids = []
        for article in articles:
            result = self.collection.update_one(
                {"url": article["url"]},
                {"$set": article},
                upsert=True  # 없으면 생성
            )

            new_ids.append(result.upserted_id)

        logging.info(f"Inserted {len(new_ids)} new articles")
        return new_ids

    def close(self):
        if hasattr(self, 'client'):
            self.client.close()
            logging.info("MongoDB connection closed")
