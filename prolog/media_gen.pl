:- module(media_gen,
          [ media_gen_ready/0,
            media_route/2,
            expert_branch/1,
            media_org_template/3,
            media_assets_empty/2,
            media_assets_load/2,
            media_assets_ensure/3,
            media_assets_write/2,
            media_asset_validate/2,
            media_asset_register/3,
            media_assets_org/2,
            image_generate_async/2,
            video_generate_async/2,
            voice_generate_async/2,
            video_submit_remote_async/2,
            video_poll_remote_async/2,
            video_cancel_remote_async/2,
            media_future_await/2,
            media_future_destroy/1,
            media_graph_backend_open/2,
            media_graph_backend_close/1,
            media_graph_checkpoint/3,
            media_graph_run_async/3,
            media_graph_run_async/4,
            media_graph_resume_async/4
          ]).

:- use_module(media_gen_runtime).
:- use_module(media_gen_expert,
              [ media_route/2,
                expert_branch/1
              ]).
:- use_module(media_gen_template,
              [ media_org_template/3
              ]).
:- use_module(media_gen_assets,
              [ media_assets_empty/2,
                media_assets_load/2,
                media_assets_ensure/3,
                media_assets_write/2,
                media_asset_validate/2,
                media_asset_register/3,
                media_assets_org/2
              ]).
:- use_module(media_gen_graph,
              [ media_gen_graph_ready/0,
                media_graph_backend_open/2,
                media_graph_backend_close/1,
                media_graph_checkpoint/3,
                media_graph_run_async/3,
                media_graph_run_async/4,
                media_graph_resume_async/4
              ]).
:- use_module('media/media', []).

media_gen_ready :-
    media_gen_runtime_ready,
    media_gen_expert:media_gen_expert_ready,
    media_gen_graph_ready.

image_generate_async(Request, Future) :-
    media_gen_runtime_ready,
    media:image_generate_async(Request, Future).

video_generate_async(Request, Future) :-
    media_gen_runtime_ready,
    media:video_generate_async(Request, Future).

voice_generate_async(Request, Future) :-
    media_gen_runtime_ready,
    media:voice_generate_async(Request, Future).

video_submit_remote_async(Request, Future) :-
    media_gen_runtime_ready,
    media:video_submit_remote_async(Request, Future).

video_poll_remote_async(Job, Future) :-
    media_gen_runtime_ready,
    media:video_poll_remote_async(Job, Future).

video_cancel_remote_async(Job, Future) :-
    media_gen_runtime_ready,
    media:video_cancel_remote_async(Job, Future).

media_future_await(Future, Outcome) :-
    media_gen_runtime_ready,
    rlm_async:rlm_future_await(Future, Outcome).

media_future_destroy(Future) :-
    media_gen_runtime_ready,
    rlm_async:rlm_future_destroy(Future).
