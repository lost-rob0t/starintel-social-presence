:- module(media_gen_expert,
          [ media_gen_expert_ready/0,
            media_route/2,
            expert_branch/1
          ]).

:- use_module(media_gen_characters).

media_gen_expert_ready.

expert_branch('reference.starintel_native').
expert_branch('reference.fictional').
expert_branch('reference.mixed').
expert_branch('reference.generic').
expert_branch('image.openai_native').
expert_branch('image.google_fictional').
expert_branch('image.override').
expert_branch('video.google_default').
expert_branch('video.override').

media_route(Request0, Decision) :-
    normalize_request(Request0, Request),
    media_gen_character_matches(Request.description,
                                Request.explicit_characters,
                                Matches),
    reference_class(Request.description, Matches, ReferenceClass),
    reference_branch(ReferenceClass, ReferenceBranch),
    route_stage(Request,
                ReferenceClass,
                Matches,
                StageDecision),
    put_dict(_{reference_class:ReferenceClass,
               matched_characters:Matches,
               branches:[ReferenceBranch|StageDecision.branches]},
             StageDecision,
             Decision),
    !.

normalize_request(Request0, Request) :-
    (   is_dict(Request0)
    ->  true
    ;   throw(error(type_error(media_request, Request0),
                    context(media_route/2,
                            'media request must be a dict')))
    ),
    require_key(Request0, description, Description),
    require_key(Request0, kind, Kind0),
    normalize_kind(Kind0, Kind),
    optional_key(Request0, flow, auto, Flow0),
    normalize_atom(Flow0, Flow),
    optional_key(Request0, explicit_characters, [], ExplicitCharacters),
    optional_key(Request0, provider_override, none, ProviderOverride0),
    normalize_provider_override(ProviderOverride0, ProviderOverride),
    Request = media_request{description:Description,
                            kind:Kind,
                            flow:Flow,
                            explicit_characters:ExplicitCharacters,
                            provider_override:ProviderOverride}.

route_stage(Request, ReferenceClass, _, Decision) :-
    Request.kind == video,
    !,
    video_route(Request, ReferenceClass, Decision).
route_stage(Request, ReferenceClass, _, Decision) :-
    Request.kind == image,
    !,
    image_route(Request, ReferenceClass, Decision).
route_stage(Request, _, _, _) :-
    throw(error(domain_error(media_stage, Request.kind),
                context(media_route/2,
                        'route image and video stages separately'))).

image_route(Request, _, Decision) :-
    Request.provider_override \== none,
    !,
    Provider = Request.provider_override,
    provider_model(image, Provider, Model),
    Decision = route_decision{provider:Provider,
                              model:Model,
                              reason:"Explicit provider override.",
                              confidence:1.0,
                              stage:image,
                              branches:['image.override']}.
image_route(_, ReferenceClass, Decision) :-
    memberchk(ReferenceClass, [show_reference, mixed]),
    !,
    provider_model(image, google, Model),
    Decision = route_decision{provider:google,
                              model:Model,
                              reason:"Recognizable fictional reference detected; prefer the configured reference-fidelity image route.",
                              confidence:0.98,
                              stage:image,
                              branches:['image.google_fictional']}.
image_route(Request, ReferenceClass, Decision) :-
    (   ReferenceClass == starintel_only
    ;   description_mentions_starintel(Request.description)
    ),
    !,
    provider_model(image, openai, Model),
    Decision = route_decision{provider:openai,
                              model:Model,
                              reason:"StarIntel-native material detected; use the configured native image route.",
                              confidence:0.99,
                              stage:image,
                              branches:['image.openai_native']}.
image_route(_, _, Decision) :-
    provider_model(image, openai, Model),
    Decision = route_decision{provider:openai,
                              model:Model,
                              reason:"No stronger reference constraint was detected; use the configured default image route.",
                              confidence:0.80,
                              stage:image,
                              branches:['image.openai_native']}.

video_route(Request, _, Decision) :-
    Request.provider_override \== none,
    !,
    Provider = Request.provider_override,
    provider_model(video, Provider, Model),
    Decision = route_decision{provider:Provider,
                              model:Model,
                              reason:"Explicit video provider override.",
                              confidence:1.0,
                              stage:video,
                              branches:['video.override']}.
video_route(_, _, Decision) :-
    provider_model(video, google, Model),
    Decision = route_decision{provider:google,
                              model:Model,
                              reason:"Use the configured default production video route.",
                              confidence:0.99,
                              stage:video,
                              branches:['video.google_default']}.

reference_class(_, Matches, mixed) :-
    has_source(Matches, starintel),
    has_non_starintel(Matches),
    !.
reference_class(_, Matches, show_reference) :-
    has_non_starintel(Matches),
    !.
reference_class(_, Matches, starintel_only) :-
    has_source(Matches, starintel),
    !.
reference_class(Description, _, starintel_only) :-
    description_mentions_starintel(Description),
    !.
reference_class(_, _, generic).

reference_branch(starintel_only, 'reference.starintel_native').
reference_branch(show_reference, 'reference.fictional').
reference_branch(mixed, 'reference.mixed').
reference_branch(generic, 'reference.generic').

has_source(Matches, Source) :-
    member(Match, Matches),
    get_dict(source, Match, Source),
    !.

has_non_starintel(Matches) :-
    member(Match, Matches),
    get_dict(source, Match, Source),
    Source \== starintel,
    !.

description_mentions_starintel(Description) :-
    text_string(Description, String),
    string_lower(String, Lower),
    sub_string(Lower, _, _, _, "starintel").

provider_model(image, openai, Model) :-
    !,
    configured_model('STARINTEL_IMAGE_OPENAI_MODEL', "gpt-image-2", Model).
provider_model(image, google, Model) :-
    !,
    configured_model('STARINTEL_IMAGE_GOOGLE_MODEL', "gemini-3-pro-image", Model).
provider_model(video, google, Model) :-
    !,
    configured_model('STARINTEL_VIDEO_GOOGLE_MODEL', "veo-3.1-generate-preview", Model).
provider_model(video, openai, Model) :-
    !,
    configured_model('STARINTEL_VIDEO_OPENAI_MODEL', "sora-2-pro", Model).
provider_model(Stage, Provider, _) :-
    throw(error(domain_error(media_provider, Stage-Provider),
                context(media_route/2,
                        'unsupported configured media provider'))).

configured_model(Name, Default, Model) :-
    (   getenv(Name, Value), Value \== ''
    ->  text_string(Value, Model)
    ;   Model = Default
    ).

normalize_kind(Kind0, Kind) :-
    normalize_atom(Kind0, Kind),
    memberchk(Kind, [image, video, both]),
    !.
normalize_kind(Kind, _) :-
    throw(error(domain_error(media_kind, Kind),
                context(media_route/2,
                        'media kind must be image, video, or both'))).

normalize_provider_override(none, none) :- !.
normalize_provider_override(null, none) :- !.
normalize_provider_override('', none) :- !.
normalize_provider_override(Value, Provider) :-
    normalize_atom(Value, Provider),
    memberchk(Provider, [openai, google]),
    !.
normalize_provider_override(Value, _) :-
    throw(error(domain_error(media_provider_override, Value),
                context(media_route/2,
                        'provider override must be openai or google'))).

normalize_atom(Value, Atom) :-
    atom(Value),
    !,
    Atom = Value.
normalize_atom(Value, Atom) :-
    string(Value),
    !,
    atom_string(Atom, Value).
normalize_atom(Value, _) :-
    throw(error(type_error(atom_or_string, Value),
                context(media_route/2,
                        'expected atom or string'))).

text_string(Value, String) :-
    string(Value),
    !,
    String = Value.
text_string(Value, String) :-
    atom(Value),
    !,
    atom_string(Value, String).
text_string(Value, _) :-
    throw(error(type_error(text, Value),
                context(media_route/2,
                        'description must be text'))).

require_key(Dict, Key, Value) :-
    (   get_dict(Key, Dict, Value)
    ->  true
    ;   throw(error(existence_error(media_request_key, Key),
                    context(media_route/2,
                            'media request is missing a required key')))
    ).

optional_key(Dict, Key, Default, Value) :-
    (   get_dict(Key, Dict, Found)
    ->  Value = Found
    ;   Value = Default
    ).
