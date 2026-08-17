:- module(media,
          [ media_provider/2,
            media_generate_async/2,
            media_generate_execute/2,
            image_generate_async/2,
            image_generate_execute/2,
            video_generate_async/2,
            video_generate_execute/2,
            voice_generate_async/2,
            voice_generate_execute/2
          ]).

/** <module> Provider-neutral media generation boundary

This module deliberately contains no StarIntel, Emacs, social-platform, or
project-layout assumptions.  It is intended to remain portable enough to move
into prolog-rlm later.

The public generation path is canonical async-first: execute predicate ->
rlm_async Future.  Sync callers may await the returned Future themselves.
*/

media_provider(fake, image).
media_provider(fake, video).
media_provider(fake, voice).

media_generate_async(Request0, Future) :-
    normalize_request(Request0, Request),
    ensure_async_runtime,
    metadata(Request, Metadata),
    rlm_async:rlm_async_submit(media:media_generate_execute(Request),
                               Metadata,
                               Future).

media_generate_execute(Request0, Outcome) :-
    catch(( normalize_request(Request0, Request),
            execute_provider(Request, Outcome) ),
          Exception,
          provider_exception(Exception, Outcome)).

image_generate_async(Request0, Future) :-
    request_with_kind(image, Request0, Request),
    media_generate_async(Request, Future).

image_generate_execute(Request0, Outcome) :-
    request_with_kind(image, Request0, Request),
    media_generate_execute(Request, Outcome).

video_generate_async(Request0, Future) :-
    request_with_kind(video, Request0, Request),
    media_generate_async(Request, Future).

video_generate_execute(Request0, Outcome) :-
    request_with_kind(video, Request0, Request),
    media_generate_execute(Request, Outcome).

voice_generate_async(Request0, Future) :-
    request_with_kind(voice, Request0, Request),
    media_generate_async(Request, Future).

voice_generate_execute(Request0, Outcome) :-
    request_with_kind(voice, Request0, Request),
    media_generate_execute(Request, Outcome).

execute_provider(Request, Outcome) :-
    (   media_provider(Request.provider, Request.kind)
    ->  provider_execute(Request.provider, Request, Outcome)
    ;   Outcome = error(media_error{kind:unsupported_provider,
                                    provider:Request.provider,
                                    media_kind:Request.kind,
                                    message:"provider does not implement this media kind"})
    ).

provider_execute(fake, Request, Outcome) :-
    fake_fixture(Request.options, Fixture),
    fake_execute(Fixture, Request, Outcome).

fake_execute(failure, Request,
             error(media_error{kind:provider_failure,
                               provider:fake,
                               media_kind:Request.kind,
                               message:"deterministic fake provider failure"})) :-
    !.
fake_execute(malformed, _, ok(malformed_fake_response)) :- !.
fake_execute(success, Request, ok(Result)) :-
    term_hash(Request, Fingerprint),
    Result = media_result{provider:fake,
                          kind:Request.kind,
                          prompt:Request.prompt,
                          inputs:Request.inputs,
                          options:Request.options,
                          artifact:artifact_ref(fake,
                                                Request.kind,
                                                Fingerprint),
                          status:completed}.

fake_fixture(Options, Fixture) :-
    (   is_dict(Options),
        get_dict(fixture, Options, Fixture0)
    ->  normalize_atom(Fixture0, Fixture)
    ;   Fixture = success
    ).

normalize_request(Request0, Request) :-
    (   is_dict(Request0)
    ->  true
    ;   throw(error(type_error(media_request, Request0),
                    context(media_generate_async/2,
                            'media request must be a dict')))
    ),
    require_key(Request0, kind, Kind0),
    normalize_atom(Kind0, Kind),
    memberchk(Kind, [image, video, voice]),
    require_key(Request0, provider, Provider0),
    normalize_atom(Provider0, Provider),
    require_key(Request0, prompt, Prompt),
    text_string(Prompt, PromptString),
    optional_key(Request0, inputs, [], Inputs),
    (   is_list(Inputs)
    ->  true
    ;   throw(error(type_error(list, Inputs),
                    context(media_generate_async/2,
                            'media request inputs must be a list')))
    ),
    optional_key(Request0, options, _{}, Options),
    (   is_dict(Options)
    ->  true
    ;   throw(error(type_error(dict, Options),
                    context(media_generate_async/2,
                            'media request options must be a dict')))
    ),
    Request = media_request{kind:Kind,
                            provider:Provider,
                            prompt:PromptString,
                            inputs:Inputs,
                            options:Options}.

request_with_kind(Kind, Request0, Request) :-
    (   is_dict(Request0)
    ->  put_dict(kind, Request0, Kind, Request)
    ;   throw(error(type_error(media_request, Request0),
                    context(media_generate_async/2,
                            'media request must be a dict')))
    ).

metadata(Request, Metadata) :-
    term_hash(Request, Fingerprint),
    Metadata = async_metadata{operation:media_generate,
                              media_kind:Request.kind,
                              provider:Request.provider,
                              request_fingerprint:Fingerprint}.

ensure_async_runtime :-
    (   current_predicate(rlm_async:rlm_async_submit/3)
    ->  true
    ;   throw(error(existence_error(prolog_rlm_runtime, rlm_async),
                    context(media_generate_async/2,
                            'load prolog-rlm before using async media APIs')))
    ).

provider_exception(Exception,
                   error(media_error{kind:exception,
                                     exception:Safe,
                                     message:"media provider execution raised an exception"})) :-
    catch(term_string(Exception, Safe, [quoted(true)]),
          _,
          Safe = "<unprintable exception>").

require_key(Dict, Key, Value) :-
    (   get_dict(Key, Dict, Value)
    ->  true
    ;   throw(error(existence_error(media_request_key, Key),
                    context(media_generate_async/2,
                            'media request is missing a required key')))
    ).

optional_key(Dict, Key, Default, Value) :-
    (   get_dict(Key, Dict, Found)
    ->  Value = Found
    ;   Value = Default
    ).

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
                context(media_generate_async/2,
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
                context(media_generate_async/2,
                        'prompt must be text'))).
