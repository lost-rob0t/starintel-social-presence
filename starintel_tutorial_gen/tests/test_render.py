from starintel_tutorial_gen import (
    TutorialPlan,
    TutorialSource,
    TutorialStep,
    render_blog,
    render_presentation,
    render_script,
)


def plan() -> TutorialPlan:
    source = TutorialSource("lost-rob0t/starintel-server", "abc123", "README.md", "Server starts with X")
    return TutorialPlan(
        title="Start StarIntel",
        slug="start-starintel",
        description="Small verified tutorial",
        sources=(source,),
        steps=(
            TutorialStep(
                "Start the server",
                "Run the documented command.",
                (source.reference,),
                "starintel start",
                "server ready",
            ),
        ),
    )


def test_all_outputs_preserve_source_reference() -> None:
    ref = plan().sources[0].reference
    for output in (render_blog(plan()), render_script(plan()), render_presentation(plan())):
        assert ref in output
        assert "starintel start" in output
