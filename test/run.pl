:- initialization(main, main).

main :-
    load_files(['media_gen_test.pl'], [silent(true)]),
    (   run_tests
    ->  halt(0)
    ;   halt(1)
    ).
