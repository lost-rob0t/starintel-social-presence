:- initialization(main, main).

:- use_module('../prolog/media_gen').

run_id(media_process_restart).

main([File]) :-
    run_id(RunId),
    media_graph_backend_open(persist(File), Backend),
    media_graph_checkpoint(Backend, RunId, Snapshot),
    require_approval_checkpoint(Snapshot),
    media_graph_resume_async(Backend, RunId, approved, Future),
    media_future_await(Future, Outcome),
    media_future_destroy(Future),
    require_remote_pause(Outcome),
    media_graph_backend_close(Backend),
    halt(0).
main(_) :-
    format(user_error,
           'usage: swipl -q -s test/media_graph_restart_phase2.pl -- <checkpoint-file>~n',
           []),
    halt(2).

require_approval_checkpoint(Snapshot) :-
    Snapshot.status == paused(approval_required),
    Snapshot.state.approval == pending,
    Snapshot.state.submit_count =:= 0,
    !.
require_approval_checkpoint(Snapshot) :-
    format(user_error,
           'phase2 could not reload the expected approval checkpoint: ~q~n',
           [Snapshot]),
    halt(1).

require_remote_pause(ok(Result)) :-
    Result.status == paused(remote_pending),
    Result.state.approval == approved,
    Result.state.submit_count =:= 1,
    Result.state.remote_job.status == remote_pending,
    string(Result.state.remote_job.remote_id),
    Result.state.remote_job.request.inputs = [artifact_ref(fake, image, _)],
    !.
require_remote_pause(Outcome) :-
    format(user_error,
           'phase2 did not persist one remote video submission: ~q~n',
           [Outcome]),
    halt(1).
