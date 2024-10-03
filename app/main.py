from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from instructor import Instructor
from pydantic import BaseModel

from app.llm.anthropic_client import call, get_client
from app.rate_limit import (
    RateLimitStatus,
    initialize_rate_limiter,
    rate_limit,
    rate_limit_status_only,
)

CONVERT_MARKDOWN_TO_HTML_SYSTEM_PROMPT = """You are an advanced AI web engineer tasked with converting pseudo-markdown into a fully self-contained HTML file. The HTML must include the following guidelines:

1. The HTML must include the Tailwind CSS CDN via <script src="https://cdn.tailwindcss.com"></script>.
2. Focus heavily on the intent of the pseudo-markdown, but adhere to markdown rules as much as possible for structure (e.g., headers, lists, code blocks, etc.).
3. The entire HTML file must be self-contained. No external files (CSS, JS) other than the Tailwind CDN are allowed.
4. Ensure the website looks visually appealing, making use of Tailwind utilities for layout, typography, and spacing. The style_prompt should guide the design decisions.
5. The HTML must be valid and render correctly across modern browsers. Follow best practices for accessibility.
6. Do not include any unnecessary boilerplate code.
7. The output should follow a clean and readable structure, using semantic HTML elements like <header>, <nav>, <section>, <footer>, <article>, etc.
8. Ensure responsiveness by applying appropriate Tailwind classes for different screen sizes.
9. It is important that you dont add more information than the user provided in the markdown. For example, if given just "# Hello World", the output should be relatively close to "<h1>Hello World</h1>" + styling and whatnot.
10. You should not add sections that the user did not provide (i.e. footers). The user will use an inferred component (i.e. <Footer />) to add those sections.
11. Short content should be centered, long content should be left-aligned. You should not mix and match centered and left-aligned content, focus on whats most important then use it for the whole document.
12. Do not say anything other than the HTML content. "Here is the HTML content" is not needed.
13. Always assume the input markdown is the complete application and should be styled as such. For example, even a single sentence should take up the full height / width of the screen. It probably doesn't need to scroll, but it should fit the space. When it doubt, make it look like a fancy slide.

Return only the full HTML content without any markdown formatting.
"""

CONVERT_MARKDOWN_TO_HTML_USER_PROMPT_TEMPLATE = """
Please convert the following pseudo-markdown into a fully self-contained HTML file using Tailwind CSS, and structure it with the following style prompt:
{style_prompt}. Make sure it includes the Tailwind CDN link. Here is the pseudo-markdown: {markdown}
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set up the rate limiter dependency during app startup
    await initialize_rate_limiter()
    yield


app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="app/templates")


@app.get("/")
async def index(
    request: Request,
    status: RateLimitStatus = Depends(rate_limit_status_only),
):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "initial_quota": status.requests_remaining,
            "is_allow_listed": str(status.is_allow_listed).lower(),
        },
    )


# Define models for request and response
class ConvertRequest(BaseModel):
    markdown: str
    style_prompt: str


class ConvertResponse(BaseModel):
    html: str


# API to convert markdown to HTML using OpenAI
@app.post("/convert")
async def convert_markdown(
    request: ConvertRequest,
    client: Instructor = Depends(get_client),
    _=Depends(rate_limit),
) -> ConvertResponse:
    # Using OpenAI API to convert markdown to HTML
    # Generate a response from OpenAI using the new Chat Completions API
    response = call(
        markdown_prompt=CONVERT_MARKDOWN_TO_HTML_USER_PROMPT_TEMPLATE.format(
            markdown=request.markdown, style_prompt=request.style_prompt
        ),
        system_prompt=CONVERT_MARKDOWN_TO_HTML_SYSTEM_PROMPT,
        client=client,
    )

    # Extract the HTML response
    html_output = response.html or "Empty"

    # Return the HTML as a response
    return ConvertResponse(html=html_output)
