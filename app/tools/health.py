import re

from app.tools.gcs_io import list_wiki_files, read_wiki_file

_SKIP_FILES = {"index.md", "log.md", "schema.md", "gaps.md", "schema_proposals.md"}


def compute_wiki_health() -> str:
    """Computes a quantitative health report for the wiki.

    Scans all pages for frontmatter metrics and returns a markdown report
    with totals, averages, and an overall health score (0.0-1.0).
    """
    files = list_wiki_files()
    if not files:
        return "Wiki is empty — no pages found."

    total = 0
    stubs = 0
    contested = 0
    confidences: list[float] = []

    for fname in files:
        if (
            fname in _SKIP_FILES
            or fname.startswith("sources/")
            or fname.startswith("raw_data/")
        ):
            continue
        total += 1
        content = read_wiki_file(fname)
        if not content:
            continue

        fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not fm_match:
            continue
        fm = fm_match.group(1)

        if re.search(r"status:\s*stub", fm):
            stubs += 1
        if re.search(r"contested:\s*true", fm):
            contested += 1

        conf_match = re.search(r"confidence:\s*([0-9.]+)", fm)
        if conf_match:
            try:
                confidences.append(float(conf_match.group(1)))
            except ValueError:
                pass

    avg_confidence = (
        round(sum(confidences) / len(confidences), 2) if confidences else 0.0
    )

    # Health score: weighted combination of stub ratio, confidence, and contested ratio
    stub_score = 1.0 - (stubs / max(total, 1))
    contested_score = 1.0 - (contested / max(total, 1))
    health_score = round(
        stub_score * 0.4 + avg_confidence * 0.4 + contested_score * 0.2, 2
    )

    status = (
        "> Wiki is healthy."
        if health_score >= 0.8
        else "> Wiki needs attention — review stubs and contested pages."
    )

    return f"""## Wiki Health Report

| Metric | Value |
|--------|-------|
| Total knowledge pages | {total} |
| Stub pages (need content) | {stubs} |
| Contested pages (contradictions) | {contested} |
| Pages with confidence scores | {len(confidences)} |
| Average confidence | {avg_confidence} |
| **Health score** | **{health_score} / 1.0** |

{status}
"""
