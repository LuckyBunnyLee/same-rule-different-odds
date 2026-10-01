"""Competition / event configuration shared by all RT data scripts.

WA URL slugs and competition ids were discovered on 2026-09-28 by following
worldathletics.org redirects (e.g. /competitions/world-athletics-championships/
budapest23/... -> ...-budapest-2023-7138987/...). ``event_id`` is the WA
competition id used in media.aws.iaaf.org document paths.
"""

WA_BASE = "https://worldathletics.org"
WA_DOCS = "https://media.aws.iaaf.org/competitiondocuments"

# comp code, year used in race_id, WA url group + slug, WA competition id,
# venue IANA time zone (WA unitDateTime values are *local* wall-clock times
# carrying a spurious 'Z'; verified against official PDF start times), and
# the official timing provider.
COMPETITIONS = [
    dict(comp="WCH", year=2025, group="world-athletics-championships",
         slug="world-athletics-championships-tokyo-2025-7190593", event_id=7190593,
         venue="Tokyo", tz="Asia/Tokyo", timing="Seiko", priority=1),
    dict(comp="WCH", year=2023, group="world-athletics-championships",
         slug="world-athletics-championships-budapest-2023-7138987", event_id=7138987,
         venue="Budapest", tz="Europe/Budapest", timing="Seiko", priority=1),
    dict(comp="WCH", year=2022, group="world-athletics-championships",
         slug="world-athletics-championships-oregon-2022-7137279", event_id=7137279,
         venue="Eugene", tz="America/Los_Angeles", timing="Seiko", priority=2),
    dict(comp="WCH", year=2019, group="world-athletics-championships",
         slug="iaaf-world-athletics-championships-doha-2019-7125365", event_id=7125365,
         venue="Doha", tz="Asia/Qatar", timing="Seiko", priority=2),
    dict(comp="OG", year=2024, group="olympic-games",
         slug="the-xxxiii-olympic-games-7153115", event_id=7153115,
         venue="Paris", tz="Europe/Paris", timing="Omega", priority=2),
    # earlier Worlds (extension; WA hosts no waveforms for these)
    dict(comp="WCH", year=2017, group="world-athletics-championships",
         slug="iaaf-world-championships-london-2017-7093740", event_id=7093740,
         venue="London", tz="Europe/London", timing="Seiko", priority=3),
    dict(comp="WCH", year=2015, group="world-athletics-championships",
         slug="15th-iaaf-world-championships-7078726", event_id=7078726,
         venue="Beijing", tz="Asia/Shanghai", timing="Seiko", priority=3),
    # World Athletics Indoor Championships (extension: 60m / 60mH, Seiko waveforms)
    dict(comp="WIC", year=2025, group="world-athletics-indoor-championships",
         slug="world-athletics-indoor-championships-7136586", event_id=7136586,
         venue="Nanjing", tz="Asia/Shanghai", timing="Seiko", priority=3),
    dict(comp="WIC", year=2024, group="world-athletics-indoor-championships",
         slug="world-athletics-indoor-championships-7180312", event_id=7180312,
         venue="Glasgow", tz="Europe/London", timing="Seiko", priority=3),
    # Tokyo 2020 Olympic Games, held in 2021; race_id keeps the official 2020.
    dict(comp="OG", year=2020, group="olympic-games",
         slug="the-xxxii-olympic-games-athletics-7132391", event_id=7132391,
         venue="Tokyo", tz="Asia/Tokyo", timing="Omega", priority=2),
]

# (event code, sex code, WA sex slug, WA discipline slug)
EVENTS = [
    ("100m", "M", "men", "100-metres"),
    ("100m", "W", "women", "100-metres"),
    ("110mH", "M", "men", "110-metres-hurdles"),
    ("100mH", "W", "women", "100-metres-hurdles"),
]
EVENTS_EXT = [
    ("200m", "M", "men", "200-metres"),
    ("200m", "W", "women", "200-metres"),
]
EVENTS_INDOOR = [
    ("60m", "M", "men", "60-metres"),
    ("60m", "W", "women", "60-metres"),
    ("60mH", "M", "men", "60-metres-hurdles"),
    ("60mH", "W", "women", "60-metres-hurdles"),
]
ALL_EVENTS = EVENTS + EVENTS_EXT + EVENTS_INDOOR

# WA phase name -> BRIEF round code. RP (repechage, Paris 2024) and R2
# (quarter-final / second round, older championships) extend the BRIEF's
# PR/R1/SF/F set because those rounds exist in the source data.
ROUND_CODES = {
    "preliminary round": "PR",
    "round 1": "R1",
    "heats": "R1",
    "repechage round": "RP",
    "repechage": "RP",
    "round 2": "R2",
    "quarter-finals": "R2",
    "quarterfinals": "R2",
    "semi-finals": "SF",
    "semi-final": "SF",
    "final": "F",
}
ROUND_ORDER = {"PR": 0, "R1": 1, "RP": 2, "R2": 3, "SF": 4, "F": 5}


def round_code(phase_name: str) -> str:
    key = phase_name.strip().lower()
    if key not in ROUND_CODES:
        raise KeyError(f"unknown WA phase name: {phase_name!r}")
    return ROUND_CODES[key]


def comp_key(c: dict) -> str:
    return f"{c['comp']}{c['year']}"


def race_id(comp: str, year: int, event: str, sex: str, rnd: str, heat: int) -> str:
    return f"{comp}{year}-{event}-{sex}-{rnd}-H{int(heat)}"


def results_url(c: dict, sex_slug: str, disc_slug: str, phase_slug: str) -> str:
    return (f"{WA_BASE}/competitions/{c['group']}/{c['slug']}/results/"
            f"{sex_slug}/{disc_slug}/{phase_slug}/result")
