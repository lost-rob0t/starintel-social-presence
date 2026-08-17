:- initialization(main, main).

:- use_module('../prolog/media_gen').

run_id(media_process_restart).

main([File]) :-
    run_id(RunId),
    media_graph_backend_open(persist(File), Backend),
    media_graph_checkpoint(Backend, RunId, Snapshot),
    require_remote_checkpoint(Snapshot, RemoteId),
    media_graph_resume_async(Backend, RunId, poll, Future),
    media_future_await(Future, Outcome),
    media_future_destroy(Future),
    require_completed(Outcome, RemoteId),
    media_graph_backend_close(Backend),
    halt(0).
main(_) :-
    format(user_error,
           'usage: swipl -q -s test/media_graph_restart_phase3.pl -- <checkpoint-file>~n',
           []),
    halt(2).

require_remote_checkpoint(Snapshot, RemoteId) :-
    Snapshot.status == paused(remote_pending),
    Snapshot.state.approval == approved,
    Snapshot.state.submit_count =:= 1,
    Snapshot.state.remote_job.status == remote_pending,
    RemoteId = Snapshot.state.remote_job.remote_id,
    string(RemoteId),
    !.
require_remote_checkpoint(Snapshot, _) :-
    format(user_error,
           'phase3 could not reload the pending remote video job: ~q~n',
           [Snapshot]),
    halt(1).

require_completed(ok(Result), RemoteId) :-
    Result.status == completed,
    Result.state.approval == approved,
    Result.state.submit_count =:= 1,
    Result.state.remote_job.remote_id == RemoteId,
    Result.state.video_artifact = artifact_ref(fake, video, _),
    !.
require_completed(Outcome, _) :-
    format(user_error,
           'phase3 did not finish the persisted video job exactly once: ~q~n',
           [Outcome]),
    halt(1).
