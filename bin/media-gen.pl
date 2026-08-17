#!/usr/bin/env swipl

:- use_module(library(http/json)).
:- use_module(library(readutil)).
:- use_module('../prolog/media_gen').

:- initialization(main, main).

main :-
    current_prolog_flag(argv, Argv),
    catch(dispatch(Argv, Code),
          Exception,
          ( print_message(error, Exception), Code = 1 )),
    halt(Code).

dispatch(["ready"], 0) :-
    media_gen_ready,
    writeln("media-gen ready"),
    !.
dispatch(["branches"], 0) :-
    forall(expert_branch(Branch), writeln(Branch)),
    !.
dispatch(["route", Kind0, Flow0|DescriptionParts], 0) :-
    DescriptionParts \== [],
    atom_string(Kind, Kind0),
    atom_string(Flow, Flow0),
    atomics_to_string(DescriptionParts, " ", Description),
    media_route(_{description:Description, kind:Kind, flow:Flow}, Decision),
    json_write_dict(current_output, Decision, [width(0)]),
    nl,
    !.
dispatch(["template", Title, Kind0, Flow0|DescriptionParts], 0) :-
    DescriptionParts \== [],
    atom_string(Kind, Kind0),
    atom_string(Flow, Flow0),
    atomics_to_string(DescriptionParts, " ", Description),
    media_org_template(Title,
                       _{description:Description, kind:Kind, flow:Flow},
                       Text),
    format("~s", [Text]),
    !.
dispatch(["shell"], 0) :-
    media_gen_ready,
    shell_loop,
    !.
dispatch(_, 2) :-
    format(user_error,
           "usage: media-gen ready | branches | route KIND FLOW DESCRIPTION... | template TITLE KIND FLOW DESCRIPTION... | shell~n",
           []).

shell_loop :-
    format("media-gen?> ", []),
    flush_output,
    read_line_to_string(user_input, Line),
    shell_line(Line, Continue),
    (   Continue == true
    ->  shell_loop
    ;   true
    ).

shell_line(end_of_file, false) :- !.
shell_line(Line, Continue) :-
    split_string(Line, " \t", " \t", Parts),
    shell_parts(Parts, Continue).

shell_parts([], true) :- !.
shell_parts(["quit"], false) :- !.
shell_parts(["exit"], false) :- !.
shell_parts(["ready"], true) :-
    !,
    ( media_gen_ready -> writeln("ready") ; writeln("not ready") ).
shell_parts(["branches"], true) :-
    !,
    forall(expert_branch(Branch), writeln(Branch)).
shell_parts(["route", Kind0, Flow0|DescriptionParts], true) :-
    DescriptionParts \== [],
    !,
    atom_string(Kind, Kind0),
    atom_string(Flow, Flow0),
    atomics_to_string(DescriptionParts, " ", Description),
    catch(( media_route(_{description:Description, kind:Kind, flow:Flow}, Decision),
            json_write_dict(current_output, Decision, [width(0)]),
            nl ),
          Exception,
          print_message(error, Exception)).
shell_parts(["why"|_], true) :-
    !,
    writeln("Use `route KIND FLOW DESCRIPTION...`; the returned decision includes reason and branches.").
shell_parts(_, true) :-
    writeln("commands: ready | branches | route KIND FLOW DESCRIPTION... | why | quit").
