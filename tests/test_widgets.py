import pytest

from lorekeeper.widgets import normalise_widget


def test_order_keeps_the_correct_sequence():
    block = normalise_widget(
        "order",
        {"prompt": "Order it", "items": ["one", "two"], "explanation": "why"},
        "01-01",
    )[0]
    assert block["type"] == "order"
    assert block["items"] == ["one", "two"]
    assert block["prompt"].startswith("<p>")


def test_fill_requires_markers_and_blanks():
    block = normalise_widget(
        "fill",
        {
            "passage": "Set [[1]] and [[2]].",
            "blanks": [{"answers": ["a"]}, {"answers": ["b", "c"], "hint": "try c"}],
        },
        "01-02",
    )[0]
    assert len(block["blanks"]) == 2
    with pytest.raises(ValueError, match="markers"):
        normalise_widget(
            "fill", {"passage": "No blanks", "blanks": [{"answers": ["a"]}]}, "01-02"
        )


def test_review_needs_a_bad_line():
    block = normalise_widget(
        "review",
        {
            "lines": [
                {"code": "context", "kind": "context"},
                {"code": "- assertion", "kind": "del", "bad": True, "feedback": "why"},
            ]
        },
        "01-03",
    )[0]
    assert block["lines"][1]["bad"] is True
    with pytest.raises(ValueError, match="bad line"):
        normalise_widget("review", {"lines": [{"code": "context"}]}, "01-03")


def test_scenario_needs_two_options():
    block = normalise_widget(
        "scenario",
        {
            "prompt": "Choose",
            "options": [
                {"label": "A", "recommended": True},
                {"label": "B", "effects": {"Cost": "High"}},
            ],
        },
        "01-04",
    )[0]
    assert len(block["options"]) == 2
    assert block["options"][0]["recommended"] is True


def test_calibration_requires_a_and_b():
    with pytest.raises(ValueError, match="calibration"):
        normalise_widget("calibration", {"prompt": "Pick", "a": {"title": "A"}}, "01-05")


def test_viva_rejects_invalid_signal_pattern():
    with pytest.raises(ValueError, match="pattern is invalid"):
        normalise_widget(
            "viva",
            {
                "questions": [
                    {
                        "prompt": "Why?",
                        "signals": [{"label": "Bad", "pattern": "[unclosed"}],
                    }
                ]
            },
            "01-06",
        )


def test_api_questions_are_normalised():
    block = normalise_widget(
        "api",
        {
            "endpoints": [{"path": "/wp-json/wp/v2/users", "body": []}],
            "questions": [{"prompt": "What?", "options": ["a", "b"], "answer": 1}],
        },
        "01-07",
    )[0]
    assert block["endpoints"][0]["status"] == 200
    assert block["questions"][0]["answer"] == 1


def test_terminal_rejects_invalid_pattern():
    with pytest.raises(ValueError, match="pattern is invalid"):
        normalise_widget(
            "terminal",
            {
                "goals": [{"id": "g1", "label": "Do it"}],
                "commands": [{"pattern": "[bad", "completes": ["g1"]}],
            },
            "01-08",
        )
