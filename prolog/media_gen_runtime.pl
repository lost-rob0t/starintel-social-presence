:- module(media_gen_runtime,
          [ media_gen_runtime_ready/0,
            prolog_rlm_root/1
          ]).

:- use_module(library(filesex)).

:- dynamic runtime_loaded/0.

media_gen_runtime_ready :-
    with_mutex(media_gen_runtime, ensure_runtime_loaded).

ensure_runtime_loaded :-
    runtime_loaded,
    !.
ensure_runtime_loaded :-
    prolog_rlm_root(Root),
    directory_file_path(Root, prolog, PrologDir),
    directory_file_path(PrologDir, 'rlm.pl', Entry),
    (   exists_file(Entry)
    ->  true
    ;   throw(error(existence_error(prolog_rlm_entrypoint, Entry),
                    context(media_gen_runtime_ready/0,
                            'PROLOG_RLM_DIR does not contain prolog/rlm.pl')))
    ),
    load_files(Entry, [if(not_loaded)]),
    (   current_predicate(rlm:rlm_ready/0),
        rlm:rlm_ready
    ->  assertz(runtime_loaded)
    ;   throw(error(resource_error(prolog_rlm),
                    context(media_gen_runtime_ready/0,
                            'prolog-rlm loaded but did not report ready')))
    ).

prolog_rlm_root(Root) :-
    configured_root('PROLOG_RLM_DIR', Root),
    !.
prolog_rlm_root(Root) :-
    configured_root('STARINTEL_PROLOG_RLM_DIR', Root),
    !.
prolog_rlm_root(Root) :-
    source_file(media_gen_runtime:media_gen_runtime_ready, Source),
    file_directory_name(Source, PrologDir),
    file_directory_name(PrologDir, RepositoryRoot),
    file_directory_name(RepositoryRoot, Parent),
    directory_file_path(Parent, 'prolog-rlm', Candidate),
    exists_directory(Candidate),
    !,
    Root = Candidate.
prolog_rlm_root(_) :-
    throw(error(existence_error(environment, 'PROLOG_RLM_DIR'),
                context(media_gen_runtime_ready/0,
                        'set PROLOG_RLM_DIR to a current prolog-rlm checkout'))).

configured_root(Name, Root) :-
    getenv(Name, Raw),
    Raw \== '',
    absolute_file_name(Raw,
                       Root,
                       [ file_type(directory),
                         access(read),
                         file_errors(fail)
                       ]).
