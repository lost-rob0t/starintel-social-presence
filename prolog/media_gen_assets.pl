:- module(media_gen_assets,
          [ media_assets_empty/2,
            media_assets_load/2,
            media_assets_ensure/3,
            media_assets_write/2,
            media_asset_validate/2,
            media_asset_register/3,
            media_assets_org/2
          ]).

:- use_module(library(filesex)).
:- use_module(library(http/json)).
:- use_module(library(lists)).

asset_schema_version(1).

media_assets_empty(Title0, Manifest) :-
    text_string(Title0, Title),
    asset_schema_version(Version),
    Manifest = _{schema_version:Version,
                 title:Title,
                 assets:[]}.

media_assets_load(Path, Manifest) :-
    setup_call_cleanup(
        open(Path, read, Stream, [encoding(utf8)]),
        json_read_dict(Stream, Raw),
        close(Stream)),
    validate_manifest(Raw, Manifest).

media_assets_ensure(Path, Title, Manifest) :-
    (   exists_file(Path)
    ->  media_assets_load(Path, Manifest)
    ;   media_assets_empty(Title, Manifest),
        media_assets_write(Path, Manifest)
    ).

media_assets_write(Path, Manifest0) :-
    validate_manifest(Manifest0, Manifest),
    file_directory_name(Path, Directory),
    make_directory_path(Directory),
    setup_call_cleanup(
        open(Path, write, Stream, [encoding(utf8)]),
        ( json_write_dict(Stream, Manifest, [width(0)]),
          nl(Stream)
        ),
        close(Stream)).

media_asset_register(Path, Asset0, Updated) :-
    media_assets_load(Path, Manifest),
    media_asset_validate(Asset0, Asset),
    get_dict(id, Asset, Id),
    get_dict(assets, Manifest, Assets0),
    replace_or_append_asset(Id, Asset, Assets0, Assets),
    put_dict(assets, Manifest, Assets, Updated),
    media_assets_write(Path, Updated).

media_asset_validate(Asset0, Asset) :-
    (   is_dict(Asset0)
    ->  true
    ;   throw(error(type_error(media_asset, Asset0),
                    context(media_asset_validate/2,
                            'asset must be a dict')))
    ),
    require_nonempty_text(Asset0, id, Id),
    (   get_dict(source, Asset0, Source0),
        is_dict(Source0),
        get_dict(type, Source0, Type0),
        nonempty_text(Type0),
        get_dict(value, Source0, Value0),
        nonempty_text(Value0)
    ->  text_string(Type0, Type),
        text_string(Value0, Value),
        Source = _{type:Type, value:Value}
    ;   throw(error(domain_error(media_asset_source, Asset0),
                    context(media_asset_validate/2,
                            'asset source must contain non-empty type and value')))
    ),
    put_dict(_{id:Id, source:Source}, Asset0, Asset).

media_assets_org(Path, Org) :-
    media_assets_load(Path, Manifest),
    file_base_name(Path, FileName),
    manifest_title(Manifest, Path, Title),
    maplist(asset_org_row, Manifest.assets, Rows),
    (   Rows == []
    ->  Table = "| /no assets yet/ | | | | | | |"
    ;   atomics_to_string(Rows, "\n", Table)
    ),
    format(string(Org),
           "#+title: ~s — assets\n#+generated_from: ~w\n#+startup: overview\n\n* Canonical manifest\n=assets.json= is canonical project asset state. This Org buffer is a generated view.\nThe concrete manifest for this view is =~w=.\n\n* Assets\n| ID | Kind | Source type | Source | Role | Status | Characters |\n|----+------+-------------+--------+------+--------+------------|\n~s\n\n* Source semantics\n- =file= :: repository/local named asset path.\n- =url= :: external image/media URL.\n- =generated= :: generated output path, normally ignored unless deliberately curated.\n- =asset= :: reference to another asset ID.\n\n* Provenance :noexport:\n- Canonical data lives in the JSON manifest.\n- This Org view may be regenerated at any time.\n",
           [Title, FileName, FileName, Table]).

validate_manifest(Raw, Manifest) :-
    (   is_dict(Raw)
    ->  true
    ;   throw(error(type_error(media_asset_manifest, Raw),
                    context(media_assets_load/2,
                            'assets.json must contain a JSON object')))
    ),
    asset_schema_version(Expected),
    (   get_dict(schema_version, Raw, Expected)
    ->  true
    ;   ( get_dict(schema_version, Raw, Actual) -> true ; Actual = missing ),
        throw(error(domain_error(media_asset_schema_version, Actual),
                    context(media_assets_load/2,
                            'unsupported assets.json schema version')))
    ),
    (   get_dict(assets, Raw, Assets0),
        is_list(Assets0)
    ->  maplist(media_asset_validate, Assets0, Assets)
    ;   throw(error(type_error(media_asset_list, Raw),
                    context(media_assets_load/2,
                            'assets.json assets must be a list')))
    ),
    (   get_dict(title, Raw, Title0)
    ->  text_string(Title0, Title)
    ;   Title = ""
    ),
    put_dict(_{title:Title, assets:Assets}, Raw, Manifest).

replace_or_append_asset(Id, Asset, Assets0, Assets) :-
    (   select(Existing, Assets0, Rest),
        get_dict(id, Existing, Id)
    ->  Assets = [Asset|Rest]
    ;   append(Assets0, [Asset], Assets)
    ).

manifest_title(Manifest, Path, Title) :-
    get_dict(title, Manifest, Candidate),
    Candidate \== "",
    !,
    Title = Candidate.
manifest_title(_, Path, Title) :-
    file_directory_name(Path, Directory),
    file_base_name(Directory, Base),
    ( Base == '' -> Title = "Media assets" ; atom_string(Base, Title) ).

asset_org_row(Asset, Row) :-
    asset_cell(Asset, id, Id),
    asset_cell(Asset, kind, Kind),
    get_dict(source, Asset, Source),
    asset_cell(Source, type, SourceType),
    asset_cell(Source, value, SourceValue),
    asset_cell(Asset, role, Role),
    asset_cell(Asset, status, Status),
    asset_characters_cell(Asset, Characters),
    format(string(Row),
           "| ~s | ~s | ~s | ~s | ~s | ~s | ~s |",
           [Id, Kind, SourceType, SourceValue, Role, Status, Characters]).

asset_cell(Dict, Key, Cell) :-
    (   get_dict(Key, Dict, Value)
    ->  cell_string(Value, Raw),
        escape_org_cell(Raw, Cell)
    ;   Cell = ""
    ).

asset_characters_cell(Asset, Cell) :-
    (   get_dict(characters, Asset, Characters),
        is_list(Characters)
    ->  maplist(text_string, Characters, Texts),
        atomics_to_string(Texts, ", ", Raw),
        escape_org_cell(Raw, Cell)
    ;   Cell = ""
    ).

cell_string(Value, String) :-
    (   string(Value)
    ->  String = Value
    ;   atom(Value)
    ->  atom_string(Value, String)
    ;   number(Value)
    ->  number_string(Value, String)
    ;   term_string(Value, String, [quoted(false)])
    ).

escape_org_cell(Raw, Escaped) :-
    split_string(Raw, "|", "", Parts),
    atomics_to_string(Parts, "\\vert{}", Escaped).

require_nonempty_text(Dict, Key, String) :-
    (   get_dict(Key, Dict, Value),
        nonempty_text(Value)
    ->  text_string(Value, String)
    ;   throw(error(domain_error(media_asset_field, Key),
                    context(media_asset_validate/2,
                            'asset is missing a required non-empty field')))
    ).

nonempty_text(Value) :-
    text_string(Value, String),
    String \== "".

text_string(Value, String) :-
    string(Value),
    !,
    String = Value.
text_string(Value, String) :-
    atom(Value),
    !,
    atom_string(Value, String).
text_string(Value, String) :-
    number(Value),
    !,
    number_string(Value, String).
text_string(Value, _) :-
    throw(error(type_error(text, Value),
                context(media_gen_assets,
                        'expected textual asset metadata'))).
