"""Clean and structure the author's historical East Coast surf reports.

The original file is read-only input. Tags are explicitly heuristic because the
source does not contain matching observations, model data, or dates.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

SOURCE = Path(__file__).with_name("surf_report_log.txt")
DESTINATION = Path(__file__).with_name("surf_report_log_cleaned.txt")

HEADING = re.compile(
    r"(?P<report>(?P<region>[A-Za-z][A-Za-z &\-/]+?) Regional "
    r"(?P<time>Morning|Afternoon) Report:)"
    r"|(?P<outlook>Rest of the Day Outlook:)"
    r"|(?P<break>\[SECTION_BREAK\])", re.I,
)
HIRING = re.compile(
    r"Forecasting SURF\?.*?Surfline.s Australian Forecast team\s*-\s*find out more and apply",
    re.I | re.S,
)

REPAIRS = {
    "We�re": "We're", "Surfline�s": "Surfline's", "it�s": "it's",
    "It�s": "It's", "there�s": "there's", "There�s": "There's",
    "you�ll": "you'll", "You�ll": "You'll", "don�t": "don't",
    "doesn�t": "doesn't", "isn�t": "isn't", "aren�t": "aren't",
    "won�t": "won't", "can�t": "can't", "shouldn�t": "shouldn't",
    "we�ll": "we'll", "We�ll": "We'll", "we�ve": "we've",
    "they�re": "they're", "that�s": "that's", "That�s": "That's",
    "today�s": "today's", "morning�s": "morning's", "afternoon�s": "afternoon's",
    "coast�s": "coast's", "ocean�s": "ocean's", "swell�s": "swell's",
    "you�re": "you're", "�": "'",
}


def clean_text(text: str) -> str:
    for broken, repaired in REPAIRS.items():
        text = text.replace(broken, repaired)
    text = text.replace("\r", "")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "-", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def sentences(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+", text) if item.strip()]


def first_match(pattern: str, text: str, default="unknown") -> str:
    match = re.search(pattern, text, re.I)
    if not match:
        return default
    direction = match.group(1).upper()
    if match.lastindex and match.lastindex > 1 and match.group(2):
        direction += "–" + match.group(2).upper()
    return direction


def infer_tags(sentence: str, section_type: str) -> dict[str, str]:
    lower = sentence.lower()
    tiny = any(word in lower for word in ("tiny", "ankle", "near-flat", "near flat", "flat"))
    big = any(word in lower for word in ("overhead", "double overhead", "big", "large", "solid size"))
    small = any(word in lower for word in ("small", "waist", "chest", "shoulder", "knee"))
    size = "mixed" if big and small else "big (~2–3 m)" if big else "tiny (<0.5 m)" if tiny else "small (~0.5–1.5 m)" if small else "unknown"
    swell = first_match(r"\b(N|NNE|NE|ENE|E|ESE|SE|SSE|S|SSW|SW|WSW|W|WNW|NW|NNW)(?:/(N|NNE|NE|ENE|E|ESE|SE|SSE|S|SSW|SW|WSW|W|WNW|NW|NNW))?\s+swell", sentence)
    if swell == "unknown":
        swell = next((short for word, short in (("east swell", "E"), ("south swell", "S"), ("north swell", "N"), ("west swell", "W")) if word in lower), "unknown")
    seconds = re.search(r"\b(\d{1,2})(?:\s*[-–]\s*second|\s+second)", lower)
    if seconds:
        value = int(seconds.group(1)); period = "short (<9 s)" if value < 9 else "medium (9–12 s)" if value < 12 else "long (≥12 s)"
    elif "short-period" in lower or "short period" in lower or "windswell" in lower:
        period = "short (<9 s)"
    elif "long-period" in lower or "long period" in lower or "long lines" in lower or "long-lines" in lower:
        period = "long (≥12 s)"
    else:
        period = "unknown"
    wind = first_match(r"\b(N|NNE|NE|ENE|E|ESE|SE|SSE|S|SSW|SW|WSW|W|WNW|NW|NNW)(?:/(N|NNE|NE|ENE|ESE|SE|SSE|SSW|SW|WSW|WNW|NW|NNW))?\s+(?:wind|winds|breeze|sea breeze)", sentence)
    if wind == "unknown":
        wind = next((short for word, short in (("southerly", "S"), ("northerly", "N"), ("easterly", "E"), ("westerly", "W")) if word in lower), "unknown")
    if any(term in lower for term in ("gusty", "strong", "fresh")): strength = "fresh/strong"
    elif "moderate" in lower: strength = "moderate"
    elif any(term in lower for term in ("light", "very light", "calm")): strength = "light"
    else: strength = "unknown"
    clean = any(term in lower for term in ("clean", "tidy", "glassy", "groom", "smooth"))
    messy = any(term in lower for term in ("messy", "bumpy", "chop", "blown out", "wind affected", "lumpy", "washy", "poor quality"))
    quality = "mixed" if clean and messy else "clean" if clean else "messy" if messy else "unknown"
    rising = any(term in lower for term in ("build", "rise", "uptick", "pulse", "increase", "strengthen"))
    easing = any(term in lower for term in ("ease", "fade", "drop", "settle down", "decline"))
    steady = any(term in lower for term in ("maintain", "hold", "hang around", "hanging in", "consistent", "stay"))
    trend_count = sum((rising, easing, steady))
    trend = "mixed" if trend_count > 1 else "rising" if rising else "easing" if easing else "steady" if steady else "unknown"
    exposed = any(term in lower for term in ("exposed", "open beach", "open stretch", "open coast"))
    sheltered = any(term in lower for term in ("shelter", "protected", "corner", "inside", "point", "north facing", "southern end"))
    exposure = "mixed" if exposed and sheltered else "exposed" if exposed else "sheltered" if sheltered else "unknown"
    return {"size": size, "swell": swell, "period": period, "wind": wind,
            "wind_strength": strength, "quality": quality, "trend": trend,
            "exposure": exposure, "section": section_type}


def parse_sections(text: str) -> list[dict]:
    matches = list(HEADING.finditer(text)); records = []
    last_region = "Unspecified East Coast"
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = clean_text(text[match.end():end])
        if match.group("break"):
            continue
        if match.group("report"):
            region = clean_text(match.group("region")); last_region = region
            kind = f"{match.group('time').title()} report"
        else:
            region = last_region; kind = "Outlook"
        # Exclude obvious orphan fragments and headings with no usable prose.
        if len(body.split()) >= 12 and body[0].isupper() and body[-1] in ".!?":
            records.append({"region": region, "type": kind, "text": body})
    unique = [] ; seen = set()
    for record in records:
        key = re.sub(r"\W+", " ", record["text"].lower()).strip()
        if key not in seen:
            seen.add(key); unique.append(record)
    return unique


def language_bank(records: list[dict]) -> list[tuple[str, int]]:
    phrases = (
        "still hanging in", "long-lines of", "worth hunting around", "open stretches",
        "surface chop", "settled down to", "smaller and cleaner", "keeps pumping in",
        "keeps coming", "on tap", "at first light", "get among", "showing some solid size",
        "holding up", "cleaner conditions", "southern corners", "protected breaks",
        "wind affected", "blown out", "pulse through", "maintain its form",
        "a little more push", "straight and washy", "tired arms", "plenty of energy",
    )
    joined = " ".join(record["text"].lower() for record in records)
    return sorted(((phrase, len(re.findall(re.escape(phrase), joined))) for phrase in phrases), key=lambda item: (-item[1], item[0]))


def render(records: list[dict]) -> str:
    counts = Counter(record["type"] for record in records)
    lines = ["CLEANED AUSTRALIAN EAST COAST SURF REPORT CORPUS", "=" * 52, "",
             "SOURCE: surf_report_log.txt (preserved unchanged)",
             "NOTE: Dates and raw observations were unavailable. All condition tags are estimates inferred from wording, not measured data.",
             "SIZE ASSUMPTIONS: tiny <0.5 m; small ~0.5–1.5 m; big ~2–3 m. 'Mixed' means the sentence describes more than one exposure or size.",
             f"UNIQUE SECTIONS: {len(records)} ({', '.join(f'{key}: {value}' for key, value in sorted(counts.items()))})", "",
             "FORECAST LANGUAGE INDEX", "-" * 23]
    lines.extend(f"{phrase} [{count} uses]" for phrase, count in language_bank(records) if count)
    lines += ["", "CLEANED AND TAGGED SECTIONS", "-" * 27, ""]
    for index, record in enumerate(records, 1):
        lines += [f"[ENTRY {index:04d}]", f"TYPE: {record['type']}", f"REGION: {record['region']}", "TEXT:", record["text"], "SENTENCE TAGS:"]
        for sentence in sentences(record["text"]):
            tags = infer_tags(sentence, record["type"])
            tag_text = "; ".join(f"{key}={value}" for key, value in tags.items())
            lines.append(f"- [{tag_text}] {sentence}")
        lines.append("")
    return "\n".join(lines)


def main():
    raw = SOURCE.read_text(encoding="utf-8", errors="replace")
    raw = HIRING.sub("\n[SECTION_BREAK]\n", raw)
    records = parse_sections(raw)
    DESTINATION.write_text(render(records), encoding="utf-8")
    print(f"Wrote {DESTINATION.name}: {len(records)} unique structured sections")


if __name__ == "__main__":
    main()
