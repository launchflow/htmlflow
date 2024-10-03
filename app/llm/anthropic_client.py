import instructor
from anthropic import Anthropic
from pydantic import BaseModel

from app.infra import claude_api_key

_client = None


class HTMLResponse(BaseModel):
    html: str


def get_client():
    global _client
    if _client is None:
        _client = instructor.from_anthropic(
            Anthropic(api_key=claude_api_key.version(use_cache=True))
        )

    return _client


def call(
    markdown_prompt: str,
    system_prompt: str,
    # model: str = "claude-3-5-sonnet-20240620",
    model: str = "claude-3-haiku-20240307",
    max_tokens: int = 4000,
    temperature: float = 0,
    client: instructor.Instructor = get_client(),
):
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": markdown_prompt,
                    }
                ],
            }
        ],
        response_model=HTMLResponse,
    )
    return response


if __name__ == "__main__":
    print(claude_api_key.version())
