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

has_character(Matches, Canonical) :-
    once(( member(Match, Matches),
           get_dict(canonical, Match, Canonical) )).

contains_text(Text, Needle) :-
    once(sub_string(Text, _, _, _, Needle)).

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
    has_character(Matches, "Morty Smith").

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
    \+ has_character(BareMatches, "Rick Sanchez"),
    media_route(_{description:"Rick and Morty: Rick explains the graph",
                  kind:image,
                  flow:'comic-explainer'},
                Contextual),
    get_dict(matched_characters, Contextual, ContextualMatches),
    has_character(ContextualMatches, "Rick Sanchez"),
    has_character(ContextualMatches, "Morty Smith").

test(comic_template_preserves_review_and_fumble) :-
    media_org_template("Rick Explains StarIntel",
                       _{description:"Morty asks Rick to explain StarIntel",
                         kind:both,
                         flow:'comic-explainer'},
                       Text),
    contains_text(Text, "* Human approval gate"),
    contains_text(Text, "Facial expression"),
    contains_text(Text, "Fumble"),
    contains_text(Text, "google").

test(asset_manifest_is_canonical_json) :-
    tmp_file(media_gen_assets, JsonPath),
    setup_call_cleanup(
        true,
        ( media_assets_ensure(JsonPath, "Rick Explains StarIntel", Empty),
          get_dict(schema_version, Empty, 1),
          get_dict(assets, Empty, []),
          Asset = _{id:"rick-ref",
                    kind:"image",
                    role:"character-reference",
                    status:"approved",
                    characters:["Rick Sanchez"],
                    source:_{type:"file", value:"assets/images/rick.png"}},
          media_asset_register(JsonPath, Asset, Updated),
          get_dict(assets, Updated, [Stored]),
          get_dict(id, Stored, "rick-ref"),
          media_assets_load(JsonPath, Reloaded),
          Reloaded = Updated,
          media_assets_org(JsonPath, Org),
          contains_text(Org, "rick-ref"),
          contains_text(Org, "assets.json")
        ),
        catch(delete_file(JsonPath), _, true)).

test(asset_manifest_rejects_missing_source,
     [throws(error(domain_error(media_asset_source, _), _))]) :-
    media_asset_validate(_{id:"broken", kind:"image"}, _).

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
