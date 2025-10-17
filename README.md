# FlowNews Crawler

RSS 피드를 통한 뉴스 기사 수집 및 요약 시스템

## 개요

- RSS 피드에서 뉴스 기사를 수집
- 중복 기사 필터링 
- 기사 본문 크롤링
- GPT-4o mini를 통한 요약 생성
- MongoDB에 저장

## 주요 구성요소

### Lambda Handler (`lambda_handler.py`)
- 메인 실행 핸들러
- 기사 크롤링 → 전처리 → 저장 파이프라인 관리

### RSS Feed Crawler (`logic/rss_feed_crawler.py`)
- RSS 피드에서 기사 링크 수집
- 기사 본문 크롤링

### Preprocessor (`logic/preprocess.py`)
- OpenRouter를 통한 GPT-4o mini 연동
- Ko-SBERT 전처리용 요약 생성 (150토큰)
- JSON 래핑 제거 및 순수 텍스트 추출

### MongoDB Connector (`logic/mongodb.py`)
- MongoDB 연결 및 데이터 저장
- 중복 기사 체크

## 환경 설정

```bash
# 필수 환경변수
MONGODB_URI=mongodb+srv://...
MONGODB_DB=database_name
MONGODB_COL=collection_name
OPENROUTER_API_KEY=sk-or-v1-...
```

## 사용법

### Lambda 핸들러 실행
```python
python lambda_handler.py
```

### 테스트 이벤트 형식
```json
{
  "data": [{
    "link": "https://example.com/news/123",
    "title": "기사 제목",
    "summary": "기사 요약",
    "date": "2023-10-01T12:00:00Z"
  }]
}
```

## 요약 시스템

- **모델**: OpenAI GPT-4o mini (via OpenRouter)
- **토큰 제한**: 150토큰
- **출력**: 순수 한국어 텍스트 (JSON/마크다운 래핑 제거)
- **목적**: Ko-SBERT 전처리용 간결한 요약

## 기술 스택

- Python 3.9+
- OpenAI SDK (OpenRouter 호환)
- PyMongo
- BeautifulSoup4
- Pydantic
