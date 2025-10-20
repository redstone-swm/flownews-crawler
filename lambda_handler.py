import asyncio
import logging
from typing import Any

from dotenv import load_dotenv

from logic.mongodb import MongoDBConnector
from logic.preprocess import preprocess
from logic.rss_feed_crawler import RSSFeedCrawler


def lambda_handler(event: dict, context: Any) -> dict:
    try:
        # 변수 로드
        articles = event.get("data") or []
        mongodb = MongoDBConnector()
        crawler = RSSFeedCrawler()

        # 크롤링
        not_duplicated_articles = list(filter(lambda x: not mongodb.is_duplicate(x["link"]), articles))
        results = crawler.crawl(not_duplicated_articles)


        # 전처리
        preprocessed_articles = preprocess(results)
        filtered_articles = list(filter(lambda x: not is_badnews(x), preprocessed_articles))

        # 저장
        inserted_ids = mongodb.save_articles(filtered_articles)

        return {
            "statusCode": 200,
            "body": {
                "count": len(inserted_ids),
                "inserted_ids": [str(_id) for _id in inserted_ids],
            }
        }
    except Exception as e:
        logging.error(f"Lambda execution failed: {str(e)}")
        return {
            "statusCode": 500,
            "body": {"error": str(e)}
        }

def is_badnews(article: dict) -> bool:
    body = article.get("body", "")
    return "새로운 연합뉴스" in body


if __name__ == '__main__':
    load_dotenv()

    is_badnews({"body": "이 기사는 새로운 연합뉴스에서 제공됩니다."})

    test_event = {
        "data": [{
            "link": "https://www.yna.co.kr/view/AKR20251020154600062",
            "title": "안규백, 1호 지휘서신…본립도생, 기본이 서야 길이 생긴다",
            "summary": "안규백 의원이 1호 지휘서신을 발표하며 본립도생의 중요성을 강조했다.",
            "date": "2023-10-01T12:00:00Z"
        }]
    }

    lambda_handler(test_event, None)
