from typing import List

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import asyncio


async def preprocess(articles: list) -> list:
    # device = "cuda" if torch.cuda.is_available() else "cpu"
    # embedding_model = SentenceTransformer(
    #     "snunlp/KR-SBERT-V40K-klueNLI-augSTS",
    #     device=device
    # )

    processed = []

    bodies = await summarize_articles(list(map(lambda x: x["body"], articles)))
    for item, body in zip(articles, bodies):
        # user_vector = embedding_model.encode(body, convert_to_numpy=True)
        # item["embedded"] = user_vector.tolist()
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
a_sync_semaphore = asyncio.Semaphore(32)  # control concurrency


async def summarize_articles(bodies: List[str]) -> List[str]:
    async def _worker(article_body: str) -> str:
        async with a_sync_semaphore:
            chain = prompt | llm | parser
            res = await chain.ainvoke({"body": article_body})
            return res.text

    return await asyncio.gather(*[_worker(b) for b in bodies])
