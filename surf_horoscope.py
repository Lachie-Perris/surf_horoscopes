"""Lightweight surf-horoscope generator enriched by free daily astrology data."""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from astrology_context import fetch_cosmic_context
from surf_style_library import retrieve_style_line

STAR_SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
              "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")

SIGN_VOICES = {
    "Aries": ("decisive energy", "Let commitment begin after observation, not before it.",
              ("choose one peak and commit", "pause for two sets before moving")),
    "Taurus": ("patient rhythm", "Quality will matter more than wave count today.",
               ("settle into the rhythm", "wait for the wave with real shape")),
    "Gemini": ("quick adaptability", "Read changing peaks without scattering your attention.",
               ("adjust once, then trust the choice", "watch how the peak shifts")),
    "Cancer": ("strong intuition", "Sensitivity is useful when it becomes careful observation.",
               ("trust the pattern you notice", "take a quiet shoreline read")),
    "Leo": ("warm confidence", "The best line needs presence, not performance.",
            ("surf one wave with generous style", "make space as confidently as you take it")),
    "Virgo": ("precise attention", "Refinement beats perfection when the sea keeps moving.",
              ("refine one part of your take-off", "make positioning the practice")),
    "Libra": ("instinct for balance", "Find the point where effort and ease meet.",
              ("share the peak and preserve your rhythm", "choose the cleanest balanced line")),
    "Scorpio": ("calm intensity", "Meet the ocean's force without trying to overpower it.",
                ("commit fully to a carefully chosen wave", "keep your breathing steady")),
    "Sagittarius": ("adventurous perspective", "Exploration works best when respect sets the boundary.",
                    ("explore a different bank after watching it", "leave room for an unexpected line")),
    "Capricorn": ("disciplined patience", "Positioning and persistence will outperform urgency.",
                  ("build the session one sound decision at a time", "hold the patient position")),
    "Aquarius": ("independent imagination", "Try the unusual line after understanding the ordinary one.",
                 ("experiment with one fresh line", "look beyond the obvious peak")),
    "Pisces": ("deep sensitivity", "Tune into the sea without drifting away from the facts.",
               ("follow the ocean's tempo", "turn feeling into a deliberate line")),
}

# Wind directions are FROM, clockwise from north.
SPOT_RULES = {
    "Bondi Beach": {"sectors": ((270.0, 360.0), (0.0, 0.0)), "swell": ((45, 180),), "label": "W to N"},
    "Byron Bay": {"sectors": ((135.0, 225.0),), "swell": ((45, 180),), "label": "SW to SE via S"},
}

SIGN_ELEMENTS = {
    "Aries": "fire", "Leo": "fire", "Sagittarius": "fire",
    "Taurus": "earth", "Virgo": "earth", "Capricorn": "earth",
    "Gemini": "air", "Libra": "air", "Aquarius": "air",
    "Cancer": "water", "Scorpio": "water", "Pisces": "water",
}
SIGN_RULERS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Pluto",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Uranus", "Pisces": "Neptune",
}

LOCATION_OPENINGS = {
    "Bondi Beach": (
        "The eastern edge is carrying a {mood} mood today.",
        "The ocean arrives with a {mood} but unmistakable presence.",
        "The water feels {mood}, asking the city to match its tempo.",
        "The day wakes to an ocean with a distinctly {mood} character.",
    ),
    "Byron Bay": (
        "Around the headland, the sea settles into a {mood} rhythm.",
        "The open horizon holds a {mood} ocean today.",
        "The water carries a {mood} energy around the bay.",
        "The sea feels {mood}, moving to its own spacious tempo.",
    ),
}
FEELING_LINES = (
    "Its character is {height_feel}, while the rhythm underneath is {energy}.",
    "On the surface it feels {height_feel}; beneath that, the pulse is {energy}.",
    "The ocean's body is {height_feel}, carried by energy that is {energy}.",
    "Expect water that feels {height_feel}, with a rhythm that remains {energy}.",
)
EAST_COAST_HEIGHT_LINES = {
    "tiny": ("The ocean is close to flat, with only faint lines showing along the beach.",
             "There is very little push in the water, so any surfable line will need careful hunting."),
    "small": ("The smaller lines still offer something surfable when the right bank draws them in.",
              "Wave heights sit in a playful range, with the better-shaped lines worth hunting down."),
    "medium": ("There is useful size across the open stretches, with enough energy to keep the session moving.",
               "The swell is showing a little more push, without becoming overly demanding."),
    "big": ("Solid sets are showing across the exposed stretches, with plenty of energy moving through the water.",
            "The exposed beaches are carrying serious size, while protected corners may offer a smaller option."),
    "very_big": ("Heavy lines are moving into the exposed coast, demanding patience, experience and careful judgement.",
                 "There is consequential size on the open stretches, with sheltered options the sensible place to look."),
}
EAST_COAST_PERIOD_LINES = {
    "short": ("Short-period energy keeps the ocean active and closely packed.",
              "The swell is restless, with limited space between pulses."),
    "medium": ("The swell has a workable rhythm, with the better sets showing a clearer shape.",
               "There is a steady pulse underneath the surface texture."),
    "long": ("Long lines are drawing into the coast with more space and intent between sets.",
             "The longer-period pulse gives each line time to organise before it reaches the beach."),
}
WIND_LINES = {
    "light": (
        "A light {wind_dir} breath leaves the surface largely untouched.",
        "The breeze is quiet enough for the ocean's natural shape to show through.",
        "Little wind interferes, so the water keeps an open, unforced face.",),
    "clean": (
        "The {wind_dir} wind is grooming the surface into cleaner lines.",
        "A tidy {wind_dir} breeze gives the ocean a more polished face.",
        "The wind is helping the sea organise itself into clean, readable lines.",
        "Cleaner conditions are settling in under the {wind_dir} breeze.",),
    "messy": (
        "The {wind_dir} wind is roughening the surface and breaking up the lines.",
        "Wind texture makes the ocean feel scattered, so patience will reveal the better moments.",
        "The surface is untidy under the {wind_dir} wind, with shape hiding inside the noise.",
        "The open stretches are wind affected, so it is worth hunting around for a cleaner corner.",),
}
TIDE_LINES = {
    "rising": (
        "The rising tide gives the water a gathering, expectant pull.",
        "The rising tide is drawing water back in, adding a sense of arrival to the session.",
    ),
    "falling": (
        "The falling tide gives the ocean a releasing, outward-moving feeling.",
        "As the tide draws away, the sea feels more exposed and revealing.",
    ),
    "high": (
        "Near high water, the ocean feels full and briefly suspended.",
        "The tide is near its upper turn, lending the shoreline a full, held breath.",
    ),
    "low": (
        "Near low water, the shoreline feels open, exposed and searching.",
        "The tide is near its lower turn, revealing more of the coast's underlying shape.",
    ),
    "unavailable": ("The tidal rhythm is not available for this reading.",),
}
HEADLINE_PATTERNS = {
    "Aries": "Commit to {subject}", "Taurus": "Wait for {subject}",
    "Gemini": "Read {subject}", "Cancer": "Trust {subject}",
    "Leo": "Meet {subject} with Presence", "Virgo": "Find Precision in {subject}",
    "Libra": "Balance Within {subject}", "Scorpio": "Go Deeper into {subject}",
    "Sagittarius": "Explore {subject}", "Capricorn": "Build Around {subject}",
    "Aquarius": "Reimagine {subject}", "Pisces": "Feel {subject}",
}
HEADLINE_SUBJECTS = {
    "Bondi Beach": {
        "light": ("the Open {mood} Face", "the {mood} Eastern Pulse"),
        "clean": ("the Clean {mood} Pulse", "the Groomed {mood} Lines"),
        "messy": ("Shape in the {mood} Static", "the Restless {mood} Edge"),
    },
    "Byron Bay": {
        "light": ("the Open {mood} Rhythm", "the {mood} Headland Pulse"),
        "clean": ("the Clean {mood} Rhythm", "the Groomed {mood} Headland Lines"),
        "messy": ("Shape in the {mood} Texture", "the Restless {mood} Headland Water"),
    },
}


@dataclass
class Horoscope:
    sign: str
    headline: str
    reading: str
    surf_intention: str
    cosmic_alignment: str


@dataclass
class SpotHoroscopes:
    location: str
    conditions_summary: str
    horoscopes: list[Horoscope]

    def model_dump_json(self, indent=2):
        return json.dumps(asdict(self), indent=indent, ensure_ascii=False)


def compass_direction(degrees):
    points = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
              "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")
    return points[int((degrees % 360 + 11.25) // 22.5) % 16]


def _in_sector(direction, start, end):
    direction %= 360
    if start == end == 0:
        return direction == 0
    return start <= direction <= end if start <= end else direction >= start or direction <= end


def interpret_conditions(row):
    """Turn forecast values into explicit, auditable writing facts."""
    location = str(row["location"])
    if location not in SPOT_RULES:
        raise KeyError(f"No wind rule configured for {location!r}")
    hs, period = float(row["wave_height_m"]), float(row["primary_period_s"])
    wind_speed = float(row["wind_speed_m_s"])
    wind_direction = float(row["wind_direction_deg"]) % 360
    wave_direction = float(row.get("primary_direction_deg", float("nan")))
    tide_height = float(row.get("tide_height_m", float("nan")))
    tide_state = str(row.get("tide_state", "unavailable"))
    next_tide_type = row.get("next_tide_type")
    next_tide_time = row.get("next_tide_time_utc")
    next_tide_height = row.get("next_tide_height_m")

    if hs < 0.5:
        mood, size_band, height_feel = "quiet", "tiny", "sleepy and delicate, with scarce push"
    elif hs <= 1.5:
        mood, size_band, height_feel = "playful", "small", "small and playful, rewarding timing more than force"
    elif hs < 2.0:
        mood, size_band, height_feel = "lively", "medium", "approachable but energetic enough for committed surfing"
    elif hs <= 3.0:
        mood, size_band, height_feel = "powerful", "big", "powerful and demanding, with a serious pulse"
    else:
        mood, size_band, height_feel = "imposing", "very_big", "heavy and imposing, with consequence in every decision"

    if period < 9:
        period_band, period_feel = "short", "short-period and restless, with closely packed energy"
    elif period < 12:
        period_band, period_feel = "medium", "moderately organised but active and peaky"
    elif period < 14:
        period_band, period_feel = "long", "cleanly pulsing, with readable lines and breathing room"
    else:
        period_band, period_feel = "long", "deep and deliberate, carrying long-period energy beneath the surface"

    favourable = any(_in_sector(wind_direction, a, b) for a, b in SPOT_RULES[location]["sectors"])
    if wind_speed < 2.0:
        wind_quality, wind_strength, wind_feel = "light", "light", "open-faced and barely textured by wind"
    elif favourable:
        wind_quality, wind_strength, wind_feel = "clean", "light" if wind_speed < 5 else "moderate" if wind_speed < 8 else "fresh/strong", "cleaner and more organised under the local wind"
    else:
        wind_quality, wind_strength, wind_feel = "messy", "light" if wind_speed < 5 else "moderate" if wind_speed < 8 else "fresh/strong", "messy and broken up by the local wind"

    tide_feelings = {
        "rising": "gathering and filling on a rising tide",
        "falling": "releasing and opening as the tide falls",
        "high": "full and briefly suspended near high water",
        "low": "drawn back and exposed near low water",
        "unavailable": "without a current tidal reading",
    }
    next_time_local = None
    if next_tide_time is not None and not pd.isna(next_tide_time):
        next_time_local = pd.Timestamp(next_tide_time).tz_convert("Australia/Sydney").isoformat()

    return {
        "location": location, "valid_time_utc": str(pd.Timestamp(row["valid_time_utc"])),
        "wave_height_m": round(hs, 2), "primary_period_s": round(period, 1),
        "wave_direction": None if pd.isna(wave_direction) else compass_direction(wave_direction),
        "wind_speed_m_s": round(wind_speed, 1), "wind_direction": compass_direction(wind_direction),
        "wind_direction_deg": round(wind_direction), "wind_quality": wind_quality,
        "wind_strength": wind_strength,
        "clean_wind_rule": SPOT_RULES[location]["label"], "ocean_mood": mood,
        "size_band": size_band, "period_band": period_band,
        "trend": str(row.get("trend", "unknown")),
        "height_feel": height_feel, "period_feel": period_feel,
        "tide_height_m": None if pd.isna(tide_height) else round(tide_height, 2),
        "tide_state": tide_state, "tide_feeling": tide_feelings.get(tide_state, tide_feelings["unavailable"]),
        "next_tide_type": next_tide_type, "next_tide_time_local": next_time_local,
        "next_tide_height_m": None if next_tide_height is None or pd.isna(next_tide_height) else round(float(next_tide_height), 2),
        "tide_station": row.get("tide_station"),
        "ocean_feeling": f"{height_feel}; {period_feel}; {wind_feel}; {tide_feelings.get(tide_state, tide_feelings['unavailable'])}",
    }


def add_forecast_trends(forecast):
    """Infer a cautious 6-hour swell trend from consecutive model guidance."""
    data = forecast.copy()
    data["valid_time_utc"] = pd.to_datetime(data["valid_time_utc"], utc=True)
    data = data.sort_values(["location", "valid_time_utc"])
    future_height = data.groupby("location")["wave_height_m"].shift(-2)
    change = future_height - data["wave_height_m"]
    data["trend"] = "steady"
    data.loc[change > 0.12, "trend"] = "rising"
    data.loc[change < -0.12, "trend"] = "easing"
    data.loc[future_height.isna(), "trend"] = "unknown"
    return data


def current_rows(forecast):
    """Return the forecast row closest to now for each location."""
    data = add_forecast_trends(forecast)
    data["distance_from_now"] = (data["valid_time_utc"] - pd.Timestamp.now(tz="UTC")).abs()
    return data.loc[data.groupby("location")["distance_from_now"].idxmin()].drop(columns="distance_from_now")


def _surf_score(row):
    """Score a morning forecast for useful swell energy and surface quality."""
    conditions = interpret_conditions(row)
    height = conditions["wave_height_m"]
    period = conditions["primary_period_s"]
    wind_score = {"clean": 5.0, "light": 4.5, "messy": max(-1.5, 1.5 - conditions["wind_speed_m_s"] / 2)}[
        conditions["wind_quality"]
    ]
    height_score = max(0.0, 3.0 - abs(height - 1.4) * 1.8)
    period_score = max(0.0, min(3.0, (period - 7.0) / 2.0))
    direction = float(row.get("primary_direction_deg", 0)) % 360
    direction_score = 1.5 if any(
        _in_sector(direction, start, end) for start, end in SPOT_RULES[conditions["location"]]["swell"]
    ) else 0.0
    return wind_score + height_score + period_score + direction_score


def _supportive_elements(first, second):
    return first == second or {first, second} in ({"fire", "air"}, {"earth", "water"})


def _astrology_score(sign, sky):
    score = 0.0
    sign_element = SIGN_ELEMENTS[sign]
    moon_sign = sky.get("moon", {}).get("sign")
    if moon_sign in SIGN_ELEMENTS:
        score += 2.0 if SIGN_ELEMENTS[moon_sign] == sign_element else (
            1.0 if _supportive_elements(SIGN_ELEMENTS[moon_sign], sign_element) else -0.5
        )
    ruler = SIGN_RULERS[sign]
    placement = sky.get("planets", {}).get(ruler)
    if placement and placement.get("sign") in SIGN_ELEMENTS:
        ruler_element = SIGN_ELEMENTS[placement["sign"]]
        score += 1.5 if _supportive_elements(ruler_element, sign_element) else -0.5
        score += -0.75 if placement.get("retrograde") else 0.5
    for event in sky.get("events", []):
        if event.get("sign") == sign:
            score += 1.5
    return score


def _future_cosmic_context(cosmic, date, sign):
    sky = cosmic.get("future", {}).get(date, {})
    moon = sky.get("moon", cosmic["moon"])
    ruler = SIGN_RULERS[sign]
    placement = sky.get("planets", {}).get(ruler)
    if placement:
        motion = "retrograde" if placement.get("retrograde") else "direct"
        lead = f"{ruler} moves {motion} through {placement.get('sign', 'the wider sky')}"
    else:
        events = sky.get("events", [])
        lead = events[0].get("headline") if events else "the wider sky opens a quieter window"
    return {
        "date": date, "sun": cosmic.get("sun", {}), "moon": moon,
        "signs": {sign: {"lead_event": lead, "daily_tip": None}},
    }


def generate_future_horoscopes(forecast, cosmic):
    """Choose the best combined surf/cosmic day in the next fortnight for every sign."""
    data = add_forecast_trends(forecast)
    local = data["valid_time_utc"].dt.tz_convert(ZoneInfo("Australia/Sydney"))
    data["local_date"] = local.dt.date.astype(str)
    data["local_hour"] = local.dt.hour
    today = pd.Timestamp.now(tz="Australia/Sydney").date().isoformat()
    candidates = data[(data["local_date"] > today) & data["local_hour"].between(5, 12)].copy()
    if candidates.empty:
        candidates = data[data["local_date"] > today].copy()
    candidates["surf_score"] = candidates.apply(_surf_score, axis=1)
    results = {}
    for location, spot_rows in candidates.groupby("location"):
        daily = spot_rows.loc[spot_rows.groupby("local_date")["surf_score"].idxmax()]
        sign_results = {}
        for sign in STAR_SIGNS:
            ranked = daily.copy()
            ranked["combined_score"] = ranked.apply(
                lambda row: row["surf_score"] + _astrology_score(
                    sign, cosmic.get("future", {}).get(row["local_date"], {})
                ), axis=1,
            )
            clean = ranked[ranked.apply(lambda row: interpret_conditions(row)["wind_quality"] != "messy", axis=1)]
            chosen = (clean if not clean.empty else ranked).sort_values("combined_score", ascending=False).iloc[0]
            conditions = interpret_conditions(chosen)
            date = chosen["local_date"]
            future_cosmic = _future_cosmic_context(cosmic, date, sign)
            horoscope = next(
                item for item in generate_spot_horoscopes(conditions, future_cosmic).horoscopes
                if item.sign == sign
            )
            horoscope.reading = horoscope.reading.replace(" today", " on this coming day")
            sign_results[sign] = {
                "date": date, "conditions": conditions, "horoscope": asdict(horoscope),
                "score": round(float(chosen["combined_score"]), 2),
            }
        results[location] = sign_results
    return results


def _rng(conditions, sign, cosmic_date=""):
    day = pd.Timestamp(conditions["valid_time_utc"]).strftime("%Y-%m-%d")
    digest = hashlib.sha256(f"{day}|{conditions['location']}|{sign}|{cosmic_date}|v2".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _cosmic_line(sign, cosmic, conditions):
    moon = cosmic["moon"]
    illumination = moon.get("illumination")
    if isinstance(illumination, (int, float)) and illumination > 1:
        illumination /= 100
    lit = f", {illumination:.0%} illuminated" if isinstance(illumination, (int, float)) else ""
    sign_data = cosmic.get("signs", {}).get(sign, {})
    lead = sign_data.get("lead_event")
    if lead:
        lead = re.sub(r"\s*\[([^]]+)\]", r", currently \1", lead).rstrip(".").lower()
        lead_text = f" Through {sign}, the particular current is {lead}."
    else:
        lead_text = f" Through {sign}, that wider sky meets your own elemental rhythm."
    tide_bridge = {
        "rising": "At the shoreline, the rising water gives the Moon's physical rhythm a gathering form.",
        "falling": "At the shoreline, the falling water gives the Moon's physical rhythm a releasing form.",
        "high": "At the shoreline, high water holds the Moon's physical rhythm at a turning point.",
        "low": "At the shoreline, low water reveals the Moon's physical rhythm at a turning point.",
    }.get(conditions.get("tide_state"), "")
    return (f"A {moon['phase_name']} Moon in {moon['sign']}{lit} sets the inner tide, "
            f"while the Sun moves through {cosmic['sun'].get('sign', 'the current season')}."
            f"{lead_text} {tide_bridge}".strip())


def generate_spot_horoscopes(conditions, cosmic):
    """Create all 12 readings from local surf logic and current astrology."""
    summary = (f"Wave height {conditions['wave_height_m']:.1f} m with a "
               f"{conditions['primary_period_s']:.0f}-second primary rhythm. "
               f"The {conditions['wind_direction']} wind leaves the surface "
               f"{conditions['wind_quality']}. Overall, the ocean feels "
               f"{conditions['ocean_feeling']}.")
    if conditions.get("next_tide_time_local"):
        next_time = pd.Timestamp(conditions["next_tide_time_local"]).strftime("%I:%M %p").lstrip("0")
        summary += (f" The tide is {conditions['tide_state']} at "
                    f"{conditions['tide_height_m']:.1f} m, heading toward "
                    f"{conditions['next_tide_type']} water around {next_time.lower()}.")
    values = {"location": conditions["location"], "mood": conditions["ocean_mood"],
              "hs": conditions["wave_height_m"], "period": conditions["primary_period_s"],
              "height_feel": conditions["height_feel"], "energy": conditions["period_feel"],
              "wind_dir": conditions["wind_direction"],
              "wind_speed": conditions["wind_speed_m_s"],
              "tide_height": conditions.get("tide_height_m")}
    reports = []
    used_style_sentences = set()
    for sign in STAR_SIGNS:
        rng = _rng(conditions, sign, cosmic.get("date", ""))
        gift, lesson, actions = SIGN_VOICES[sign]
        cosmic_alignment = _cosmic_line(sign, cosmic, conditions)
        opening = rng.choice(LOCATION_OPENINGS[conditions["location"]]).format(**values)
        height_line = rng.choice(EAST_COAST_HEIGHT_LINES[conditions["size_band"]]).format(**values)
        period_line = rng.choice(EAST_COAST_PERIOD_LINES[conditions["period_band"]]).format(**values)
        wind_line = rng.choice(WIND_LINES[conditions["wind_quality"]]).format(**values)
        tide_line = rng.choice(TIDE_LINES.get(conditions["tide_state"], TIDE_LINES["unavailable"])).format(**values)
        style_line = retrieve_style_line(conditions, sign, "surf", used_style_sentences)
        structures = (
            (opening, height_line, period_line, wind_line, tide_line, style_line),
            (style_line, opening, wind_line, tide_line, height_line, period_line),
            (opening, wind_line, height_line, tide_line, style_line, period_line),
            (opening, period_line, style_line, wind_line, tide_line, height_line),
        )
        surf_lines = [line for line in rng.choice(structures) if line]
        reading = " ".join((*surf_lines, f"Your {gift} is useful here. {lesson}"))
        subject = rng.choice(
            HEADLINE_SUBJECTS[conditions["location"]][conditions["wind_quality"]]
        ).format(mood=conditions["ocean_mood"].title())
        headline = HEADLINE_PATTERNS[sign].format(subject=subject)
        api_tip = cosmic.get("signs", {}).get(sign, {}).get("daily_tip")
        intention = api_tip or (rng.choice(actions).capitalize() + ".")
        reports.append(Horoscope(sign, headline, reading, intention, cosmic_alignment))
    return SpotHoroscopes(conditions["location"], summary, reports)


def _as_markdown(report, conditions):
    lines = [f"# {report.location} surf horoscopes", "",
             f"*Conditions valid {conditions['valid_time_utc']}*", "", report.conditions_summary, ""]
    for item in report.horoscopes:
        lines += [f"## {item.sign} — {item.headline}", "", f"*{item.cosmic_alignment}*", "",
                  item.reading, "",
                  f"**Surf intention:** {item.surf_intention}", ""]
    return "\n".join(lines)


def generate_all_horoscopes(forecast, output_dir="output", cosmic_context=None):
    """Generate both reports, falling back safely when the astrology API is unavailable."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = {}
    cosmic_context = cosmic_context or fetch_cosmic_context()
    for _, row in current_rows(forecast).iterrows():
        conditions = interpret_conditions(row)
        report = generate_spot_horoscopes(conditions, cosmic_context)
        reports[report.location] = report
        slug = report.location.lower().replace(" beach", "").replace(" ", "_")
        (output_dir / f"surf_horoscopes_{slug}.json").write_text(report.model_dump_json(), encoding="utf-8")
        (output_dir / f"surf_horoscopes_{slug}.md").write_text(_as_markdown(report, conditions), encoding="utf-8")
    metadata = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "generator": "surf templates + CosmyDay daily astrology v2",
                "astrology_source": cosmic_context.get("source"),
                "tide_source": "Bureau of Meteorology high/low predictions; display heights interpolated",
                "cosmic_context": cosmic_context, "locations": list(reports)}
    (output_dir / "surf_horoscope_run.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return reports
