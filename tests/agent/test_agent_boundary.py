from agent.agent import build_investigator, build_monitor


def test_only_investigator_and_monitor_agents_are_constructed() -> None:
    investigator = build_investigator("assess_feasibility")
    monitor = build_monitor()

    assert investigator.name == "investigator"
    assert monitor.name == "monitor"
    investigator_callbacks = investigator.hooks._registered_callbacks
    monitor_callbacks = monitor.hooks._registered_callbacks
    assert investigator_callbacks
    assert monitor_callbacks
    assert any(
        getattr(callback.callback, "__name__", "") in {"before_tool_call", "after_tool_call"}
        for callbacks in investigator_callbacks.values()
        for callback in callbacks
    )


def test_monitor_has_investigator_handoff_tool() -> None:
    monitor = build_monitor()

    assert "investigator" in monitor.tool_registry.registry

