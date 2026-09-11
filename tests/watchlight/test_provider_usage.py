import pytest
from watchlight.extensions.dashscope.provider import DASHSCOPE_BASE_URL, DashScopeProvider
from watchlight.extensions.deepseek.provider import DEEPSEEK_BASE_URL, DeepSeekProvider
from watchlight.extensions.openai.provider import OPENAI_API_URL, OpenAIProvider


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "model", "url"),
    [
        (OpenAIProvider("test-key"), "gpt-4o-mini", OPENAI_API_URL),
        (
            DeepSeekProvider("test-key"),
            "deepseek-chat",
            f"{DEEPSEEK_BASE_URL}/chat/completions",
        ),
        (
            DashScopeProvider("test-key"),
            "qwen-plus",
            f"{DASHSCOPE_BASE_URL}/chat/completions",
        ),
    ],
)
async def test_openai_compatible_stream_reads_usage_only_final_chunk(
    httpx_mock, provider, model: str, url: str
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=url,
        headers={"content-type": "text/event-stream"},
        text=(
            'data: {"choices":[{"delta":{"content":"ok"}}]}\n\n'
            'data: {"choices":[],"usage":{"prompt_tokens":12,"completion_tokens":3}}\n\n'
            "data: [DONE]\n\n"
        ),
    )

    events = [
        event
        async for event in provider.create_stream(
            model=model,
            messages=[{"role": "user", "content": "hello"}],
        )
    ]

    assert events == [
        {"type": "text_delta", "text": "ok"},
        {"type": "usage", "input_tokens": 12, "output_tokens": 3},
    ]
    request = httpx_mock.get_request()
    assert request is not None
    assert request.read()
    assert b'"stream_options":{"include_usage":true}' in request.content
