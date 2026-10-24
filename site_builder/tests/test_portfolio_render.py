"""The personal site has its own navigation and presentation."""

from pathlib import Path
from typing import Iterator

import pytest

from starintel_site_builder import render
from starintel_site_builder.models import GraphModel, SiteModel, SourceDoc


@pytest.fixture(autouse=True)
def personal_vhost() -> Iterator[None]:
    render.set_bases(render.SiteBases(
        www="https://starintel.actor",
        blog="https://blog.starintel.actor",
        docs="https://docs.starintel.actor",
        nsaspy="https://nsaspy.starintel.actor",
    ))
    render.set_page_vhost("nsaspy")
    yield
    render.set_bases(render.SiteBases())
    render.set_page_vhost("www")


def test_personal_home_leads_to_resume_and_source_projects() -> None:
    project = SourceDoc(
        path=Path("nsaspy/projects/starintel.org"),
        section="portfolio",
        slug="starintel",
        title="StarIntel",
        description="Document-driven intelligence platform.",
        url="https://nsaspy.starintel.actor/projects/starintel.html",
        tags=("human", "starintel"),
        human=True,
    )
    page = render.portfolio_landing(SiteModel(portfolio=[project]))

    assert "I build systems that can explain what they know." in page
    assert 'href="https://nsaspy.starintel.actor/resume.html"' in page
    assert 'href="https://nsaspy.starintel.actor/projects/starintel.html"' in page
    assert 'href="https://blog.starintel.actor/index.html"' in page
    assert "badge--human" not in page


def test_resume_has_personal_navigation_without_publication_badges() -> None:
    resume = SourceDoc(
        path=Path("nsaspy/resume.org"),
        section="portfolio",
        slug="resume",
        title="Resume",
        description="Systems and intelligence tooling engineer.",
        url="https://nsaspy.starintel.actor/resume.html",
        tags=("human", "resume"),
        human=True,
    )
    page = render.article_page(
        resume,
        '<nav id="table-of-contents"></nav><h2>nsaspy</h2>',
        GraphModel(),
        [("Work", render.portfolio_url()), ("Resume", None)],
    )

    assert 'class="site--nsaspy"' in page
    assert 'class="article portfolio-article portfolio-article--resume"' in page
    assert 'aria-current="page">Resume</a>' in page
    assert 'href="mailto:nsaspy@airmail.cc"' in page
    assert "badge--human" not in page
    assert "badge--post" not in page


def test_resume_links_to_each_project_page() -> None:
    resume = SourceDoc(
        path=Path("nsaspy/resume.org"), section="portfolio", slug="resume",
        title="Resume", url="https://nsaspy.starintel.actor/resume.html",
    )
    projects = [
        SourceDoc(
            path=Path(f"nsaspy/projects/{slug}.org"), section="portfolio",
            slug=slug, title=title,
            url=f"https://nsaspy.starintel.actor/projects/{slug}.html",
        )
        for slug, title in (("starintel", "StarIntel"), ("quasar", "Quasar"))
    ]
    page = render.article_page(
        resume, "<p>Work summary.</p>", GraphModel(), [],
        related_projects=projects,
    )

    assert 'id="project-pages-title"' in page
    for project in projects:
        assert f'href="{project.url}"' in page


def test_daily_note_keeps_its_own_label() -> None:
    note = SourceDoc(
        path=Path("nsaspy/daily/2026-08-28.org"),
        section="portfolio",
        slug="2026-08-28",
        title="2026-08-28",
        url="https://nsaspy.starintel.actor/daily/2026-08-28.html",
        human=True,
    )
    page = render.article_page(note, "<p>Workshop note.</p>", GraphModel(), [])

    assert '<p class="portfolio-eyebrow">Notes</p>' in page
    assert "badge--human" not in page
