from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .models import CharacterEntry, CharacterMatch


BUILTIN_ENTRIES = (
    CharacterEntry("StarIntel-chan", ("starintel-chan", "starintel chan"), "StarIntel", "starintel"),
    CharacterEntry("Mara", ("mara",), "StarIntel", "starintel"),
    CharacterEntry("Zara", ("zara",), "StarIntel", "starintel"),
    CharacterEntry("Rick Sanchez", ("rick sanchez",), "Rick and Morty", "show", ("rick",)),
    CharacterEntry("Morty Smith", ("morty smith", "morty"), "Rick and Morty", "show"),
    CharacterEntry("Summer Smith", ("summer smith",), "Rick and Morty", "show", ("summer",)),
    CharacterEntry("Beth Smith", ("beth smith",), "Rick and Morty", "show", ("beth",)),
    CharacterEntry("Jerry Smith", ("jerry smith",), "Rick and Morty", "show", ("jerry",)),
    CharacterEntry("Mr. Meeseeks", ("mr meeseeks", "meeseeks"), "Rick and Morty", "show"),
    CharacterEntry("Birdperson", ("birdperson",), "Rick and Morty", "show"),
    CharacterEntry("Squanchy", ("squanchy",), "Rick and Morty", "show"),
    CharacterEntry("Evil Morty", ("evil morty",), "Rick and Morty", "show"),
    CharacterEntry("Rick Prime", ("rick prime",), "Rick and Morty", "show"),
    CharacterEntry("Homer Simpson", ("homer simpson",), "The Simpsons", "show", ("homer",)),
    CharacterEntry("Marge Simpson", ("marge simpson", "marge"), "The Simpsons", "show"),
    CharacterEntry("Bart Simpson", ("bart simpson", "bart"), "The Simpsons", "show"),
    CharacterEntry("Lisa Simpson", ("lisa simpson",), "The Simpsons", "show", ("lisa",)),
    CharacterEntry("Philip J. Fry", ("philip j fry", "fry"), "Futurama", "show"),
    CharacterEntry("Turanga Leela", ("turanga leela", "leela"), "Futurama", "show"),
    CharacterEntry("Bender", ("bender rodriguez", "bender"), "Futurama", "show"),
    CharacterEntry("Peter Griffin", ("peter griffin",), "Family Guy", "show", ("peter",)),
    CharacterEntry("Stewie Griffin", ("stewie griffin", "stewie"), "Family Guy", "show"),
    CharacterEntry("Brian Griffin", ("brian griffin",), "Family Guy", "show", ("brian",)),
    CharacterEntry("Stan Marsh", ("stan marsh",), "South Park", "show", ("stan",)),
    CharacterEntry("Kyle Broflovski", ("kyle broflovski",), "South Park", "show", ("kyle",)),
    CharacterEntry("Eric Cartman", ("eric cartman", "cartman"), "South Park", "show"),
    CharacterEntry("Kenny McCormick", ("kenny mccormick",), "South Park", "show", ("kenny",)),
    CharacterEntry("SpongeBob SquarePants", ("spongebob squarepants", "spongebob"), "SpongeBob SquarePants", "show"),
    CharacterEntry("Patrick Star", ("patrick star",), "SpongeBob SquarePants", "show"),
    CharacterEntry("Squidward Tentacles", ("squidward tentacles", "squidward"), "SpongeBob SquarePants", "show"),
    CharacterEntry("Finn the Human", ("finn the human",), "Adventure Time", "show", ("finn",)),
    CharacterEntry("Jake the Dog", ("jake the dog",), "Adventure Time", "show", ("jake",)),
    CharacterEntry("Princess Bubblegum", ("princess bubblegum", "bubblegum"), "Adventure Time", "show"),
    CharacterEntry("Marceline", ("marceline",), "Adventure Time", "show"),
    CharacterEntry("Dipper Pines", ("dipper pines", "dipper"), "Gravity Falls", "show"),
    CharacterEntry("Mabel Pines", ("mabel pines", "mabel"), "Gravity Falls", "show"),
    CharacterEntry("Grunkle Stan", ("grunkle stan",), "Gravity Falls", "show"),
    CharacterEntry("BoJack Horseman", ("bojack horseman", "bojack"), "BoJack Horseman", "show"),
    CharacterEntry("Sterling Archer", ("sterling archer",), "Archer", "show", ("archer",)),
)


def _norm(text: str) -> str:
    text = text.casefold().replace("’", "'")
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return " ".join(text.split())


def _contains(text: str, phrase: str) -> bool:
    return re.search(rf"(?:^|\s){re.escape(_norm(phrase))}(?:$|\s)", text) is not None


def _entry_from_obj(obj: dict[str, object]) -> CharacterEntry:
    aliases = tuple(str(x) for x in obj.get("aliases", []) or [])
    ambiguous = tuple(str(x) for x in obj.get("ambiguous_aliases", []) or [])
    return CharacterEntry(
        canonical=str(obj["canonical"]),
        aliases=aliases,
        universe=str(obj.get("universe", "unknown")),
        source=str(obj.get("source", "show")),
        ambiguous_aliases=ambiguous,
    )


class CharacterCatalog:
    def __init__(self, entries: tuple[CharacterEntry, ...] = BUILTIN_ENTRIES):
        self.entries = entries

    @classmethod
    def from_environment(cls, root: Path | None = None) -> "CharacterCatalog":
        entries = list(BUILTIN_ENTRIES)
        paths: list[Path] = []
        if root:
            default = root / ".cache" / "fictional-characters.jsonl"
            if default.exists():
                paths.append(default)
        configured = os.getenv("STARINTEL_CHARACTER_CATALOGS", "")
        paths.extend(Path(p) for p in configured.split(os.pathsep) if p)
        for path in paths:
            entries.extend(_load_catalog(path))
        return cls(tuple(entries))

    def match(self, text: str, explicit: tuple[str, ...] = ()) -> tuple[CharacterMatch, ...]:
        haystack = _norm(" ".join((text, *explicit)))
        found: dict[tuple[str, str], CharacterMatch] = {}
        universe_cues = {_norm(entry.universe) for entry in self.entries if entry.universe}
        active_universes = {cue for cue in universe_cues if cue and _contains(haystack, cue)}

        for entry in self.entries:
            aliases = (entry.canonical, *entry.aliases)
            matched = next((alias for alias in aliases if _contains(haystack, alias)), None)
            if not matched and _norm(entry.universe) in active_universes:
                matched = next((alias for alias in entry.ambiguous_aliases if _contains(haystack, alias)), None)
            if not matched:
                continue
            key = (_norm(entry.canonical), _norm(entry.universe))
            found[key] = CharacterMatch(entry.canonical, entry.universe, entry.source, matched)
        return tuple(found.values())


def _load_catalog(path: Path) -> list[CharacterEntry]:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix == ".json":
        raw = json.loads(path.read_text())
        return [_entry_from_obj(obj) for obj in raw]
    entries: list[CharacterEntry] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        entries.append(_entry_from_obj(json.loads(line)))
    return entries
