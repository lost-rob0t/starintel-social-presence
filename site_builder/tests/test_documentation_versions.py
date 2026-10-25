"""Default navigation follows the stable latest spec URL; historical pages survive."""
import json
from starintel_site_builder.builder import build_site


def test_old_documentation_is_retained_but_not_default(fake_repo, tmp_path):
    (fake_repo / 'docs/archive.json').write_text(json.dumps(['sub/nested.org']))
    out = tmp_path / 'site'
    build_site(fake_repo, out, fake_repo / '.build', externals=[])
    archived = (out / 'docs/sub/nested.html').read_text()
    assert 'Archived documentation' in archived
    assert 'noindex' in archived
    assert 'https://spec.starintel.actor/latest/' in archived
    current = (out / 'docs/fixture-docs.html').read_text()
    assert 'href="/docs/sub/nested.html"' not in current
    assert 'href="https://spec.starintel.actor/latest/">Spec</a>' in current
    assert 'href="/docs/sub/nested.html"' in (out / 'docs/versions.html').read_text()
    assert '/docs/sub/nested.html' not in (out / 'sitemap.xml').read_text()
    assert '/docs/sub/nested.html' not in (out / 'assets/graph.json').read_text()
