from watchlight.agents.system_prompt.builder import (
    DEFAULT_DEEPCLAW_IDENTITY,
    DEFAULT_WATCHLIGHT_IDENTITY,
    build_system_prompt,
)


def test_default_identity_matches_watchlight_mvp() -> None:
    prompt = build_system_prompt()

    assert "我是 Watchlight" in prompt
    assert "个人情报追踪与决策助理" in prompt
    assert "关注目标、来源范围、触发条件、执行频率和通知策略" in prompt
    assert "明确确认" in prompt
    assert "不得绕过登录、验证码、付费墙" in prompt
    assert "不得虚构工具、数据、来源、后台进度或执行结果" in prompt
    assert "只能依据 watch_tasks_list 的成功结果或平台确定性任务查询结果" in prompt
    assert "会话列表、记忆搜索和聊天历史不能代替" in prompt
    assert "调用失败时" in prompt
    assert "不得据此回答“没有任务”" in prompt
    assert "删除关注任务必须进入平台提供的确定性删除流程" in prompt
    assert "完整的“确认删除”" in prompt
    assert "普通“确认”“确定”" in prompt
    assert "不得声称任务已删除" in prompt
    assert "你是DeepClaw" not in prompt


def test_dynamic_tool_rules_are_preserved() -> None:
    prompt = build_system_prompt(
        tool_descriptions=[{"name": "web_search", "description": "搜索公开网络"}],
        tool_instructions=["搜索后必须给出真实来源。"],
        channel_context="当前渠道：飞书",
    )

    assert "当前渠道：飞书" in prompt
    assert "web_search: 搜索公开网络" in prompt
    assert "搜索后必须给出真实来源。" in prompt


def test_old_identity_symbol_remains_compatible() -> None:
    assert DEFAULT_DEEPCLAW_IDENTITY == DEFAULT_WATCHLIGHT_IDENTITY
