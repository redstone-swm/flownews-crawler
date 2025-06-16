from __future__ import annotations

import os
import sys
import json
import re
import html
import concurrent.futures as cf
import requests
from bs4 import BeautifulSoup, Tag
from typing import List, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
NAVER_CLIENT_ID     = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
MONGODB_URI         = os.getenv("MONGODB_URI")
DB_NAME             = os.getenv("MONGODB_DB")
COLLECTION_NAME     = os.getenv("MONGODB_COL")

if not all([MONGODB_URI, DB_NAME, COLLECTION_NAME]):
    print("ERROR: 환경변수가 없습니다.", file=sys.stderr)
    sys.exit(1)

BASE_RANK_URL = "https://news.nate.com/rank/interest"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
}

def clean_text(raw_html: Tag) -> str:
    """광고 iframe·script 제거 후 순수 텍스트로 반환"""
    for tag in raw_html(["script", "style", "iframe"]):
        tag.decompose()
    text = raw_html.get_text("\n", strip=True)
    text = html.unescape(text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()

# 기사 URL -> (rank, article_id, title, date, body)
def fetch_article(args: Tuple[int, str]) -> Tuple[int, str, str, str, str]:
    rank, url = args
    m = re.search(r"/view/([^?]+)", url)
    article_id = m.group(1) if m else ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        r.encoding = "euc-kr"
        soup = BeautifulSoup(r.text, "html.parser")
        h_tag = soup.select_one("h1.viewTite") or soup.select_one("h1.articleSubecjt")
        title = h_tag.get_text(strip=True) if h_tag else ""
        em_tag = soup.select_one("span.firstDate em")
        pub_date = em_tag.get_text(strip=True) if em_tag else ""
        body_tag = soup.select_one("#articleContetns")
        body = clean_text(body_tag) if body_tag else ""
        return rank, article_id, title, pub_date, body
    except Exception as e:
        print(f"[warn] {url} 파싱 실패 → {e}", file=sys.stderr)
        return rank, article_id, "", "", ""

def fetch_top30(date: str) -> List[str]:
    params = {"sc": "all", "p": "day", "date": date}
    r = requests.get(BASE_RANK_URL, params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    r.encoding = "euc-kr"
    soup = BeautifulSoup(r.text, "html.parser")
    urls: List[str] = []
    for a in soup.select("div.postRankSubjectList a.lt1")[:5]:
        urls.append("https://" + a["href"].lstrip("/"))
    for a in soup.select("div.postRankSubject li a[href*='/view/']"):
        if len(urls) >= 30:
            break
        urls.append("https://" + a["href"].lstrip("/"))
    return urls

def scrape_and_save(date: str) -> List[dict]:
    urls = fetch_top30(date)
    jobs = [(rank, url) for rank, url in enumerate(urls, 1)]
    results: List[dict] = []
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        for rank, article_id, title, pub_date, body in ex.map(fetch_article, jobs):
            if not title or not article_id:
                print(f"[warn] {urls[rank-1]} 삽입 실패", file=sys.stderr)
                continue
            results.append({
                "rank": rank,
                "article_id": article_id,
                "title": title,
                "url": urls[rank - 1],
                "date": pub_date,
                "body": body
            })
    results.sort(key=lambda x: x["rank"])
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    col = db[COLLECTION_NAME]
    for doc in results:
        if doc["article_id"]:
            col.update_one({"article_id": doc["article_id"]}, {"$set": doc}, upsert=True)
    client.close()
    return results

def main():
    if len(sys.argv) != 3 or not all(arg.isdigit() and len(arg) == 8 for arg in sys.argv[1:]):
        print("사용법: python NateNewsCrawler.py YYYYMMDD_START YYYYMMDD_END", file=sys.stderr)
        sys.exit(1)
    start_str, end_str = sys.argv[1], sys.argv[2]
    start = datetime.strptime(start_str, "%Y%m%d")
    end = datetime.strptime(end_str, "%Y%m%d")
    if start > end:
        print("ERROR: 시작 날짜는 종료 날짜보다 이전이어야 합니다.", file=sys.stderr)
        sys.exit(1)
    all_data: dict[str, List[dict]] = {}
    current = start
    while current <= end:
        date_code = current.strftime("%Y%m%d")
        print(f"# Crawling date: {date_code}", file=sys.stderr)
        data = scrape_and_save(date_code)
        all_data[date_code] = data
        current += timedelta(days=1)
    print(json.dumps(all_data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
