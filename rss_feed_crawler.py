import logging
from datetime import datetime
from typing import Dict
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import feedparser
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO)


def format_date(text) -> str:
    """
    'YYYY-MM-DD hh:ss' 형태로 변환
    """
    dt = datetime.strptime(text, '%a, %d %b %Y %H:%M:%S %z')
    return dt.strftime('%Y-%m-%d %H:%M')


def remove_intro_outro_lines(text):
    lines = text.strip().split('\n')
    if len(lines) <= 2:
        return ''
    return '\n'.join(lines[1:-1])


def extract_yna_article_content(html):
    """
    연합뉴스 뉴스 파싱
    """
    soup = BeautifulSoup(html, "html.parser")
    # 1. story-news article 클래스의 div 찾기
    story_div = soup.find("div", class_="story-news article")
    if not story_div:
        return ""

    # 2. 광고, 저작권 등 불필요한 aside, p.txt-copyright 등 제거
    for aside in story_div.find_all("aside"):
        aside.decompose()
    for copyright_p in story_div.find_all("p", class_="txt-copyright"):
        copyright_p.decompose()

    # 3. 남은 <p> 태그만 텍스트 추출
    paragraphs = story_div.find_all("p")
    content = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    return remove_intro_outro_lines(content)


class RSSFeedCrawler:
    def __init__(self, mongodb_uri, db_name, collection_name):
        if not mongodb_uri or not db_name or not collection_name:
            raise ValueError("check your environment variables")

        self.client = MongoClient(mongodb_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

        self.robot_parsers: Dict[str, RobotFileParser] = {}

    def check_robots_txt(self, url: str) -> bool:
        domain = urlparse(url).netloc
        if domain not in self.robot_parsers:
            rp = RobotFileParser()
            rp.set_url(f"https://{domain}/robots.txt")
            rp.read()
            self.robot_parsers[domain] = rp
        return self.robot_parsers[domain].can_fetch("*", url)

    def is_duplicate(self, url: str) -> bool:
        return self.collection.find_one({"url": url}) is not None

    def crawl_rss_feed(self, feed_url: str) -> list:
        if feed_url is None:
            raise ValueError("feed_url is required")

        saved_count = 0
        results = []

        feed = feedparser.parse(feed_url)

        logging.info(f"feed entries size: {len(feed.entries)}")

        for entry in feed.entries:
            article_url = entry.link

            if not self.check_robots_txt(article_url) or self.is_duplicate(article_url):
                logging.warning(f"Skipping {article_url}")
                continue

            try:
                response = requests.get(article_url)
                response.raise_for_status()

                article = {
                    "title": entry.title,
                    "url": article_url,
                    "body": extract_yna_article_content(response.text),
                    "date": format_date(entry.published),
                    "summary": entry.get("summary", ""),
                    "created_at": datetime.now()
                }

                # 속보는 내용이 없으므로 패스
                if article["body"] == "":
                    continue

                saved_count += 1
                results.append(article)

            except Exception as e:
                logging.error(f"Error crawling {article_url}: {str(e)}")

        if len(results) == 0:
            logging.info("No new articles found")
            return []

        insert_result = self.collection.insert_many(results)
        inserted_ids = insert_result.inserted_ids

        logging.info(f"Saved {saved_count} articles to MongoDB")

        return inserted_ids

    def close(self):
        self.client.close()
