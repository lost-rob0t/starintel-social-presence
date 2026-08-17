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
            field(approval, any, none, replace)
          ],
          [ node(expert_plan, expert_plan_handler),
            node(compile_context, compile_context_handler),
            node(compile_request, compile_request_handler),
            node(generate_keyframe, generate_keyframe_handler),
            node(human_review, human_review_handler),
            node(finalize, finalize_handler)
          ],
          [ edge(start, expert_plan),
            edge(expert_plan, compile_context),
            edge(compile_context, compile_request),
            edge(compile_request, generate_keyframe),
            edge(generate_keyframe, human_review),
            edge(human_review, finalize),
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

finalize_node(_, Context, update(media_patch{approval:Approval})) :-
    get_dict(resume, Context, Resume),
    (   Resume == none
    ->  Approval = missing_resume
    ;   Approval = Resume
    ).

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
