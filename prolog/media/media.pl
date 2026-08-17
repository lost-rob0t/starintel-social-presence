:- module(media,
          [ media_provider/2,
            media_generate_async/2,
            media_generate_execute/2,
            image_generate_async/2,
            image_generate_execute/2,
            video_generate_async/2,
            video_generate_execute/2,
            voice_generate_async/2,
            voice_generate_execute/2,
            video_submit_remote_async/2,
            video_submit_remote_execute/2,
            video_poll_remote_async/2,
            video_poll_remote_execute/2,
            video_cancel_remote_async/2,
            video_cancel_remote_execute/2
          ]).

/** <module> Provider-neutral media generation boundary

This module deliberately contains no StarIntel, Emacs, social-platform, or
project-layout assumptions. It is intended to remain portable enough to move
into prolog-rlm later.

The public generation path is canonical async-first: execute predicate ->
rlm_async Future. Sync callers may await the returned Future themselves.
Code already running inside an rlm_async/rlm_graph worker calls the execute
predicates directly rather than nesting Future waits.

Provider-bound request data is canonicalized to ground terms before scheduling.
In particular, anonymous-tag SWI dicts are converted to named dicts so their
representation-level tag variables cannot leak into Future metadata or durable
execution identity.

Remote media jobs are explicit serializable terms. A submit operation returns a
stable remote job handle; polling and cancellation consume that handle. The
fake provider gives deterministic offline coverage of this lifecycle. This
contract does not claim to solve crash atomicity for arbitrary paid effects;
that generic once-only boundary remains an upstream prolog-rlm concern.
*/

media_provider(fake, image).
media_provider(fake, video).
media_provider(fake, voice).

media_generate_async(Request0, Future) :-
    normalize_request(Request0, Request),
    ensure_async_runtime,
    metadata(media_generate, Request, Metadata),
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

video_submit_remote_async(Request0, Future) :-
    request_with_kind(video, Request0, Request1),
    normalize_request(Request1, Request),
    ensure_async_runtime,
    metadata(video_submit_remote, Request, Metadata),
    rlm_async:rlm_async_submit(media:video_submit_remote_execute(Request),
                               Metadata,
                               Future).

video_submit_remote_execute(Request0, Outcome) :-
    catch(( request_with_kind(video, Request0, Request1),
            normalize_request(Request1, Request),
            execute_remote_submit(Request, Outcome) ),
          Exception,
          provider_exception(Exception, Outcome)).

video_poll_remote_async(Job0, Future) :-
    normalize_remote_job(Job0, Job),
    ensure_async_runtime,
    remote_metadata(video_poll_remote, Job, Metadata),
    rlm_async:rlm_async_submit(media:video_poll_remote_execute(Job),
                               Metadata,
                               Future).

video_poll_remote_execute(Job0, Outcome) :-
    catch(( normalize_remote_job(Job0, Job),
            execute_remote_poll(Job, Outcome) ),
          Exception,
          provider_exception(Exception, Outcome)).

video_cancel_remote_async(Job0, Future) :-
    normalize_remote_job(Job0, Job),
    ensure_async_runtime,
    remote_metadata(video_cancel_remote, Job, Metadata),
    rlm_async:rlm_async_submit(media:video_cancel_remote_execute(Job),
                               Metadata,
                               Future).

video_cancel_remote_execute(Job0, Outcome) :-
    catch(( normalize_remote_job(Job0, Job),
            execute_remote_cancel(Job, Outcome) ),
          Exception,
          provider_exception(Exception, Outcome)).

execute_provider(Request, Outcome) :-
    (   media_provider(Request.provider, Request.kind)
    ->  provider_execute(Request.provider, Request, Outcome)
    ;   Outcome = error(media_error{kind:unsupported_provider,
                                    provider:Request.provider,
                                    media_kind:Request.kind,
                                    message:"provider does not implement this media kind"})
    ).

provider_execute(fake, Request, Outcome) :-
    fake_fixture(Request.options, fixture, success, Fixture),
    fake_execute(Fixture, Request, Outcome).

fake_execute(failure, Request,
             error(media_error{kind:provider_failure,
                               provider:fake,
                               media_kind:Request.kind,
                               message:"deterministic fake provider failure"})) :-
    !.
fake_execute(malformed, _, ok(malformed_fake_response)) :- !.
fake_execute(success, Request, ok(Result)) :-
    request_fingerprint(Request, Fingerprint),
    Result = media_result{provider:fake,
                          kind:Request.kind,
                          prompt:Request.prompt,
                          inputs:Request.inputs,
                          options:Request.options,
                          artifact:artifact_ref(fake,
                                                Request.kind,
                                                Fingerprint),
                          status:completed}.

execute_remote_submit(Request, Outcome) :-
    (   media_provider(Request.provider, video)
    ->  remote_submit_provider(Request.provider, Request, Outcome)
    ;   Outcome = error(media_error{kind:unsupported_remote_video_provider,
                                    provider:Request.provider,
                                    message:"provider does not implement remote video jobs"})
    ).

remote_submit_provider(fake, Request, Outcome) :-
    fake_fixture(Request.options, submit_fixture, success, Fixture),
    fake_remote_submit(Fixture, Request, Outcome).

fake_remote_submit(failure, _,
                   error(media_error{kind:remote_submit_failure,
                                     provider:fake,
                                     message:"deterministic fake remote submit failure"})) :-
    !.
fake_remote_submit(malformed, _, ok(malformed_remote_job)) :- !.
fake_remote_submit(success, Request, ok(Job)) :-
    request_fingerprint(Request, Fingerprint),
    format(string(RemoteId), "fake-video-~16r", [Fingerprint]),
    Job = remote_media_job{provider:fake,
                           kind:video,
                           remote_id:RemoteId,
                           request_fingerprint:Fingerprint,
                           request:Request,
                           status:remote_pending}.

execute_remote_poll(Job, Outcome) :-
    remote_poll_provider(Job.provider, Job, Outcome).

remote_poll_provider(fake, Job, Outcome) :-
    get_dict(request, Job, Request),
    fake_fixture(Request.options, poll_fixture, success, Fixture),
    fake_remote_poll(Fixture, Job, Outcome).

fake_remote_poll(pending, Job, ok(Job)) :- !.
fake_remote_poll(failure, Job,
                 error(media_error{kind:remote_poll_failure,
                                   provider:Job.provider,
                                   remote_id:Job.remote_id,
                                   message:"deterministic fake remote poll failure"})) :-
    !.
fake_remote_poll(malformed, _, ok(malformed_remote_poll)) :- !.
fake_remote_poll(success, Job, ok(Result)) :-
    Result = remote_media_result{provider:Job.provider,
                                 kind:video,
                                 remote_id:Job.remote_id,
                                 request_fingerprint:Job.request_fingerprint,
                                 artifact:artifact_ref(Job.provider,
                                                       video,
                                                       Job.request_fingerprint),
                                 status:completed}.

execute_remote_cancel(Job, Outcome) :-
    remote_cancel_provider(Job.provider, Job, Outcome).

remote_cancel_provider(fake, Job, ok(Cancelled)) :-
    put_dict(status, Job, cancelled, Cancelled).

fake_fixture(Options, Key, Default, Fixture) :-
    (   is_dict(Options),
        get_dict(Key, Options, Fixture0)
    ->  normalize_atom(Fixture0, Fixture)
    ;   Fixture = Default
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
    optional_key(Request0, inputs, [], Inputs0),
    (   is_list(Inputs0)
    ->  maplist(canonical_data, Inputs0, Inputs)
    ;   throw(error(type_error(list, Inputs0),
                    context(media_generate_async/2,
                            'media request inputs must be a list')))
    ),
    optional_key(Request0, options, media_options{}, Options0),
    (   is_dict(Options0)
    ->  canonical_dict(media_options, Options0, Options)
    ;   throw(error(type_error(dict, Options0),
                    context(media_generate_async/2,
                            'media request options must be a dict')))
    ),
    Request = media_request{kind:Kind,
                            provider:Provider,
                            prompt:PromptString,
                            inputs:Inputs,
                            options:Options},
    require_ground(Request, media_request).

normalize_remote_job(Job0, Job) :-
    (   is_dict(Job0)
    ->  true
    ;   throw(error(type_error(remote_media_job, Job0),
                    context(video_poll_remote_async/2,
                            'remote media job must be a dict')))
    ),
    require_key(Job0, provider, Provider0),
    normalize_atom(Provider0, Provider),
    require_key(Job0, kind, Kind0),
    normalize_atom(Kind0, Kind),
    (   Kind == video
    ->  true
    ;   throw(error(domain_error(remote_media_kind, Kind),
                    context(video_poll_remote_async/2,
                            'remote media jobs currently support video')))
    ),
    require_key(Job0, remote_id, RemoteId0),
    text_string(RemoteId0, RemoteId),
    require_key(Job0, request_fingerprint, Fingerprint),
    integer(Fingerprint),
    require_key(Job0, request, Request0),
    normalize_request(Request0, Request),
    optional_key(Job0, status, remote_pending, Status0),
    normalize_atom(Status0, Status),
    Job = remote_media_job{provider:Provider,
                           kind:video,
                           remote_id:RemoteId,
                           request_fingerprint:Fingerprint,
                           request:Request,
                           status:Status},
    require_ground(Job, remote_media_job).

request_with_kind(Kind, Request0, Request) :-
    (   is_dict(Request0)
    ->  put_dict(kind, Request0, Kind, Request)
    ;   throw(error(type_error(media_request, Request0),
                    context(media_generate_async/2,
                            'media request must be a dict')))
    ).

canonical_data(Value, Value) :-
    atomic(Value),
    !.
canonical_data(Value, Canonical) :-
    is_dict(Value),
    !,
    canonical_dict(media_data, Value, Canonical).
canonical_data(Value, Canonical) :-
    is_list(Value),
    !,
    maplist(canonical_data, Value, Canonical).
canonical_data(Value, Value) :-
    ground(Value),
    !.
canonical_data(_, _) :-
    throw(error(instantiation_error,
                context(media_generate_async/2,
                        'media input data must be ground'))).

canonical_dict(Tag, Dict0, Dict) :-
    dict_pairs(Dict0, _, Pairs0),
    maplist(canonical_pair, Pairs0, Pairs),
    dict_pairs(Dict, Tag, Pairs).

canonical_pair(Key-Value0, Key-Value) :-
    canonical_data(Value0, Value).

metadata(Operation, Request, Metadata) :-
    request_fingerprint(Request, Fingerprint),
    Metadata = async_metadata{operation:Operation,
                              media_kind:Request.kind,
                              provider:Request.provider,
                              request_fingerprint:Fingerprint}.

remote_metadata(Operation, Job, Metadata) :-
    Metadata = async_metadata{operation:Operation,
                              media_kind:video,
                              provider:Job.provider,
                              remote_id:Job.remote_id,
                              request_fingerprint:Job.request_fingerprint}.

request_fingerprint(Request, Fingerprint) :-
    term_hash(Request, Fingerprint).

require_ground(Term, Label) :-
    (   ground(Term)
    ->  true
    ;   throw(error(instantiation_error,
                    context(media_generate_async/2,
                            Label)))
    ).

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
                        'prompt or remote identifier must be text'))).
