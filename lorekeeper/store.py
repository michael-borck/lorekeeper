"""Build the static pack catalogue and the sample store pack."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .book import build_book_pack
from .compile import compile_unit
from .pack import build_pack, unit_from_root
from .registry import engine_root, get_unit
from .signing import key_id, load_private_key, sign_bytes

CATALOG_FORMAT = "lorekeeper.catalog"
CATALOG_VERSION = 1
STORE_PACK = "pocket-incidents"

PACK_ART = {
    "pocket-incidents": ("cybersecurity", "crisis"),
    "information-security": ("cybersecurity", "advisor"),
    "audit-and-control": ("business", "judgement"),
    "assume-breach": ("cybersecurity", "crisis"),
    "speak-software": ("cyberpunk", "advisor"),
    "build-web-guide-ai": ("cyberpunk", "chain"),
    "systems-analysis-and-design": ("business", "judgement"),
    "follow-the-trace": ("noir", "chain"),
    "the-human-edge": ("business", "advisor"),
    "test-the-claim": ("business", "judgement"),
    "substantiate-dont-assume": ("business", "advisor"),
    "conversation-not-delegation": ("university", "advisor"),
    "prove-dont-persuade": ("business", "gamble"),
    "build-ai-understand-ai": ("cyberpunk", "chain"),
    "break-with-permission": ("cybersecurity", "crisis"),
    "follow-the-packet": ("cyberpunk", "chain"),
    "simplebot": ("cyberpunk", "opportunity"),
    "build-it-teach-it": ("university", "advisor"),
    "think-python-direct-ai": ("science", "advisor"),
    "code-python-consult-ai": ("science", "petitioner"),
    "ship-python-orchestrate-ai": ("cyberpunk", "chain"),
    "converse-python-partner-ai": ("cyberpunk", "advisor"),
    "partner-dont-police": ("university", "advisor"),
    "the-absolute-minimum-you-must-know": ("base", "advisor"),
    "the-great-silence": ("space", "crisis"),
    "programming-paradigms": ("cyberpunk", "judgement"),
    "simulate-it": ("science", "gamble"),
    "ai-toys": ("cyberpunk", "opportunity"),
    "security-toys": ("cybersecurity", "advisor"),
    "netsim-field-guide": ("cyberpunk", "chain"),
}

# Hand-picked Quest narrator per pack. It sets the pack's guide and its region
# on the world map; tags are only the fallback for packs without one.
PACK_NARRATOR = {
    "pocket-incidents": "sentinel",
    "information-security": "sentinel",
    "audit-and-control": "sentinel",
    "assume-breach": "sentinel",
    "follow-the-trace": "sentinel",
    "test-the-claim": "sentinel",
    "substantiate-dont-assume": "sentinel",
    "break-with-permission": "sentinel",
    "security-toys": "sentinel",
    "speak-software": "oracle",
    "the-human-edge": "oracle",
    "conversation-not-delegation": "oracle",
    "prove-dont-persuade": "oracle",
    "build-ai-understand-ai": "oracle",
    "the-great-silence": "oracle",
    "ai-toys": "oracle",
    "build-web-guide-ai": "artificer",
    "simplebot": "artificer",
    "think-python-direct-ai": "artificer",
    "code-python-consult-ai": "artificer",
    "ship-python-orchestrate-ai": "artificer",
    "converse-python-partner-ai": "artificer",
    "programming-paradigms": "artificer",
    "follow-the-packet": "courier",
    "netsim-field-guide": "courier",
    "systems-analysis-and-design": "architect",
    "simulate-it": "architect",
    "build-it-teach-it": "mentor",
    "partner-dont-police": "mentor",
    "the-absolute-minimum-you-must-know": "cartographer",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _pocket_incidents(build_root: Path) -> dict:
    unit = get_unit("signal-and-noise")
    source = compile_unit(unit, build_root)
    module = next(
        module for module in source["modules"] if module.get("number") == 11
    )
    module = copy.deepcopy(module)
    module["number"] = 1
    module["slug"] = "incident"
    for lesson in module["lessons"]:
        if str(lesson.get("id", "")).startswith("11-"):
            lesson["id"] = "01-" + str(lesson["id"])[3:]

    story_src = "stories/the-3am-page.json"
    story_path = build_root / "signal-and-noise" / story_src
    if not story_path.is_file():
        raise FileNotFoundError(f"story not found: {story_path}")

    course = {
        "schema": 1,
        "generated_at": _now(),
        "unit": {
            "slug": STORE_PACK,
            "title": "Pocket Incidents: The 3AM Page",
            "theme": "pixel",
            "tags": ["incident", "security", "systems", "story"],
            "level": "beginner",
            "pitch": "A short incident-response pack: evidence, containment and the record.",
            "start": "01-01",
        },
        "modules": [module],
    }

    return {
        "format": "lorekeeper.pack",
        "version": 1,
        "id": STORE_PACK,
        "title": "Pocket Incidents: The 3AM Page",
        "author": "Lorekeeper",
        "licence": "Course content",
        "createdAt": _now(),
        "courses": [
            {
                "slug": STORE_PACK,
                "title": "Pocket Incidents: The 3AM Page",
                "theme": "pixel",
                "level": "beginner",
                "tags": ["incident", "security", "systems", "story"],
                "pitch": "A short incident-response pack: evidence, containment and the record.",
                "start": "01-01",
                "course": course,
                "stories": {
                    story_src: json.loads(story_path.read_text(encoding="utf-8"))
                },
            }
        ],
    }


def _course_source(name: str) -> Path:
    base = Path(
        os.environ.get("LOREKEEPER_COURSE_SOURCE", engine_root().parent / "course-source")
    )
    return base / name


def _information_security(build_root: Path) -> dict:
    root = _course_source("information-security")
    if not root.is_dir():
        raise FileNotFoundError(f"information security source not found: {root}")
    unit = unit_from_root(
        root,
        unit_id="information-security",
        title="Information Security: A Field Guide",
        theme="pixel",
        tags=["security", "risk", "operations", "incident"],
        level="beginner",
        pitch="A field guide to software security, malware, cryptography and incident planning.",
        start="01-01",
    )
    pack = build_pack(unit, build_root)
    pack["licence"] = "Course content"
    return pack


def _audit_and_control(build_root: Path) -> dict:
    root = _course_source("audit-and-control")
    if not root.is_dir():
        raise FileNotFoundError(f"audit and control source not found: {root}")
    unit = unit_from_root(
        root,
        unit_id="audit-and-control",
        title="Audit and Control: A Field Guide",
        theme="storybook",
        tags=["audit", "risk", "controls", "compliance", "security"],
        level="intermediate",
        pitch="A field guide to audit evidence, risk, controls and professional judgement.",
        start="01-01",
    )
    pack = build_pack(unit, build_root)
    pack["licence"] = "Course content"
    return pack


def _assume_breach() -> dict:
    root = engine_root().parents[2] / "books" / "assume-breach"
    if not root.is_dir():
        raise FileNotFoundError(f"assume breach source not found: {root}")
    return build_book_pack(
        root,
        unit_id="assume-breach",
        title="Assume Breach: A First Course in Defensive Security",
        theme="pixel",
        tags=["security", "risk", "incident", "foundations"],
        level="beginner",
        pitch="A first course in defensive security: what to protect, where to spend, and how to respond.",
    )


def _speak_software() -> dict:
    root = engine_root().parents[2] / "books" / "speak-software"
    if not root.is_dir():
        raise FileNotFoundError(f"speak software source not found: {root}")
    return build_book_pack(
        root,
        unit_id="speak-software",
        title="Speak Software: Programming at the Natural-Language Layer",
        theme="pixel",
        tags=["ai", "programming", "agents", "testing"],
        level="beginner",
        pitch="Program at the natural-language layer: specify, verify, decompose and ship software with an AI agent.",
    )


def _build_web_guide_ai() -> dict:
    root = engine_root().parents[2] / "books" / "build-web-guide-ai"
    if not root.is_dir():
        raise FileNotFoundError(f"build web guide ai source not found: {root}")
    return build_book_pack(
        root,
        unit_id="build-web-guide-ai",
        title="Build Web, Guide AI: Business Web Development with AI",
        theme="pixel",
        tags=["web", "html", "css", "javascript", "cms", "react"],
        level="beginner",
        pitch="Build business websites with an AI partner: specify, check, structure, connect and hand over.",
        parts="1-6",
    )


def _systems_analysis_and_design() -> dict:
    root = engine_root().parents[2] / "books" / "frame-the-system-guide-ai"
    if not root.is_dir():
        raise FileNotFoundError(f"systems analysis source not found: {root}")
    return build_book_pack(
        root,
        unit_id="systems-analysis-and-design",
        title="Frame the System, Guide the AI: Systems Analysis and Design in the AI Era",
        theme="storybook",
        tags=["analysis", "design", "requirements", "systems", "ai", "governance"],
        level="beginner",
        pitch="Frame the problem, make requirements checkable, model the decisions and hand over a system that may contain AI.",
        parts="1-4",
    )


def _follow_the_trace() -> dict:
    root = engine_root().parents[2] / "books" / "follow-the-trace"
    if not root.is_dir():
        raise FileNotFoundError(f"follow the trace source not found: {root}")
    return build_book_pack(
        root,
        unit_id="follow-the-trace",
        title="Follow the Trace, Prove the Case: Digital Forensics in Practice",
        theme="pixel",
        tags=["forensics", "security", "evidence", "investigation"],
        level="intermediate",
        pitch="Preserve, examine and report digital evidence, with a companion Docker forensics lab.",
        parts="1-3",
    )


def _the_human_edge() -> dict:
    root = engine_root().parents[2] / "books" / "the-human-edge-using"
    if not root.is_dir():
        raise FileNotFoundError(f"the human edge source not found: {root}")
    return build_book_pack(
        root,
        unit_id="the-human-edge",
        title="The Human Edge: Using AI with Judgement",
        theme="storybook",
        tags=["ai", "judgement", "trust", "verification", "professional"],
        level="beginner",
        pitch="Judge, brief, check and deliver AI-assisted work without surrendering the decision.",
        parts="1-4",
    )


def _test_the_claim() -> dict:
    root = engine_root().parents[2] / "books" / "test-the-claim"
    if not root.is_dir():
        raise FileNotFoundError(f"test the claim source not found: {root}")
    return build_book_pack(
        root,
        unit_id="test-the-claim",
        title="Test the Claim, Rate the Control: A Tessera Audit Workbook",
        theme="storybook",
        tags=["audit", "security", "essential-eight", "evidence", "governance"],
        level="intermediate",
        pitch="A guided workbook for scoping, evidencing and reporting the Tessera security audit.",
        parts="1-3",
    )


def _substantiate_dont_assume() -> dict:
    root = engine_root().parents[2] / "books" / "substantiate-dont-assume"
    if not root.is_dir():
        raise FileNotFoundError(f"substantiate source not found: {root}")
    return build_book_pack(
        root,
        unit_id="substantiate-dont-assume",
        title="Substantiate, Don't Assume: Why the Auditor's Opinion Matters More Than Ever in the Age of AI",
        theme="storybook",
        tags=["audit", "assurance", "risk", "evidence", "ai"],
        level="intermediate",
        pitch="Test the claim, weigh the evidence and form a defensible audit opinion.",
        parts="1-2",
    )


def _conversation_not_delegation() -> dict:
    root = engine_root().parents[2] / "books" / "conversation-not-delegation"
    if not root.is_dir():
        raise FileNotFoundError(f"conversation source not found: {root}")
    return build_book_pack(
        root,
        unit_id="conversation-not-delegation",
        title="Conversation, Not Delegation: How to Think With AI, Not Just Use It",
        theme="storybook",
        tags=["conversation", "ai", "judgement", "prompting", "critical-thinking"],
        level="beginner",
        pitch="Think with AI rather than delegating to it: keep the question, the correction and the evidence visible.",
        parts="1-4",
    )


def _prove_dont_persuade() -> dict:
    root = engine_root().parents[2] / "books" / "prove-dont-persuade"
    if not root.is_dir():
        raise FileNotFoundError(f"prove source not found: {root}")
    return build_book_pack(
        root,
        unit_id="prove-dont-persuade",
        title="Prove, Don't Persuade: Why Proof Beats the Demo in Applied AI",
        theme="storybook",
        tags=["ai", "evaluation", "evidence", "risk", "judgement"],
        level="intermediate",
        pitch="Judge applied AI by evidence, not by the demo: test the claim, measure what matters and report the failures.",
        parts="1-2",
    )


def _build_ai_understand_ai() -> dict:
    root = engine_root().parents[2] / "books" / "build-ai-understand-ai"
    if not root.is_dir():
        raise FileNotFoundError(f"build ai source not found: {root}")
    return build_book_pack(
        root,
        unit_id="build-ai-understand-ai",
        title="Build AI, Understand AI: How Today's LLM Systems Actually Work, in Small Readable Pieces",
        theme="pixel",
        tags=["ai", "llm", "python", "rag", "agents", "evaluation"],
        level="intermediate",
        pitch="Build tiny versions of chat, retrieval, agents and judges, and see what the systems you use are made of.",
        parts="1-7",
    )


def _break_with_permission() -> dict:
    root = engine_root().parents[2] / "books" / "break-with-permission"
    if not root.is_dir():
        raise FileNotFoundError(f"break with permission source not found: {root}")
    return build_book_pack(
        root,
        unit_id="break-with-permission",
        title="Break with Permission: Ethical Hacking in Practice",
        theme="pixel",
        tags=["security", "ethical-hacking", "penetration-testing", "scope", "reporting"],
        level="intermediate",
        pitch="Scope, test and report an authorised security assessment without crossing the boundary.",
        parts="1-3",
    )


def _follow_the_packet() -> dict:
    root = engine_root().parents[2] / "books" / "follow-the-packet"
    if not root.is_dir():
        raise FileNotFoundError(f"follow the packet source not found: {root}")
    return build_book_pack(
        root,
        unit_id="follow-the-packet",
        title="Follow the Packet: An Enterprise Network Field Guide",
        theme="pixel",
        tags=["networking", "routing", "dns", "firewall", "ids", "troubleshooting"],
        level="intermediate",
        pitch="Read a multi-site enterprise network one packet at a time: routing, DNS, policy, faults and baselines.",
        parts="1-3",
    )


def _simplebot() -> dict:
    root = engine_root().parents[2] / "books" / "simplebot"
    if not root.is_dir():
        raise FileNotFoundError(f"simplebot source not found: {root}")
    return build_book_pack(
        root,
        unit_id="simplebot",
        title="SimpleBot: A Small Wrapper, a Real Project",
        theme="pixel",
        tags=["python", "llm", "api", "testing", "teaching", "security"],
        level="beginner",
        pitch="Build a small Python wrapper around an LLM, then handle the edges: prompts, errors, secrets, tests and classroom use.",
        parts="1-3",
    )


def _build_it_teach_it() -> dict:
    root = engine_root().parents[2] / "books" / "build-it-teach-it"
    if not root.is_dir():
        raise FileNotFoundError(f"build it teach it source not found: {root}")
    return build_book_pack(
        root,
        unit_id="build-it-teach-it",
        title="Build It, Teach It: Hands-on AI Projects for the Classroom",
        theme="storybook",
        tags=["ai", "education", "projects", "teaching", "rag", "agents"],
        level="beginner",
        pitch="Build small AI systems and teach the ideas underneath them, with project and classroom tracks.",
        parts="1-4",
    )




def _think_python() -> dict:
    return build_book_pack(
        engine_root().parents[2] / "books" / "think-python-direct-ai",
        unit_id="think-python-direct-ai",
        title="Think Python, Direct AI: Computational Thinking for Beginners",
        theme="pixel",
        tags=["python", "computational-thinking", "ai", "beginners"],
        level="beginner",
        pitch="Learn computational thinking with an AI partner, then direct the code.",
        parts="1-5",
    )


def _code_python() -> dict:
    return build_book_pack(
        engine_root().parents[2] / "books" / "code-python-consult-ai",
        unit_id="code-python-consult-ai",
        title="Code Python, Consult AI: Python Fundamentals for the AI Era",
        theme="pixel",
        tags=["python", "ai", "fundamentals"],
        level="beginner",
        pitch="Build Python fundamentals by consulting AI and verifying the result.",
    )


def _ship_python() -> dict:
    return build_book_pack(
        engine_root().parents[2] / "books" / "ship-python-orchestrate-ai",
        unit_id="ship-python-orchestrate-ai",
        title="Ship Python, Orchestrate AI: Professional Python in the AI Era",
        theme="pixel",
        tags=["python", "professional", "workflow", "testing"],
        level="intermediate",
        pitch="Take a Python project from a folder to a tested, documented, installable release.",
    )


def _converse_python() -> dict:
    return build_book_pack(
        engine_root().parents[2] / "books" / "converse-python-partner-ai",
        unit_id="converse-python-partner-ai",
        title="Converse Python, Partner AI: The Intentional Prompting Methodology",
        theme="pixel",
        tags=["python", "prompting", "ai", "methodology"],
        level="intermediate",
        pitch="Use intentional prompting to design, test and ship Python with an AI partner.",
        parts="1-5",
    )


def _partner_dont_police() -> dict:
    return build_book_pack(
        engine_root().parents[2] / "books" / "partner-dont-police",
        unit_id="partner-dont-police",
        title="Partner, Don't Police: AI in the Business Classroom",
        theme="storybook",
        tags=["education", "ai", "teaching", "assessment"],
        level="intermediate",
        pitch="Design business education that treats AI as a partner rather than a policing problem.",
    )


def _absolute_minimum() -> dict:
    return build_book_pack(
        engine_root().parents[2] / "books" / "the-absolute-minimum-you-must-know",
        unit_id="the-absolute-minimum-you-must-know",
        title="The Absolute Minimum You Must Know",
        theme="pixel",
        tags=["reference", "python", "thinking", "verification"],
        level="beginner",
        pitch="The smallest useful reference for thinking, Python, verification, data and directing AI.",
        parts="1-7",
        sanitize=True,
    )


def _great_silence() -> dict:
    return build_book_pack(
        engine_root().parents[2] / "books" / "the-great-silence",
        unit_id="the-great-silence",
        title="The Great Silence: Six Frames for Thinking About AI at Civilisational Scale",
        theme="storybook",
        tags=["ai", "risk", "civilisation", "essays"],
        level="intermediate",
        pitch="Six frames from the search for aliens, applied to AI at civilisational scale.",
    )


def _programming_paradigms() -> dict:
    return build_book_pack(
        engine_root().parents[2] / "books" / "programming-paradigms",
        unit_id="programming-paradigms",
        title="One Calculator, Three Paradigms: Imperative, Functional and Object-Oriented Python",
        theme="pixel",
        tags=["python", "paradigms", "teaching"],
        level="beginner",
        pitch="The same calculator built three ways, to make programming paradigms visible.",
    )


def _simulate_it() -> dict:
    return build_book_pack(
        engine_root().parents[2] / "books" / "simulate-it",
        unit_id="simulate-it",
        title="Simulate It, Understand It: A Practical Guide to Modelling with SimLab",
        theme="pixel",
        tags=["simulation", "modelling", "teaching", "python"],
        level="intermediate",
        pitch="Turn a system question into a reproducible, validated simulation.",
    )


def _ai_toys() -> dict:
    return build_book_pack(
        engine_root().parents[2] / "books" / "ai-toys-book",
        unit_id="ai-toys",
        title="AI Toys: Six Misconceptions You Can Break",
        theme="pixel",
        tags=["ai", "misconceptions", "teaching", "interactive"],
        level="beginner",
        pitch="Six small interactive toys, each built to break one belief about AI.",
    )


def _security_toys() -> dict:
    return build_book_pack(
        engine_root().parents[2] / "books" / "security-toys-book",
        unit_id="security-toys",
        title="Security Toys: Six Beliefs a Demonstration Can Break",
        theme="pixel",
        tags=["security", "misconceptions", "teaching", "interactive"],
        level="beginner",
        pitch="Six small interactive toys, each built to break one security belief.",
    )


def _netsim_field_guide() -> dict:
    return build_book_pack(
        engine_root().parents[2] / "books" / "netsim-field-guide",
        unit_id="netsim-field-guide",
        title="Build the Network, Watch It Run: A NetSim Field Guide",
        theme="pixel",
        tags=["networking", "simulation", "teaching", "firewall", "labs"],
        level="intermediate",
        pitch="Build topologies in NetSim, follow the packet, test the firewall and author auto-graded labs.",
    )


def _write_pack(out: Path, pack: dict, key) -> dict:
    narrator = PACK_NARRATOR.get(pack["id"], "")
    for course in pack["courses"]:
        if narrator and not course.get("narrator"):
            course["narrator"] = narrator
            course["course"]["unit"]["narrator"] = narrator
    packs_dir = out / "packs"
    packs_dir.mkdir(parents=True, exist_ok=True)
    pack_path = packs_dir / f"{pack['id']}.json"
    pack_path.write_text(
        json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    pack_bytes = pack_path.read_bytes()
    entry = pack["courses"][0]
    return {
        "id": pack["id"],
        "title": pack["title"],
        "description": entry["pitch"],
        "version": "1.0.0",
        "author": pack["author"],
        "licence": pack["licence"],
        "theme": entry["theme"],
        "tags": entry["tags"],
        "level": entry["level"],
        "artSet": PACK_ART.get(pack["id"], ("base", "advisor"))[0],
        "artScene": PACK_ART.get(pack["id"], ("base", "advisor"))[1],
        "narrator": entry.get("narrator", ""),
        "courses": len(pack["courses"]),
        "lessons": sum(len(module["lessons"]) for module in entry["course"]["modules"]),
        "size": pack_path.stat().st_size,
        "sha256": hashlib.sha256(pack_bytes).hexdigest(),
        "keyId": key_id(key) if key else None,
        "signature": sign_bytes(key, pack_bytes) if key else None,
        "url": f"packs/{pack['id']}.json",
    }


def build_store(
    out: Path,
    build_root: Path | None = None,
    key_path: Path | None = None,
) -> dict:
    out = out.resolve()
    build_root = (build_root or engine_root() / "build").resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "packs").mkdir(parents=True, exist_ok=True)

    key = load_private_key(key_path) if key_path else None
    packs = [
        _pocket_incidents(build_root),
        _information_security(build_root),
        _audit_and_control(build_root),
        _assume_breach(),
        _speak_software(),
        _build_web_guide_ai(),
        _systems_analysis_and_design(),
        _follow_the_trace(),
        _the_human_edge(),
        _test_the_claim(),
        _substantiate_dont_assume(),
        _conversation_not_delegation(),
        _prove_dont_persuade(),
        _build_ai_understand_ai(),
        _break_with_permission(),
        _follow_the_packet(),
        _simplebot(),
        _build_it_teach_it(),
        _think_python(),
        _code_python(),
        _ship_python(),
        _converse_python(),
        _partner_dont_police(),
        _absolute_minimum(),
        _great_silence(),
        _programming_paradigms(),
        _simulate_it(),
        _ai_toys(),
        _security_toys(),
        _netsim_field_guide(),
    ]
    catalog_packs = [_write_pack(out, pack, key) for pack in packs]
    catalog = {
        "format": CATALOG_FORMAT,
        "version": CATALOG_VERSION,
        "updatedAt": _now(),
        "packs": catalog_packs,
    }
    (out / "catalog.json").write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out / "README.md").write_text(
        "# Lorekeeper pack store\n\n"
        "Generated by `python3 -m lorekeeper store`. Do not edit by hand.\n\n"
        "The player fetches `catalog.json` and verifies each pack SHA-256 before "
        "import. Packs can contain exercise test code; only install packs you trust.\n",
        encoding="utf-8",
    )
    for extra in out.rglob("._*"):
        extra.unlink()
    return catalog
