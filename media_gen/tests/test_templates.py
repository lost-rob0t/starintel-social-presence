from starintel_media_gen.catalog import CharacterCatalog
from starintel_media_gen.models import MediaKind, MediaRequest
from starintel_media_gen.templates import render_org


def test_comic_template_encodes_workflow_and_fumble():
    text = render_org(
        "Rick Explains StarIntel",
        MediaRequest("Morty asks Rick to explain StarIntel", MediaKind.BOTH, "comic-explainer"),
        CharacterCatalog(),
    )
    assert "* Human approval gate" in text
    assert "Facial expression" in text
    assert "Fumble" in text
    assert "gemini-3-pro-image" in text
    assert "veo-3.1-generate-preview" in text
