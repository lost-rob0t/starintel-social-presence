:- module(media_gen_characters,
          [ media_gen_character_matches/3,
            character_entry/5
          ]).

:- use_module(library(lists)).
:- use_module(library(pairs)).

character_entry("StarIntel-chan", "StarIntel", starintel,
                ["starintel-chan", "starintel chan"], []).
character_entry("Mara", "StarIntel", starintel, ["mara"], []).
character_entry("Zara", "StarIntel", starintel, ["zara"], []).
character_entry("Rick Sanchez", "Rick and Morty", show,
                ["rick sanchez"], ["rick"]).
character_entry("Morty Smith", "Rick and Morty", show,
                ["morty smith", "morty"], []).
character_entry("Summer Smith", "Rick and Morty", show,
                ["summer smith"], ["summer"]).
character_entry("Beth Smith", "Rick and Morty", show,
                ["beth smith"], ["beth"]).
character_entry("Jerry Smith", "Rick and Morty", show,
                ["jerry smith"], ["jerry"]).
character_entry("Mr. Meeseeks", "Rick and Morty", show,
                ["mr meeseeks", "meeseeks"], []).
character_entry("Birdperson", "Rick and Morty", show,
                ["birdperson"], []).
character_entry("Evil Morty", "Rick and Morty", show,
                ["evil morty"], []).
character_entry("Rick Prime", "Rick and Morty", show,
                ["rick prime"], []).
character_entry("Homer Simpson", "The Simpsons", show,
                ["homer simpson"], ["homer"]).
character_entry("Marge Simpson", "The Simpsons", show,
                ["marge simpson", "marge"], []).
character_entry("Bart Simpson", "The Simpsons", show,
                ["bart simpson", "bart"], []).
character_entry("Lisa Simpson", "The Simpsons", show,
                ["lisa simpson"], ["lisa"]).
character_entry("Philip J. Fry", "Futurama", show,
                ["philip j fry", "fry"], []).
character_entry("Turanga Leela", "Futurama", show,
                ["turanga leela", "leela"], []).
character_entry("Bender", "Futurama", show,
                ["bender rodriguez", "bender"], []).
character_entry("Peter Griffin", "Family Guy", show,
                ["peter griffin"], ["peter"]).
character_entry("Stewie Griffin", "Family Guy", show,
                ["stewie griffin", "stewie"], []).
character_entry("Stan Marsh", "South Park", show,
                ["stan marsh"], ["stan"]).
character_entry("Eric Cartman", "South Park", show,
                ["eric cartman", "cartman"], []).
character_entry("Finn the Human", "Adventure Time", show,
                ["finn the human"], ["finn"]).
character_entry("Jake the Dog", "Adventure Time", show,
                ["jake the dog"], ["jake"]).
character_entry("Dipper Pines", "Gravity Falls", show,
                ["dipper pines", "dipper"], []).
character_entry("Mabel Pines", "Gravity Falls", show,
                ["mabel pines", "mabel"], []).
character_entry("BoJack Horseman", "BoJack Horseman", show,
                ["bojack horseman", "bojack"], []).

media_gen_character_matches(Description, Explicit0, Matches) :-
    normalize_explicit(Explicit0, Explicit),
    text_string(Description, DescriptionString),
    append([DescriptionString], Explicit, Texts),
    atomics_to_string(Texts, " ", Combined),
    normalize_text(Combined, Haystack),
    findall(Match,
            direct_character_match(Haystack, Match),
            Direct0),
    sort_matches(Direct0, Direct),
    active_universes(Haystack, Direct, Universes),
    findall(Match,
            ambiguous_character_match(Haystack, Universes, Match),
            Ambiguous0),
    append(Direct, Ambiguous0, All),
    sort_matches(All, Matches).

normalize_explicit(Explicit, Strings) :-
    (   var(Explicit)
    ->  Strings = []
    ;   is_list(Explicit)
    ->  maplist(text_string, Explicit, Strings)
    ;   text_string(Explicit, One),
        Strings = [One]
    ).

direct_character_match(Haystack,
                       character_match{canonical:Canonical,
                                       universe:Universe,
                                       source:Source,
                                       matched:Matched}) :-
    character_entry(Canonical, Universe, Source, Aliases, _),
    member(Alias0, [Canonical|Aliases]),
    normalize_text(Alias0, Alias),
    contains_phrase(Haystack, Alias),
    Matched = Alias0.

active_universes(Haystack, Direct, Universes) :-
    findall(Universe,
            ( character_entry(_, Universe, _, _, _),
              normalize_text(Universe, Cue),
              contains_phrase(Haystack, Cue) ),
            ExplicitUniverses),
    findall(Universe,
            ( member(Match, Direct),
              get_dict(universe, Match, Universe) ),
            MatchedUniverses),
    append(ExplicitUniverses, MatchedUniverses, Combined),
    sort(Combined, Universes).

ambiguous_character_match(Haystack, Universes,
                          character_match{canonical:Canonical,
                                          universe:Universe,
                                          source:Source,
                                          matched:Matched}) :-
    memberchk(Universe, Universes),
    character_entry(Canonical, Universe, Source, _, Ambiguous),
    member(Matched, Ambiguous),
    normalize_text(Matched, Alias),
    contains_phrase(Haystack, Alias).

sort_matches(Matches0, Matches) :-
    map_list_to_pairs(match_key, Matches0, Pairs0),
    keysort(Pairs0, Pairs),
    dedupe_match_pairs(Pairs, Matches).

match_key(Match, Key) :-
    get_dict(canonical, Match, Canonical),
    get_dict(universe, Match, Universe),
    Key = Canonical-Universe.

dedupe_match_pairs([], []).
dedupe_match_pairs([Key-Match|Pairs], [Match|Matches]) :-
    drop_key(Key, Pairs, Rest),
    dedupe_match_pairs(Rest, Matches).

drop_key(Key, [Key-_|Pairs], Rest) :-
    !,
    drop_key(Key, Pairs, Rest).
drop_key(_, Pairs, Pairs).

contains_phrase(Haystack, Phrase) :-
    Phrase \== "",
    string_concat(" ", Haystack, H0),
    string_concat(H0, " ", PaddedHaystack),
    string_concat(" ", Phrase, P0),
    string_concat(P0, " ", PaddedPhrase),
    sub_string(PaddedHaystack, _, _, _, PaddedPhrase).

normalize_text(Text0, Normalized) :-
    text_string(Text0, Text),
    string_lower(Text, Lower),
    string_codes(Lower, Codes),
    maplist(normalized_code, Codes, NormalizedCodes),
    string_codes(Spaced, NormalizedCodes),
    split_string(Spaced, " ", " ", Parts),
    atomics_to_string(Parts, " ", Normalized).

normalized_code(Code, Code) :-
    code_type(Code, alnum),
    !.
normalized_code(39, 39) :- !.
normalized_code(_, 32).

text_string(Text, String) :-
    string(Text),
    !,
    String = Text.
text_string(Text, String) :-
    atom(Text),
    !,
    atom_string(Text, String).
text_string(Text, String) :-
    number(Text),
    !,
    number_string(Text, String).
text_string(Text, _) :-
    throw(error(type_error(text, Text),
                context(media_gen_character_matches/3,
                        'character matching input must be text'))).
