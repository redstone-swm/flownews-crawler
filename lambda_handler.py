import os
import logging
from typing import Any

import boto3
from dotenv import load_dotenv

from rss_feed_crawler import RSSFeedCrawler


def lambda_handler(event: dict, context: Any) -> dict:
    try:
        # 변수 로드
        mongodb_uri = os.environ.get("MONGODB_URI")
        db_name = os.environ.get("MONGODB_DB")
        collection_name = os.environ.get("MONGODB_COL")
        rss_feed_url = event.get("rss_feed_url")
        sqs_queue_url = os.environ.get("SQS_QUEUE_URL")

        # 크롤링
        crawler = RSSFeedCrawler(mongodb_uri, db_name, collection_name)
        inserted_ids = crawler.crawl_rss_feed(rss_feed_url)
        crawler.close()

        # SQS 이벤트 전송
        send_messages(inserted_ids, sqs_queue_url)

        return {
            "statusCode": 200,
            "body": {
                "inserted_count": len(inserted_ids),
                "inserted_ids": [str(_id) for _id in inserted_ids]
            }
        }
    except Exception as e:
        logging.error(f"Lambda execution failed: {str(e)}")
        return {
            "statusCode": 500,
            "body": {"error": str(e)}
        }


def send_messages(inserted_ids: list, sqs_queue_url: str):
    if not inserted_ids or not sqs_queue_url:
        return

    region = os.environ.get('AWS_REGION', 'ap-northeast-2')
    sqs = boto3.client('sqs', region)
    for obj_id in inserted_ids:
        sqs.send_message(
            QueueUrl=sqs_queue_url,
            MessageBody=str(obj_id)
        )


if __name__ == '__main__':
    load_dotenv()

    test_event = {"rss_feed_url": "https://www.yna.co.kr/rss/politics.xml"}
    lambda_handler(test_event, None)
