from openai import OpenAI

from app.infra import openai_api_key

_client = None


def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=openai_api_key.version(use_cache=True))
    return _client


if __name__ == "__main__":
    print(openai_api_key.version())
