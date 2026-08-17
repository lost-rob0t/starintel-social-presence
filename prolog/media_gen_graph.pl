:- module(media_gen_graph,
          [ media_gen_graph_ready/0,
            media_graph_compile/1,
            media_graph_backend_open/2,
            media_graph_backend_close/1,
            media_graph_checkpoint/3,
            media_graph_run_async/3,
            media_graph_run_async/4,
            media_graph_resume_async/4
          ]).

:- use_module(media_gen_runtime).
:- use_module(media_gen_expert).
:- use_module('media/media').

media_gen_graph_ready :-
    media_gen_runtime_ready,
    media_graph_compile(_).

media_graph_compile(Compiled) :-
    media_gen_runtime_ready,
    graph_spec(Spec),
    graph_registry(Registry),
    rlm_graph:graph_compile(Spec, Registry, [], ok(Compiled)).

media_graph_backend_open(Kind, Backend) :-
    media_gen_runtime_ready,
    rlm_graph:graph_backend_open(Kind, Backend).

media_graph_backend_close(Backend) :-
    rlm_graph:graph_backend_close(Backend).

media_graph_checkpoint(Backend, RunId, Snapshot) :-
    media_gen_runtime_ready,
    rlm_graph:graph_checkpoint(Backend, RunId, Snapshot).

media_graph_run_async(Request, Backend, Future) :-
    media_graph_run_async(Request, Backend, auto, Future).

media_graph_run_async(Request0, Backend, RunId, Future) :-
    media_graph_compile(Compiled),
    canonical_request(Request0, Request),
    Initial = media_graph_initial{request:Request},
    rlm_graph:graph_run_async(Compiled,
                              Initial,
                              [ backend(Backend),
                                time_limit(30.0),
                                run_id(RunId)
                              ],
                              Future).

media_graph_resume_async(Backend, RunId, Resume, Future) :-
    media_graph_compile(Compiled),
    rlm_graph:graph_resume_async(Compiled,
                                 Backend,
                                 RunId,
                                 Resume,
                                 [time_limit(30.0)],
                                 Future).

graph_spec(
    graph(media_gen_v1,
          [ field(request, any, none, replace),
            field(route, any, none, replace),
            field(generation_context, any, none, replace),
            field(provider_request, any, none, replace),
            field(artifact, any, none, replace),
            field(approval, any, none, replace),
            field(remote_job, any, none, replace),
            field(video_artifact, any, none, replace),
            field(submit_count, integer, 0, sum)
          ],
          [ node(expert_plan, expert_plan_handler),
            node(compile_context, compile_context_handler),
            node(compile_request, compile_request_handler),
            node(generate_keyframe, generate_keyframe_handler),
            node(human_review, human_review_handler),
            node(submit_video, submit_video_handler),
            node(remote_wait, remote_wait_handler),
            node(poll_video, poll_video_handler),
            node(finalize, finalize_handler)
          ],
          [ edge(start, expert_plan),
            edge(expert_plan, compile_context),
            edge(compile_context, compile_request),
            edge(compile_request, generate_keyframe),
            edge(generate_keyframe, human_review),
            edge(human_review, submit_video),
            edge(submit_video, remote_wait),
            edge(remote_wait, poll_video),
            edge(poll_video, finalize),
            edge(finalize, end)
          ])).

graph_registry(
    [ handler(expert_plan_handler,
              media_gen_graph:expert_plan_node),
      handler(compile_context_handler,
              media_gen_graph:compile_context_node),
      handler(compile_request_handler,
              media_gen_graph:compile_request_node),
      handler(generate_keyframe_handler,
              media_gen_graph:generate_keyframe_node),
      handler(human_review_handler,
              media_gen_graph:human_review_node),
      handler(submit_video_handler,
              media_gen_graph:submit_video_node),
      handler(remote_wait_handler,
              media_gen_graph:remote_wait_node),
      handler(poll_video_handler,
              media_gen_graph:poll_video_node),
      handler(finalize_handler,
              media_gen_graph:finalize_node)
    ]).

expert_plan_node(State, _, update(media_patch{route:Decision})) :-
    get_dict(request, State, Request),
    media_route(Request, Decision).

compile_context_node(State, _, update(media_patch{generation_context:Context})) :-
    get_dict(request, State, Request),
    get_dict(route, State, Route),
    get_dict(matched_characters, Route, Characters),
    Context = generation_context{request:Request,
                                 route:Route,
                                 characters:Characters,
                                 input_assets:[],
                                 constraints:media_constraints{human_review:true}}.

compile_request_node(State, _, update(media_patch{provider_request:ProviderRequest})) :-
    get_dict(request, State, Request),
    get_dict(route, State, Route),
    get_dict(description, Request, Prompt),
    get_dict(kind, Request, Kind0),
    normalize_media_kind(Kind0, Kind),
    get_dict(provider, Route, TargetProvider),
    get_dict(model, Route, TargetModel),
    ProviderRequest = media_request{kind:Kind,
                                    provider:fake,
                                    prompt:Prompt,
                                    inputs:[],
                                    options:media_provider_options{
                                                fixture:success,
                                                target_provider:TargetProvider,
                                                target_model:TargetModel}}.

generate_keyframe_node(State, _, update(media_patch{artifact:Artifact})) :-
    get_dict(provider_request, State, ProviderRequest),
    media:media_generate_execute(ProviderRequest, Outcome),
    (   Outcome = ok(Result)
    ->  get_dict(artifact, Result, Artifact)
    ;   throw(error(media_generation_failed(Outcome),
                    context(generate_keyframe_node/3,
                            'fake media provider failed inside graph')))
    ).

human_review_node(_, _,
                  interrupt(approval_required,
                            media_patch{approval:pending})).

submit_video_node(State, Context,
                  update(media_patch{approval:approved,
                                     remote_job:RemoteJob,
                                     submit_count:1})) :-
    get_dict(resume, Context, approved),
    get_dict(request, State, Request),
    get_dict(description, Request, Prompt),
    get_dict(flow, Request, Flow),
    put_dict(kind, Request, video, VideoRouteRequest),
    media_route(VideoRouteRequest, VideoRoute),
    get_dict(provider, VideoRoute, TargetProvider),
    get_dict(model, VideoRoute, TargetModel),
    get_dict(artifact, State, Keyframe),
    VideoRequest = video_request{provider:fake,
                                 prompt:Prompt,
                                 inputs:[Keyframe],
                                 options:media_provider_options{
                                             submit_fixture:success,
                                             poll_fixture:success,
                                             flow:Flow,
                                             target_provider:TargetProvider,
                                             target_model:TargetModel}},
    media:video_submit_remote_execute(VideoRequest, Outcome),
    (   Outcome = ok(RemoteJob),
        is_dict(RemoteJob),
        get_dict(status, RemoteJob, remote_pending)
    ->  true
    ;   throw(error(media_remote_submit_failed(Outcome),
                    context(submit_video_node/3,
                            'remote video submission did not return a pending job')))
    ).
submit_video_node(_, Context, _) :-
    get_dict(resume, Context, Resume),
    throw(error(media_review_not_approved(Resume),
                context(submit_video_node/3,
                        'video submission requires explicit approval'))).

remote_wait_node(_, _,
                 interrupt(remote_pending,
                           media_patch{})).

poll_video_node(State, _,
                update(media_patch{video_artifact:VideoArtifact})) :-
    get_dict(remote_job, State, RemoteJob),
    media:video_poll_remote_execute(RemoteJob, Outcome),
    (   Outcome = ok(Result),
        is_dict(Result),
        get_dict(status, Result, completed),
        get_dict(artifact, Result, VideoArtifact)
    ->  true
    ;   throw(error(media_remote_poll_incomplete(Outcome),
                    context(poll_video_node/3,
                            'remote video poll did not complete')))
    ).

finalize_node(_, _, update(media_patch{})).

canonical_request(Request0, Request) :-
    (   is_dict(Request0)
    ->  dict_pairs(Request0, _, Pairs),
        dict_pairs(Request, media_graph_request, Pairs)
    ;   throw(error(type_error(media_request, Request0),
                    context(media_graph_run_async/4,
                            'graph request must be a dict')))
    ),
    (   ground(Request)
    ->  true
    ;   throw(error(instantiation_error,
                    context(media_graph_run_async/4,
                            'durable graph request must be ground')))
    ).

normalize_media_kind(Kind, Kind) :-
    atom(Kind),
    memberchk(Kind, [image, video, voice]),
    !.
normalize_media_kind(KindString, Kind) :-
    string(KindString),
    atom_string(Kind, KindString),
    memberchk(Kind, [image, video, voice]),
    !.
normalize_media_kind(Kind, _) :-
    throw(error(domain_error(media_kind, Kind),
                context(compile_request_node/3,
                        'graph generation requires image, video, or voice'))).
