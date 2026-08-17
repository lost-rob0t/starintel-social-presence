:- initialization(main, main).

:- use_module('../prolog/media_gen').

run_id(media_process_restart).

main([File]) :-
    run_id(RunId),
    media_graph_backend_open(persist(File), Backend),
    Request = media_restart_request{description:"Rick and Morty explain StarIntel",
                                    kind:image,
                                    flow:'comic-explainer'},
    media_graph_run_async(Request, Backend, RunId, Future),
    media_future_await(Future, Outcome),
    media_future_destroy(Future),
    require_approval_pause(Outcome),
    media_graph_backend_close(Backend),
    halt(0).
main(_) :-
    format(user_error,
           'usage: swipl -q -s test/media_graph_restart_phase1.pl -- <checkpoint-file>~n',
           []),
    halt(2).

require_approval_pause(ok(Result)) :-
    Result.status == paused(approval_required),
    Result.run_id == media_process_restart,
    Result.state.approval == pending,
    Result.state.submit_count =:= 0,
    Result.state.artifact = artifact_ref(fake, image, _),
    !.
require_approval_pause(Outcome) :-
    format(user_error,
           'phase1 did not persist the expected approval pause: ~q~n',
           [Outcome]),
    halt(1).
