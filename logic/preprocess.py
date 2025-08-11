from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


from typing import List

def summarize_articles(bodies: List[str]) -> List[str]:
    results = []
    for article_body in bodies:
        chain = prompt | llm | parser
        res = chain.invoke({"body": article_body})
        results.append(res.text)
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

template = """
당신은 뉴스 기사 내용을 Ko-SBERT 전처리를 위해서 핵심만 간결하게 요약하는 전문가입니다.
주어진 기사 내용을 읽고, 다음 형식에 맞춰 150토큰으로 요약해주세요.
{format_instructions}

기사 내용:
{body}
"""

prompt = PromptTemplate(
    template=template,
    input_variables=["body"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0, max_retries=2)