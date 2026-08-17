from starintel_media_gen.catalog import CharacterCatalog
from starintel_media_gen.models import MediaKind, MediaRequest, ReferenceClass
from starintel_media_gen.router import route


CATALOG = CharacterCatalog()


def test_starintel_native_image_routes_openai():
    decision = route(MediaRequest("StarIntel-chan explains Star-Expert", MediaKind.IMAGE, "starintel-brand"), CATALOG)
    assert decision.provider == "openai"
    assert decision.model == "gpt-image-2"
    assert decision.reference_class == ReferenceClass.STARINTEL_ONLY


def test_show_reference_image_routes_google():
    decision = route(MediaRequest("Morty asks Rick to explain StarIntel", MediaKind.IMAGE, "comic-explainer"), CATALOG)
    assert decision.provider == "google"
    assert decision.model == "gemini-3-pro-image"
    assert decision.reference_class == ReferenceClass.SHOW_REFERENCE


def test_show_reference_video_routes_veo():
    decision = route(MediaRequest("Animate Morty staring at the graph", MediaKind.VIDEO, "image-to-video"), CATALOG)
    assert decision.provider == "google"
    assert decision.model == "veo-3.1-generate-preview"


def test_ambiguous_rick_requires_universe_context():
    decision = route(MediaRequest("Rick explains the graph", MediaKind.IMAGE), CATALOG)
    assert not decision.matched_characters
    contextual = route(MediaRequest("Rick and Morty: Rick explains the graph", MediaKind.IMAGE), CATALOG)
    assert any(match.canonical == "Rick Sanchez" for match in contextual.matched_characters)
