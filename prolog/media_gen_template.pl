:- module(media_gen_template,
          [ media_org_template/3
          ]).

:- use_module(media_gen_expert).

media_org_template(Title0, Request0, Text) :-
    text_string(Title0, Title),
    normalize_template_request(Request0, Request),
    template_routes(Request, ImageRoute, VideoRoute),
    route_summary(ImageRoute, ImageSummary),
    route_summary(VideoRoute, VideoSummary),
    format(string(Text),
           "#+title: ~s\n#+description: media-gen production plan\n\n* Intent\n\n- Description :: ~s\n- Flow :: ~w\n- Requested kind :: ~w\n\n* Characters and continuity\n\n- Resolve canonical identities before generation.\n- Prefer approved visual assets over generated prose descriptions.\n- Facial expression :: define the expression at each story beat.\n- Fumble :: preserve the intended misunderstanding/correction/fumble progression when the concept requires it.\n\n* Provider plan\n\n- Image :: ~s\n- Video :: ~s\n\n* Input assets\n\n- Pass actual approved/reference assets to providers when supported.\n- Keep assets.json authoritative for project asset state.\n\n* Human approval gate\n\n- [ ] Character identity is correct.\n- [ ] Facial expression progression is correct.\n- [ ] Composition and text are readable.\n- [ ] StarIntel technical claims are accurate.\n- [ ] Approved keyframe is safe to continue into video.\n\n* Async continuation\n\nAfter approval, resume the durable graph rather than blocking an Emacs or scheduler worker while a human reviews the still.\n",
           [Title,
            Request.description,
            Request.flow,
            Request.kind,
            ImageSummary,
            VideoSummary]).

normalize_template_request(Request0, Request) :-
    (   is_dict(Request0)
    ->  true
    ;   throw(error(type_error(media_request, Request0),
                    context(media_org_template/3,
                            'template request must be a dict')))
    ),
    require_key(Request0, description, Description),
    optional_key(Request0, kind, both, Kind0),
    normalize_atom(Kind0, Kind),
    optional_key(Request0, flow, auto, Flow0),
    normalize_atom(Flow0, Flow),
    optional_key(Request0, explicit_characters, [], ExplicitCharacters),
    Request = media_template_request{description:Description,
                                     kind:Kind,
                                     flow:Flow,
                                     explicit_characters:ExplicitCharacters}.

template_routes(Request, ImageRoute, VideoRoute) :-
    Base = _{description:Request.description,
             flow:Request.flow,
             explicit_characters:Request.explicit_characters},
    put_dict(kind, Base, image, ImageRequest),
    put_dict(kind, Base, video, VideoRequest),
    media_route(ImageRequest, ImageRoute),
    media_route(VideoRequest, VideoRoute).

route_summary(Route, Summary) :-
    format(string(Summary),
           "~w / ~s (~w)",
           [Route.provider, Route.model, Route.reference_class]).

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
                context(media_org_template/3,
                        'title must be text'))).

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
                context(media_org_template/3,
                        'expected atom or string'))).

require_key(Dict, Key, Value) :-
    (   get_dict(Key, Dict, Value)
    ->  true
    ;   throw(error(existence_error(media_request_key, Key),
                    context(media_org_template/3,
                            'template request is missing description')))
    ).

optional_key(Dict, Key, Default, Value) :-
    (   get_dict(Key, Dict, Found)
    ->  Value = Found
    ;   Value = Default
    ).
