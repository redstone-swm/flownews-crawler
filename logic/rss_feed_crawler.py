import logging
from typing import Dict
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from newspaper import Article

logging.basicConfig(level=logging.INFO)


class RSSFeedCrawler:
    def __init__(self):
        self.robot_parsers: Dict[str, RobotFileParser] = {}

    def check_robots_txt(self, url: str) -> bool:
        domain = urlparse(url).netloc
        if domain not in self.robot_parsers:
            rp = RobotFileParser()
            rp.set_url(f"https://{domain}/robots.txt")
            rp.read()
            self.robot_parsers[domain] = rp
        return self.robot_parsers[domain].can_fetch("*", url)

    def crawl(self, articles: list) -> list:
        saved_count = 0
        results = []

        try:
            for article in articles:
                article_url = article["link"]
                if not self.check_robots_txt(article_url):
                    logging.warning(f"Skipping {article_url}")
                    continue

                parser = Article(article["link"])
                parser.download()
                parser.parse()

                results.append({
                    "title": parser.title,
                    "url": article["link"],
                    "image": parser.top_image,
                    "date": parser.publish_date if parser.publish_date else article["date"],
                    "body": parser.text,
                    "source": article.get("source", "unknown"),
                    "category": article.get("category", "unknown")
                })

                saved_count += 1

        except Exception as e:
            logging.error(f"Error crawling : {str(e)}")

        if len(results) == 0:
            logging.info("No new articles found")
            return []

        logging.info("Crawled %d articles", len(results))

        return results


def close(self):
    self.client.close()
