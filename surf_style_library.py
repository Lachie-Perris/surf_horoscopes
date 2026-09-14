"""Retrieve safe, condition-matched language from the author's report corpus."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CORPUS = Path(__file__).with_name("surf_report_log_cleaned.txt")
TAGGED_LINE = re.compile(r"^- \[(?P<tags>.+?)\] (?P<text>.+)$", re.M)
PLACE_WORDS = re.compile(
    r"\b(?:Sydney|Wollongong|Newcastle|Lennox|Ballina|Byron|Bondi|"
    r"Northern NSW|Central Coast|Gold Coast|Illawarra)\b", re.I,
)
UNSAFE_DETAIL = re.compile(
    r"\b(?:high tide|low tide|tides?|tidal|first light|this morning|this afternoon|"
    r"tonight|tomorrow|mid-?day|later|soon|get in early|all day|rest of the day|christmas|"
    r"morning|afternoon|evening|dawn|arvo|previous days?|through the day|"
    r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|cams?|"
    r"should|will|likely|expected|forecast|set to|best bet|while you can|may|"
    r"seek out|pack a little|protected|protection|sheltered|corners?|headlands?|if you're keen|"
    r"reporting|extra volume|learners?|groms?|"
    r"north facing|south facing|northern end|southern end|"
    r"\d{1,2}(?::\d{2})?(?:am|pm)|\d+(?:\.\d+)?\s*(?:m|metres?|ft|feet|seconds?|secs?))\b",
    re.I,
)
MEASURED_SIZE = re.compile(
    r"\b(?:ankle|knee|waist|chest|shoulder|head)[- ]high\b|\bdouble overhead\b",
    re.I,
)
STYLE_MOTIFS = {
    "trend": {
        "rising": ("keeps coming", "keeps pumping in", "is showing a little more push"),
        "steady": ("is still hanging in", "is holding its form", "is maintaining a steady run"),
        "easing": ("is slowly easing", "is settling down", "is gradually fading"),
        "unknown": ("is showing", "is moving through", "has a readable presence"),
    },
    "period": {
        "short": ("short-period energy", "closely packed energy", "a restless pulse"),
        "medium": ("a steady pulse", "a workable rhythm", "active, peaky energy"),
        "long": ("long lines", "well-organised sets", "more breathing room between sets"),
    },
    "quality": {
        "light": ("light winds leave the surface open", "the breeze barely marks the surface"),
        "clean": ("cleaner conditions let the lines show their shape", "a tidy surface keeps the better lines readable"),
        "messy": ("surface chop breaks up the lines", "wind texture leaves the open water unsettled", "the open water is wind affected"),
    },
}


@dataclass(frozen=True)
class StyleSentence:
    text: str
    tags: dict[str, str]


def _parse_tags(value: str) -> dict[str, str]:
    return dict(item.split("=", 1) for item in value.split("; ") if "=" in item)


def _eligible(text: str) -> bool:
    words = text.split()
    return (
        8 <= len(words) <= 34
        and not PLACE_WORDS.search(text)
        and not UNSAFE_DETAIL.search(text)
        and not MEASURED_SIZE.search(text)
        and "report:" not in text.lower()
        and text[:1].isupper()
        and "favourable" not in text.lower()
        and text[-1:] in ".!?"
    )


@lru_cache(maxsize=1)
def load_style_library(path: Path = CORPUS) -> tuple[StyleSentence, ...]:
    """Load unique, reusable sentences; return empty when the corpus is absent."""
    if not path.exists():
        return ()
    source = path.read_text(encoding="utf-8")
    seen, items = set(), []
    for match in TAGGED_LINE.finditer(source):
        text = re.sub(r"\s+", " ", match.group("text")).strip()
        key = re.sub(r"\W+", " ", text.lower()).strip()
        if key not in seen and _eligible(text):
            seen.add(key)
            items.append(StyleSentence(text, _parse_tags(match.group("tags"))))
    return tuple(items)


def _direction_matches(tagged: str, actual: str | None) -> bool:
    if not actual or tagged == "unknown":
        return True
    return actual in tagged.replace("–", "-").split("-")


def _score(item: StyleSentence, conditions: dict) -> float | None:
    tags = item.tags
    size = tags.get("size", "unknown")
    size_band = conditions.get("size_band")
    size_map = {"tiny": "tiny", "small": "small", "medium": "unknown",
                "big": "big", "very_big": "big"}
    expected_size = size_map.get(size_band, "unknown")
    if size != "unknown" and expected_size not in size:
        return None
    quality = tags.get("quality", "unknown")
    actual_quality = conditions.get("wind_quality")
    if quality not in ("unknown", actual_quality):
        return None
    period = tags.get("period", "unknown")
    actual_period = conditions.get("period_band")
    if period != "unknown" and actual_period not in period:
        return None
    if not _direction_matches(tags.get("swell", "unknown"), conditions.get("wave_direction")):
        return None
    if not _direction_matches(tags.get("wind", "unknown"), conditions.get("wind_direction")):
        return None
    # Reject sentences whose direction language was not understood by the cleaner.
    has_direction = re.search(r"\b(?:[NSEW]{1,3}(?:/[NSEW]{1,3})?|north|south|east|west|northerly|southerly|easterly|westerly)\b", item.text, re.I)
    if has_direction and tags.get("swell") == "unknown" and tags.get("wind") == "unknown":
        return None
    wind_strength = tags.get("wind_strength", "unknown")
    if wind_strength != "unknown" and wind_strength != conditions.get("wind_strength"):
        return None
    if re.search(r"\b(?:solid|heavy|large|big|tiny|very small|maxing out)\b", item.text, re.I) and size == "unknown":
        return None
    trend = tags.get("trend", "unknown")
    actual_trend = conditions.get("trend", "unknown")
    if trend not in ("unknown", actual_trend):
        return None
    # The offshore point cannot support a claim about a sheltered or exposed bank.
    if tags.get("exposure", "unknown") != "unknown":
        return None
    score = 0.0
    score += 4.0 if quality == actual_quality else 0
    score += 3.0 if expected_size != "unknown" and expected_size in size else 0
    score += 3.0 if period != "unknown" and actual_period in period else 0
    score += 2.0 if tags.get("swell") != "unknown" else 0
    score += 2.0 if tags.get("wind") != "unknown" else 0
    score += 2.0 if wind_strength != "unknown" else 0
    score += 2.0 if actual_trend != "unknown" and trend == actual_trend else 0
    score += 1.0 if tags.get("exposure") == "unknown" else 0
    # A retrieved line must have at least one useful condition match.
    return score if score >= 4 else None


def retrieve_style_line(conditions: dict, sign: str, slot: str, used: set[str]) -> str | None:
    """Compose a safe line from condition-matched motifs found in the corpus.

    Whole historical sentences remain searchable through ``load_style_library``
    for analysis, but are not emitted because they can contain hidden context.
    """
    seed = f"{conditions.get('valid_time_utc')}|{conditions.get('location')}|{sign}|{slot}"
    choices = (
        STYLE_MOTIFS["trend"].get(conditions.get("trend"), STYLE_MOTIFS["trend"]["unknown"]),
        STYLE_MOTIFS["period"][conditions["period_band"]],
        STYLE_MOTIFS["quality"][conditions["wind_quality"]],
    )
    for attempt in range(18):
        selected = []
        for index, options in enumerate(choices):
            digest = hashlib.sha256(f"{seed}|{attempt}|{index}".encode()).digest()
            selected.append(options[int.from_bytes(digest[:4], "big") % len(options)])
        quality = selected[2][0].upper() + selected[2][1:]
        frame = int.from_bytes(hashlib.sha256(f"{seed}|{attempt}|frame".encode()).digest()[:4], "big") % 3
        text = (
            f"The swell {selected[0]}, carrying {selected[1]}, while {selected[2]}."
            if frame == 0 else
            f"With {selected[1]} beneath it, the swell {selected[0]}; {selected[2]}."
            if frame == 1 else
            f"{quality}. Underneath, the swell {selected[0]} with {selected[1]}."
        )
        if text not in used:
            used.add(text)
            return text
    return None
