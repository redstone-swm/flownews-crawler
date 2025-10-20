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
        results.append(content)
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
    "너는 한국어 뉴스 요약기다. 출력은 순수 한국어 텍스트로, "
    "정확히 두 문단을 출력한다(각 문단은 개행으로 구분). "
    "마크다운, 코드블록, JSON, 불릿, 따옴표, 백틱, 메타설명 금지. "
    "앞뒤 공백 없이 출력한다."
)

USER_TEMPLATE = (
    "당신은 정치, 경제, 사회, 산업, 연예, 스포츠 등 다양한 분야의 뉴스를 요약하는 전문가입니다. "
    "주어진 기사를 읽고 Ko-SBERT 전처리에 적합하면서도 가독성이 높은 형태로 **50토큰** 이내에 한국어 요약문을 작성하세요. "
    "요약은 반드시 사실 중심으로 하며, 불필요한 수식어나 추측 표현을 사용하지 마세요. "
    "출력 형식: "
    "1) 첫번째 문장: 기사 전체의 주요 사건, 이슈 또는 결과를 간결히 요약. "
    "2) 두번째 문장: 배경, 수치, 인물, 원인·영향 등 구체적 사실 정보 요약. "
    "문단 구분은 별도 표기 없이 개행으로만 구분하세요. "
    "카테고리별 유의사항: "
    "정치·경제·사회·산업은 정책, 수치, 기관·기업명, 발언 주체를 명확히 포함하고, "
    "연예·스포츠는 주요 인물·사건·결과 중심으로, 자연·생활·기후는 현상과 영향 중심으로 요약하세요. "
    "자연스럽고 간결한 문체를 사용하세요. "
    "기사 내용: {body}"
)

prompt = PromptTemplate(
    template=USER_TEMPLATE,
    input_variables=["body"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)