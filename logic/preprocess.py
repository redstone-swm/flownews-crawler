from dotenv import load_dotenv

from openai import OpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import json
import re
from typing import List
import os

def summarize_articles(bodies: List[str]) -> List[str]:
    results = []
    for article_body in bodies:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_MSG},
                {"role": "user", "content": USER_TEMPLATE.format(body=article_body, format_instructions=parser.get_format_instructions())}
            ],
            temperature=0,
            max_tokens=300
        )
        content = response.choices[0].message.content
        results.append(extract_text_from_response(content))
    return results


def preprocess(articles: list) -> list:
    processed = []
    bodies = summarize_articles([x["body"] for x in articles])
    for item, body in zip(articles, bodies):
        item["summary"] = body
        processed.append(item)
    return processed


class Summary(BaseModel):
    text: str = Field(..., description="기사 내용을 150토큰으로 요약")


load_dotenv()

parser = PydanticOutputParser(pydantic_object=Summary)

def extract_text_from_response(content: str) -> str:
    """
    모델 응답에서 불필요한 JSON 래핑/따옴표 제거.
    오직 순수 요약 텍스트만 반환.
    """
    s = content.strip()

    # JSON 객체 형태일 때
    if s.startswith("{") and s.endswith("}"):
        try:
            data = json.loads(s)
            if "text" in data:
                s = data["text"]
        except json.JSONDecodeError:
            pass

    # 혹시 따옴표로 감싸인 경우
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1]

    # 코드펜스/백틱 제거
    s = re.sub(r"^```[\s\S]*?```$", "", s)
    # 개행/공백 정리
    s = re.sub(r"\s+", " ", s).strip()
    return s


SYSTEM_MSG = (
    "너는 뉴스 요약기다. 반드시 **순수 한국어 텍스트** 한 문단만 출력한다. "
    "다음은 절대 출력하지 말 것: 마크다운, 코드블록(```), JSON, 리스트/불릿, 머리말, "
    "인용부호(따옴표/쌍따옴표), 백틱, 메타설명. "
    "출력은 앞뒤 공백 없는 한 문단이어야 한다."
)

USER_TEMPLATE    = """
당신은 뉴스 기사 내용을 Ko-SBERT 전처리를 위해서 핵심만 간결하게 요약하는 전문가입니다.
주어진 기사 내용을 읽고, 다음 형식에 맞춰 150토큰으로 요약해주세요.
- 다음 텍스트가 길더라도 모든 내용을 검토해서 요약해야 합니다.
- 중간에 끊지 말고, 전체 텍스트를 기반으로 핵심 요약을 작성하세요.
- 불필요한 수식어나 추측 없이 사실 위주로 작성하세요.
- 기사 내용 초반에 등장하는 언론사명이나 기자명은 요약에 포함하지 마세요.

{format_instructions}

기사 내용:
{body}
"""

prompt = PromptTemplate(
    template=USER_TEMPLATE,
    input_variables=["body"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)