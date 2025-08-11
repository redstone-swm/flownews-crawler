import torch
from sentence_transformers import SentenceTransformer
import openai


def preprocess(articles: list) -> list:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    embedding_model = SentenceTransformer(
        "snunlp/KR-SBERT-V40K-klueNLI-augSTS",
        device=device
    )

    processed = []
    for item in articles:
        body = item.get("body", "")
        user_vector = embedding_model.encode(body, convert_to_numpy=True)
        item["embedded"] = user_vector.tolist()
        item["summary"] = get_summary(body)

        processed.append(item)
    return processed

def get_summary(text: str) -> str:
    prompt = f"다음 내용을 한 문장으로 요약해 주세요:\n\n{text}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 유능한 한국어 뉴스 요약가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return ""