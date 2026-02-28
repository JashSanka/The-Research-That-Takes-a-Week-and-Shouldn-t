import json
from groq import AsyncGroq
from app.config import settings
from app.utils.helpers import strip_json_codeblock

client = None
if settings.GROQ_API_KEY:
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)


async def decompose_query(query: str) -> list[str]:
    """
    Decomposes a broad research query into 5 focused sub-questions using Groq LLM.
    """
    if not client:
        print("Warning: GROQ_API_KEY not set. Using fallback decomposition.")
        return [
            f"What is the market size and growth for {query}?",
            f"What is the regulatory environment for {query}?",
            f"What is the competitive landscape for {query}?",
            f"What are the funding trends for {query}?",
            f"What are the risk factors for {query}?"
        ]

    prompt = f"""You are an expert research analyst. Break down the following complex research query into exactly 5 focused sub-questions that need to be answered to provide a comprehensive report.
Return ONLY a valid JSON object with a single key "questions" whose value is an array of 5 strings. Do not include any other text, markdown formatting, or preamble.

Query: "{query}"
    """

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1024,
            response_format={"type": "json_object"}
        )

        content = strip_json_codeblock(response.choices[0].message.content)
        data = json.loads(content)

        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            for val in data.values():
                if isinstance(val, list):
                    return val

        return [query]

    except Exception as e:
        print(f"Error in decompose_query: {e}")
        return [f"What are the key aspects of: {query}"]
