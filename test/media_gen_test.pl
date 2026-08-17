:- begin_tests(media_gen).

:- use_module('../prolog/media_gen').

branch_request('reference.starintel_native',
               _{description:"StarIntel-chan explains Star-Expert",
                 kind:image,
                 flow:'starintel-brand'}).
branch_request('reference.fictional',
               _{description:"Morty explains the graph",
                 kind:image,
                 flow:'comic-explainer'}).
branch_request('reference.mixed',
               _{description:"StarIntel-chan argues with Morty about the graph",
                 kind:image,
                 flow:'comic-explainer'}).
branch_request('reference.generic',
               _{description:"A black and gold abstract network diagram",
                 kind:image,
                 flow:auto}).
branch_request('image.openai_native',
               _{description:"StarIntel-chan explains Star-Expert",
                 kind:image,
                 flow:'starintel-brand'}).
branch_request('image.google_fictional',
               _{description:"Morty explains the graph",
                 kind:image,
                 flow:'comic-explainer'}).
branch_request('image.override',
               _{description:"A generic diagram",
                 kind:image,
                 flow:auto,
                 provider_override:google}).
branch_request('video.google_default',
               _{description:"Animate Morty staring at the graph",
                 kind:video,
                 flow:'image-to-video'}).
branch_request('video.override',
               _{description:"Animate a generic graph",
                 kind:video,
                 flow:'image-to-video',
                 provider_override:openai}).

test(runtime_ready) :-
    media_gen_ready.

test(starintel_native_image_routes_openai) :-
    media_route(_{description:"StarIntel-chan explains Star-Expert",
                  kind:image,
                  flow:'starintel-brand'},
                Decision),
    get_dict(provider, Decision, openai),
    get_dict(reference_class, Decision, starintel_only),
    get_dict(branches, Decision, Branches),
    memberchk('image.openai_native', Branches).

test(show_reference_image_routes_google) :-
    media_route(_{description:"Morty asks Rick to explain StarIntel",
                  kind:image,
                  flow:'comic-explainer'},
                Decision),
    get_dict(provider, Decision, google),
    get_dict(reference_class, Decision, show_reference),
    get_dict(matched_characters, Decision, Matches),
    member(Morty, Matches),
    get_dict(canonical, Morty, "Morty Smith").

test(show_reference_video_routes_google) :-
    media_route(_{description:"Animate Morty staring at the graph",
                  kind:video,
                  flow:'image-to-video'},
                Decision),
    get_dict(provider, Decision, google),
    get_dict(branches, Decision, Branches),
    memberchk('video.google_default', Branches).

test(ambiguous_rick_requires_context) :-
    media_route(_{description:"Rick explains the graph",
                  kind:image,
                  flow:auto},
                Bare),
    get_dict(matched_characters, Bare, BareMatches),
    \+ ( member(M, BareMatches),
         get_dict(canonical, M, "Rick Sanchez") ),
    media_route(_{description:"Rick and Morty: Rick explains the graph",
                  kind:image,
                  flow:'comic-explainer'},
                Contextual),
    get_dict(matched_characters, Contextual, ContextualMatches),
    member(Rick, ContextualMatches),
    get_dict(canonical, Rick, "Rick Sanchez").

test(comic_template_preserves_review_and_fumble) :-
    media_org_template("Rick Explains StarIntel",
                       _{description:"Morty asks Rick to explain StarIntel",
                         kind:both,
                         flow:'comic-explainer'},
                       Text),
    sub_string(Text, _, _, _, "* Human approval gate"),
    sub_string(Text, _, _, _, "Facial expression"),
    sub_string(Text, _, _, _, "Fumble"),
    sub_string(Text, _, _, _, "google").

test(fake_media_provider_is_async_and_preserves_inputs) :-
    Request = image_request{provider:fake,
                            prompt:"Draw the graph",
                            inputs:[asset_ref(graph_reference)],
                            options:_{fixture:success}},
    image_generate_async(Request, Future),
    media_future_await(Future, Outcome),
    media_future_destroy(Future),
    Outcome = ok(Result),
    get_dict(kind, Result, image),
    get_dict(inputs, Result, [asset_ref(graph_reference)]),
    get_dict(provider, Result, fake).

test(media_graph_interrupts_and_resumes) :-
    media_graph_backend_open(memory, Backend),
    setup_call_cleanup(
        true,
        ( Request = _{description:"Rick and Morty explain StarIntel",
                      kind:image,
                      flow:'comic-explainer'},
          media_graph_run_async(Request, Backend, Future),
          media_future_await(Future, PausedOutcome),
          media_future_destroy(Future),
          PausedOutcome = ok(Paused),
          get_dict(status, Paused, paused(approval_required)),
          get_dict(run_id, Paused, RunId),
          media_graph_resume_async(Backend, RunId, approved, ResumeFuture),
          media_future_await(ResumeFuture, CompletedOutcome),
          media_future_destroy(ResumeFuture),
          CompletedOutcome = ok(Completed),
          get_dict(status, Completed, completed),
          get_dict(state, Completed, State),
          get_dict(approval, State, approved)
        ),
        media_graph_backend_close(Backend)).

test(every_declared_expert_branch_has_a_fixture) :-
    forall(expert_branch(Branch),
           ( branch_request(Branch, Request),
             media_route(Request, Decision),
             get_dict(branches, Decision, Branches),
             memberchk(Branch, Branches) )).

:- end_tests(media_gen).
