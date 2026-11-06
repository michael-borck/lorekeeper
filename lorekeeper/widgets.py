"""Normalise interactive lesson widgets from overlay YAML."""

from __future__ import annotations

import re

from .parse import clean_markdown, render_markdown

WIDGET_KINDS = {
    "order",
    "fill",
    "hotspot",
    "review",
    "scenario",
    "calibration",
    "viva",
    "api",
    "sql",
    "terminal",
}


def _render(value) -> str:
    text = clean_markdown(str(value or ""))
    return render_markdown(text) if text.strip() else ""


def _text(value, name: str, lesson_id: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{lesson_id}: {name} is required")
    return result


def normalise_question(raw: dict, index: int) -> dict:
    prompt = str(raw.get("prompt", "")).strip()
    if not prompt:
        raise ValueError(f"checkpoint question {index} has no prompt")

    options_raw = raw.get("options") or []
    options: list[str] = []
    answer = -1

    for position, option in enumerate(options_raw):
        if isinstance(option, dict):
            options.append(str(option.get("text", "")).strip())
            if option.get("correct"):
                answer = position
        else:
            text = str(option).strip()
            options.append(text)
            if raw.get("correct") is not None and text == str(raw["correct"]).strip():
                answer = position

    if "answer" in raw:
        answer = int(raw["answer"])
    if not options:
        raise ValueError(f"checkpoint question {index} has no options")
    if not 0 <= answer < len(options):
        raise ValueError(f"checkpoint question {index} has no valid answer")

    return {
        "id": str(raw.get("id") or f"q{index + 1}"),
        "prompt": prompt,
        "options": options,
        "answer": answer,
        "explanation": str(raw.get("explanation", "")).strip(),
    }


def normalise_order(spec: dict, lesson_id: str) -> list[dict]:
    items = [str(item).strip() for item in spec.get("items") or [] if str(item).strip()]
    if len(items) < 2:
        raise ValueError(f"{lesson_id}: order needs at least two items")
    return [
        {
            "type": "order",
            "prompt": _render(spec.get("prompt")),
            "items": items,
            "explanation": _render(spec.get("explanation")),
        }
    ]


def normalise_fill(spec: dict, lesson_id: str) -> list[dict]:
    passage = _text(spec.get("passage"), "passage", lesson_id)
    blanks_raw = spec.get("blanks") or []
    if not blanks_raw:
        raise ValueError(f"{lesson_id}: fill needs blanks")
    blanks = []
    for index, raw in enumerate(blanks_raw, start=1):
        if isinstance(raw, dict):
            answers = raw.get("answers") or ([raw["answer"]] if "answer" in raw else [])
            hint = str(raw.get("hint", "")).strip()
        else:
            answers = [raw]
            hint = ""
        answers = [str(answer).strip() for answer in answers if str(answer).strip()]
        if not answers:
            raise ValueError(f"{lesson_id}: blank {index} has no answer")
        blanks.append({"answers": answers, "hint": hint})

    markers = [int(marker) for marker in re.findall(r"\[\[(\d+)\]\]", passage)]
    if not markers:
        raise ValueError(f"{lesson_id}: passage needs [[1]] style markers")
    if max(markers) > len(blanks):
        raise ValueError(f"{lesson_id}: passage marker {max(markers)} has no blank")

    return [
        {
            "type": "fill",
            "prompt": _render(spec.get("prompt")),
            "passage": passage,
            "blanks": blanks,
        }
    ]


def normalise_hotspot(spec: dict, lesson_id: str) -> list[dict]:
    markup = _text(spec.get("markup"), "markup", lesson_id)
    targets = []
    for index, raw in enumerate(spec.get("targets") or [], start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"{lesson_id}: hotspot target {index} must be a mapping")
        selector = _text(raw.get("selector"), f"hotspot target {index} selector", lesson_id)
        label = _text(raw.get("label"), f"hotspot target {index} label", lesson_id)
        targets.append(
            {
                "selector": selector,
                "label": label,
                "feedback": _render(raw.get("feedback")),
            }
        )
    if not targets:
        raise ValueError(f"{lesson_id}: hotspot needs targets")
    return [
        {
            "type": "hotspot",
            "prompt": _render(spec.get("prompt")),
            "markup": markup,
            "targets": targets,
        }
    ]


def normalise_review(spec: dict, lesson_id: str) -> list[dict]:
    lines = []
    for index, raw in enumerate(spec.get("lines") or [], start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"{lesson_id}: review line {index} must be a mapping")
        code = str(raw.get("code", "")).rstrip("\n")
        if not code:
            raise ValueError(f"{lesson_id}: review line {index} has no code")
        lines.append(
            {
                "code": code,
                "kind": str(raw.get("kind", "context")),
                "bad": bool(raw.get("bad")),
                "feedback": _render(raw.get("feedback")),
            }
        )
    if not lines:
        raise ValueError(f"{lesson_id}: review needs lines")
    if not any(line["bad"] for line in lines):
        raise ValueError(f"{lesson_id}: review needs at least one bad line")
    return [
        {
            "type": "review",
            "prompt": _render(spec.get("prompt")),
            "lines": lines,
            "explanation": _render(spec.get("explanation")),
        }
    ]


def normalise_scenario(spec: dict, lesson_id: str) -> list[dict]:
    options = []
    for index, raw in enumerate(spec.get("options") or [], start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"{lesson_id}: scenario option {index} must be a mapping")
        options.append(
            {
                "id": str(raw.get("id") or f"o{index}"),
                "label": _text(raw.get("label"), f"scenario option {index} label", lesson_id),
                "outcome": _render(raw.get("outcome")),
                "effects": {
                    str(key): str(value) for key, value in (raw.get("effects") or {}).items()
                },
                "recommended": bool(raw.get("recommended")),
                "feedback": _render(raw.get("feedback")),
            }
        )
    if len(options) < 2:
        raise ValueError(f"{lesson_id}: scenario needs at least two options")
    return [
        {
            "type": "scenario",
            "prompt": _render(spec.get("prompt")),
            "options": options,
            "debrief": _render(spec.get("debrief")),
        }
    ]


def normalise_calibration(spec: dict, lesson_id: str) -> list[dict]:
    options = {}
    for key in ("a", "b"):
        raw = spec.get(key)
        if not isinstance(raw, dict):
            raise ValueError(f"{lesson_id}: calibration needs an '{key}' option")
        options[key] = {
            "title": _text(raw.get("title"), f"calibration {key} title", lesson_id),
            "body": _render(raw.get("body")),
        }
    better = str(spec.get("better", "")).lower()
    if better not in ("a", "b"):
        raise ValueError(f"{lesson_id}: calibration 'better' must be a or b")
    return [
        {
            "type": "calibration",
            "prompt": _render(spec.get("prompt")),
            "options": options,
            "better": better,
            "rationale": _render(spec.get("rationale")),
        }
    ]


def normalise_viva(spec: dict, lesson_id: str) -> list[dict]:
    questions = []
    for index, raw in enumerate(spec.get("questions") or [], start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"{lesson_id}: viva question {index} must be a mapping")
        signals = []
        for signal_index, signal in enumerate(raw.get("signals") or [], start=1):
            if not isinstance(signal, dict):
                raise ValueError(
                    f"{lesson_id}: viva question {index} signal {signal_index} must be a mapping"
                )
            pattern = _text(
                signal.get("pattern"),
                f"viva question {index} signal {signal_index} pattern",
                lesson_id,
            )
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(
                    f"{lesson_id}: viva signal pattern is invalid: {pattern} ({exc})"
                ) from exc
            signals.append(
                {
                    "label": _text(
                        signal.get("label"),
                        f"viva question {index} signal {signal_index} label",
                        lesson_id,
                    ),
                    "pattern": pattern,
                }
            )
        questions.append(
            {
                "prompt": _text(
                    raw.get("prompt"), f"viva question {index} prompt", lesson_id
                ),
                "strong_answer": _render(raw.get("strong_answer")),
                "signals": signals,
                "follow_up": _render(raw.get("follow_up")),
            }
        )
    if not questions:
        raise ValueError(f"{lesson_id}: viva needs questions")
    return [
        {
            "type": "viva",
            "context": _render(spec.get("context")),
            "questions": questions,
            "rubric": [str(item) for item in spec.get("rubric") or []],
        }
    ]


def normalise_api(spec: dict, lesson_id: str) -> list[dict]:
    endpoints = []
    for index, raw in enumerate(spec.get("endpoints") or [], start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"{lesson_id}: api endpoint {index} must be a mapping")
        endpoints.append(
            {
                "id": str(raw.get("id") or f"e{index}"),
                "method": str(raw.get("method", "GET")).upper(),
                "path": _text(raw.get("path"), f"api endpoint {index} path", lesson_id),
                "status": int(raw.get("status", 200)),
                "body": raw.get("body"),
            }
        )
    if not endpoints:
        raise ValueError(f"{lesson_id}: api needs endpoints")
    questions = [
        normalise_question(question, index)
        for index, question in enumerate(spec.get("questions") or [])
    ]
    if not questions:
        raise ValueError(f"{lesson_id}: api needs questions")
    return [
        {
            "type": "api",
            "prompt": _render(spec.get("prompt")),
            "endpoints": endpoints,
            "questions": questions,
        }
    ]


def normalise_sql(spec: dict, lesson_id: str) -> list[dict]:
    return [
        {
            "type": "sql",
            "prompt": _render(spec.get("prompt")),
            "task": _render(spec.get("task")),
            "schema": _text(spec.get("schema"), "schema", lesson_id),
            "seed": str(spec.get("seed", "")),
            "solution": _text(spec.get("solution"), "solution", lesson_id),
        }
    ]


def normalise_terminal(spec: dict, lesson_id: str) -> list[dict]:
    goals = []
    for index, raw in enumerate(spec.get("goals") or [], start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"{lesson_id}: terminal goal {index} must be a mapping")
        goals.append(
            {
                "id": str(raw.get("id") or f"g{index}"),
                "label": _text(raw.get("label"), f"terminal goal {index} label", lesson_id),
            }
        )
    if not goals:
        raise ValueError(f"{lesson_id}: terminal needs goals")

    commands = []
    for index, raw in enumerate(spec.get("commands") or [], start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"{lesson_id}: terminal command {index} must be a mapping")
        pattern = _text(raw.get("pattern"), f"terminal command {index} pattern", lesson_id)
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValueError(
                f"{lesson_id}: terminal pattern is invalid: {pattern} ({exc})"
            ) from exc
        commands.append(
            {
                "pattern": pattern,
                "output": _render(raw.get("output")),
                "completes": [str(item) for item in raw.get("completes") or []],
            }
        )
    if not commands:
        raise ValueError(f"{lesson_id}: terminal needs commands")
    return [
        {
            "type": "terminal",
            "prompt": _render(spec.get("prompt")),
            "host": str(spec.get("host", "operator@workbench")),
            "cwd": str(spec.get("cwd", "~")),
            "goals": goals,
            "commands": commands,
            "help": _render(spec.get("help")),
        }
    ]


WIDGETS = {
    "order": normalise_order,
    "fill": normalise_fill,
    "hotspot": normalise_hotspot,
    "review": normalise_review,
    "scenario": normalise_scenario,
    "calibration": normalise_calibration,
    "viva": normalise_viva,
    "api": normalise_api,
    "sql": normalise_sql,
    "terminal": normalise_terminal,
}


def normalise_widget(kind: str, spec: dict, lesson_id: str) -> list[dict]:
    try:
        handler = WIDGETS[kind]
    except KeyError as exc:
        raise ValueError(f"{lesson_id}: unknown lesson kind '{kind}'") from exc
    return handler(spec, lesson_id)
