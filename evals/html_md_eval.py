#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "beautifulsoup4>=4.14.0",
#   "markdownify>=1.2.0",
# ]
# ///

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def project_root() -> Path:
    return Path(os.environ.get("IMPROVE_PROJECT_ROOT", Path.cwd())).resolve()


sys.path.insert(0, str(project_root()))

from html_to_md import build_context, generate_toc_markdown


def summary_path() -> Path:
    configured = os.environ.get("IMPROVE_SUMMARY_PATH")
    if configured:
        return Path(configured)
    return project_root() / "improvement" / "summaries" / "latest.json"


def collect_markdown_files(markdown_dir: Path) -> list[Path]:
    return sorted(markdown_dir.rglob("*.md"))


def extract_links(text: str) -> list[str]:
    return re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)


def extract_markdown_links(text: str) -> list[tuple[str, str]]:
    return re.findall(r"\[([^\]]*)\]\(([^)]+)\)", text)


def extract_image_links(text: str) -> list[str]:
    return re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)


def find_unlabeled_opening_fences(text: str) -> bool:
    fence_pattern = re.compile(r"^```([A-Za-z0-9_+-]*)\s*$", re.M)
    open_fence = False
    unlabeled = False
    for match in fence_pattern.finditer(text):
        lang = match.group(1)
        if not open_fence:
            if not lang:
                unlabeled = True
            open_fence = True
        else:
            open_fence = False
    return unlabeled


def find_empty_fenced_code_blocks(text: str) -> bool:
    return re.search(r"(?ms)^```[A-Za-z0-9_+-]*\s*\n\s*\n```$", text) is not None


def extract_fenced_code_blocks(text: str) -> list[tuple[str, str]]:
    matches = re.findall(r"(?ms)^```([A-Za-z0-9_+-]*)\s*\n(.*?)\n```$", text)
    return [(lang, body) for lang, body in matches]


def extract_caption_title_lines(text: str) -> list[str]:
    matches: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^\*\*(Table|Figure|Example):\s+\S.*\*\*$", stripped):
            matches.append(stripped)
    return matches


def looks_json_like(text: str) -> bool:
    key_value_count = len(re.findall(r'(?m)^\s*"[^"\n]+"\s*:', text))
    if re.search(r'^\s*[\{\[]', text) and re.search(r'"\w[^"\n]*"\s*:', text, re.M):
        return True
    if key_value_count >= 2:
        return True
    if key_value_count >= 1 and re.search(r'(?m)^\s*[}\]],?\s*$', text):
        return True
    return False


def looks_cpp_like(text: str) -> bool:
    if re.search(r"(^|\n)\s*(typedef|struct\b|class\b|enum\b|namespace\b|template\s*<|#include\b)", text):
        return True
    if re.search(r"(^|\n)\s*(?:u?int\d+_t|size_t|ssize_t|char|bool|void|float|double|long|short)\b", text):
        return True
    if re.search(r"(^|\n)\s*[A-Za-z_]\w*(?:::\w+)*\s+\(\s*\*+\s*[A-Za-z_]\w*\s*\)\s*\([^)]*\)\s*;?", text):
        return True
    if re.search(
        r"(^|\n)\s*(?:const\s+)?(?:unsigned\s+|signed\s+)?(?:void|bool|char|int|float|double|long|short|size_t|ssize_t|u?int\d+_t|[A-Za-z_]\w*(?:::\w+)*)"
        r"(?:\s+const)?(?:\s*[\*&]+)?\s+[A-Za-z_]\w*\s*\([^)]*\)\s*;?",
        text,
    ):
        return True
    return False


def evaluate() -> dict[str, object]:
    root = project_root()
    markdown_dir = root / "markdown"

    checks: list[dict[str, object]] = []
    failures = 0

    def check(name: str, passed: bool, detail: str) -> None:
        nonlocal failures
        if not passed:
            failures += 1
        checks.append({"name": name, "passed": passed, "detail": detail})

    markdown_files = collect_markdown_files(markdown_dir)
    check(
        "markdown_exists",
        markdown_dir.exists(),
        f"markdown dir: {markdown_dir}",
    )
    check(
        "markdown_has_files",
        len(markdown_files) > 0,
        f"markdown files: {len(markdown_files)}",
    )

    check(
        "toc_md_exists",
        (markdown_dir / "toc.md").exists(),
        f"toc exists: {(markdown_dir / 'toc.md').exists()}",
    )
    check(
        "index_md_is_not_generated",
        not (markdown_dir / "index.md").exists(),
        f"index exists: {(markdown_dir / 'index.md').exists()}",
    )

    nested_markdown = [
        str(path.relative_to(root))
        for path in markdown_files
        if path.parent != markdown_dir
    ]
    check(
        "markdown_is_flat",
        not nested_markdown,
        f"nested markdown files: {nested_markdown[:10]}",
    )

    non_lowercase_markdown = [
        str(path.relative_to(root))
        for path in markdown_files
        if path.name != path.name.lower()
    ]
    check(
        "markdown_filenames_are_lowercase",
        not non_lowercase_markdown,
        f"non-lowercase markdown files: {non_lowercase_markdown[:10]}",
    )

    bad_html_links: list[str] = []
    missing_local_targets: list[str] = []
    unlabeled_code_fences: list[str] = []
    non_lowercase_md_links: list[str] = []
    raw_xref_fragments: list[str] = []
    duplicate_structural_anchors: list[str] = []
    empty_code_fence_files: list[str] = []
    suspicious_text_fences: list[str] = []
    title_heading_lines: list[str] = []
    non_bold_title_lines: list[str] = []
    malformed_title_lines: list[str] = []
    bold_title_lines: list[str] = []
    legacy_note_formatting: list[str] = []
    faq_heading_issues: list[str] = []
    raw_html_anchor_files: list[str] = []
    headings_with_html_anchors: list[str] = []
    explicit_heading_anchor_lines: list[str] = []
    non_slug_fragments: list[str] = []
    quoted_heading_link_labels: list[str] = []
    autonumbered_headings: list[str] = []
    autonumbered_titles: list[str] = []
    image_links_not_in_images: list[str] = []
    missing_image_targets: list[str] = []
    toc_format_issues: list[str] = []
    toc_missing_targets: list[str] = []
    toc_nbsp_artifacts: list[str] = []
    toc_parent_indent_issues: list[str] = []
    toc_autonumber_indent_diff: list[str] = []
    split_word_cells: list[str] = []
    on_page_links: list[str] = []
    adjacent_code_artifacts: list[str] = []
    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        if path.name == "toc.md":
            bad_toc_lines: list[str] = []
            for line in text.splitlines():
                if not line.strip():
                    continue
                if not re.match(r"^\s*-\s+\[.+\]\([^)]+\)\s*$", line):
                    bad_toc_lines.append(line)
                if "__160" in line:
                    toc_nbsp_artifacts.append(line)
            if bad_toc_lines:
                toc_format_issues.append(str(path.relative_to(root)))
        if re.search(r"(?m)^\| [a-z] [a-z]\w", text):
            split_word_cells.append(str(path.relative_to(root)))
        if re.search(r"\[.*? on page \d+\]", text):
            on_page_links.append(str(path.relative_to(root)))
        if re.search(r"[a-zA-Z0-9]``[a-zA-Z]", text):
            adjacent_code_artifacts.append(str(path.relative_to(root)))
        if find_unlabeled_opening_fences(text):
            unlabeled_code_fences.append(str(path.relative_to(root)))
        if find_empty_fenced_code_blocks(text):
            empty_code_fence_files.append(str(path.relative_to(root)))
        if '<a id="' in text:
            raw_html_anchor_files.append(str(path.relative_to(root)))
        if re.search(r"(?m)^#{1,6}\s+\d+(?:\.\d+)*\s+", text):
            autonumbered_headings.append(str(path.relative_to(root)))
        if re.search(r"(?m)^#####\s+(?:Table|Figure|Example)\s+\d+(?:\.\d+)*\b", text):
            autonumbered_titles.append(str(path.relative_to(root)))
        for lang, body in extract_fenced_code_blocks(text):
            stripped_body = body.strip()
            if lang != "text" or not stripped_body:
                continue
            if looks_json_like(stripped_body):
                suspicious_text_fences.append(f"{path.relative_to(root)} -> json-like")
            elif looks_cpp_like(stripped_body):
                suspicious_text_fences.append(f"{path.relative_to(root)} -> cpp-like")
        for image_link in extract_image_links(text):
            target = image_link.split("#", 1)[0].strip()
            if not target:
                continue
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not target.startswith("images/"):
                image_links_not_in_images.append(f"{path.relative_to(root)} -> {image_link}")
            target_path = (path.parent / target).resolve()
            if not target_path.exists():
                missing_image_targets.append(f"{path.relative_to(root)} -> {image_link}")
        if re.search(r"(?m)^#{1,6}\s+.*<a id=", text):
            headings_with_html_anchors.append(str(path.relative_to(root)))
        if re.search(r'(?m)^(?:<a id="[^"]+"></a>\s*)+$', text):
            explicit_heading_anchor_lines.append(str(path.relative_to(root)))
        if re.search(r'<a id="\d+"></a><a id="\d+_(?:Body|TableTitle|TableHead)_\d+"></a>', text):
            duplicate_structural_anchors.append(str(path.relative_to(root)))
        if re.search(r'<a id="\d+"></a><a id="\d+__\dHead_\d+"></a>', text):
            duplicate_structural_anchors.append(str(path.relative_to(root)))
        for line in text.splitlines():
            stripped = line.strip()
            if re.match(r"^#{1,6}\s+(Table|Figure|Example):\s+\S", stripped):
                title_heading_lines.append(f"{path.relative_to(root)} -> {stripped}")
            if re.match(r"^(Table|Figure|Example):\s+\S", stripped):
                non_bold_title_lines.append(f"{path.relative_to(root)} -> {stripped}")
            if re.match(r"^\*\*(Table|Figure|Example)(?!:\s)", stripped):
                malformed_title_lines.append(f"{path.relative_to(root)} -> {stripped}")
            elif re.match(r"^\*\*(Table|Figure|Example):(?=\S)", stripped):
                malformed_title_lines.append(f"{path.relative_to(root)} -> {stripped}")
            elif re.match(r"^\*\*(Table|Figure|Example):\s+\S", stripped) and not re.match(
                r"^\*\*(Table|Figure|Example):\s+\S.*\*\*$",
                stripped,
            ):
                malformed_title_lines.append(f"{path.relative_to(root)} -> {stripped}")
        bold_title_lines.extend(f"{path.relative_to(root)} -> {line}" for line in extract_caption_title_lines(text))
        if re.search(r"^\*\*(?:Note|Warning|Tip):\*\*|^(?:Note|Warning|Tip):\s+\S", text, re.M):
            legacy_note_formatting.append(str(path.relative_to(root)))
        if "faq" in path.stem:
            first_heading = re.search(r"(?m)^(#{1,6})\s+", text)
            if not first_heading or first_heading.group(1) != "#":
                faq_heading_issues.append(str(path.relative_to(root)))
        for label, link in extract_markdown_links(text):
            if ("#" in link or link.endswith(".md")) and re.fullmatch(r'[“"][^”"]+[”"]', label.strip()):
                quoted_heading_link_labels.append(f"{path.relative_to(root)} -> [{label}]({link})")
        for link in extract_links(text):
            if "#XREF_" in link or "#xref" in link.lower():
                raw_xref_fragments.append(f"{path.relative_to(root)} -> {link}")
            if "#" in link:
                target, fragment = link.split("#", 1)
                if not target or target.endswith(".md"):
                    if fragment and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", fragment):
                        non_slug_fragments.append(f"{path.relative_to(root)} -> {link}")
            target = link.split("#", 1)[0].strip()
            if not target:
                continue
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if target.endswith((".htm", ".html")):
                bad_html_links.append(f"{path.relative_to(root)} -> {link}")
                continue
            if target.endswith(".md") and target != target.lower():
                non_lowercase_md_links.append(f"{path.relative_to(root)} -> {link}")

            target_path = (path.parent / target).resolve()
            if target.endswith(".md") and not target_path.exists():
                missing_local_targets.append(f"{path.relative_to(root)} -> {link}")
                if path.name == "toc.md":
                    toc_missing_targets.append(f"{path.relative_to(root)} -> {link}")

    check(
        "html_links_rewritten",
        not bad_html_links,
        f"bad html links: {bad_html_links[:10]}",
    )
    check(
        "markdown_targets_exist",
        not missing_local_targets,
        f"missing local markdown targets: {missing_local_targets[:10]}",
    )
    check(
        "markdown_links_are_lowercase",
        not non_lowercase_md_links,
        f"non-lowercase markdown links: {non_lowercase_md_links[:10]}",
    )
    check(
        "toc_uses_markdown_bullets",
        not toc_format_issues,
        f"toc formatting issues: {toc_format_issues[:10]}",
    )
    check(
        "toc_links_resolve",
        not toc_missing_targets,
        f"toc missing targets: {toc_missing_targets[:10]}",
    )
    toc_source = root / "cleaned_html" / "Basic HTML" / "index.html"
    toc_output = markdown_dir / "toc.md"
    if toc_source.exists() and toc_output.exists():
        context = build_context(root / "cleaned_html", markdown_dir)
        expected_toc = generate_toc_markdown(toc_source, context)
        actual_toc = toc_output.read_text(encoding="utf-8")
        if expected_toc != actual_toc:
            expected_lines = expected_toc.splitlines()
            actual_lines = actual_toc.splitlines()
            for index, (expected, actual) in enumerate(zip(expected_lines, actual_lines), start=1):
                if expected != actual:
                    toc_autonumber_indent_diff.append(
                        f"line {index}: expected {expected!r} got {actual!r}"
                    )
                    break
            if len(expected_lines) != len(actual_lines):
                toc_autonumber_indent_diff.append(
                    f"line count: expected {len(expected_lines)} got {len(actual_lines)}"
                )
        for index, expected in enumerate(expected_toc.splitlines(), start=1):
            if expected.startswith("- "):
                actual = actual_toc.splitlines()[index - 1] if index - 1 < len(actual_toc.splitlines()) else ""
                if actual.startswith(" "):
                    toc_parent_indent_issues.append(f"line {index}: {actual}")
    check(
        "toc_has_no_nbsp_artifacts",
        not toc_nbsp_artifacts,
        f"toc __160 artifacts: {toc_nbsp_artifacts[:10]}",
    )
    check(
        "toc_parent_entries_are_flush_left",
        not toc_parent_indent_issues,
        f"indented parent toc entries: {toc_parent_indent_issues[:10]}",
    )
    check(
        "toc_indent_uses_autonumbering",
        not toc_autonumber_indent_diff,
        f"toc autonumber indent differences: {toc_autonumber_indent_diff[:5]}",
    )
    check(
        "xref_fragments_are_rewritten",
        not raw_xref_fragments,
        f"raw xref fragments: {raw_xref_fragments[:10]}",
    )
    check(
        "code_fences_have_language_ids",
        not unlabeled_code_fences,
        f"unlabeled code fences: {unlabeled_code_fences[:10]}",
    )
    check(
        "code_fences_are_not_empty",
        not empty_code_fence_files,
        f"empty fenced code blocks: {empty_code_fence_files[:10]}",
    )
    check(
        "markdown_contains_no_raw_html_anchor_tags",
        not raw_html_anchor_files,
        f"markdown files with raw html anchors: {raw_html_anchor_files[:10]}",
    )
    check(
        "image_links_use_images_folder",
        not image_links_not_in_images,
        f"image links not in images folder: {image_links_not_in_images[:10]}",
    )
    check(
        "image_targets_exist",
        not missing_image_targets,
        f"missing image targets: {missing_image_targets[:10]}",
    )
    check(
        "text_code_fences_are_not_obviously_misclassified",
        not suspicious_text_fences,
        f"suspicious text fences: {suspicious_text_fences[:10]}",
    )
    check(
        "duplicate_structural_anchors_removed",
        not duplicate_structural_anchors,
        f"duplicate structural anchors: {duplicate_structural_anchors[:10]}",
    )
    check(
        "headings_do_not_embed_html_anchors",
        not headings_with_html_anchors,
        f"headings with html anchors: {headings_with_html_anchors[:10]}",
    )
    check(
        "markdown_does_not_emit_standalone_anchor_lines",
        not explicit_heading_anchor_lines,
        f"standalone anchor lines: {explicit_heading_anchor_lines[:10]}",
    )
    check(
        "heading_links_use_slug_fragments",
        not non_slug_fragments,
        f"non-slug fragments: {non_slug_fragments[:10]}",
    )
    check(
        "heading_link_labels_are_not_quoted",
        not quoted_heading_link_labels,
        f"quoted heading link labels: {quoted_heading_link_labels[:10]}",
    )
    check(
        "headings_do_not_use_autonumbering",
        not autonumbered_headings,
        f"autonumbered headings: {autonumbered_headings[:10]}",
    )
    check(
        "table_figure_example_titles_do_not_use_autonumbering",
        not autonumbered_titles,
        f"autonumbered table/figure/example titles: {autonumbered_titles[:10]}",
    )
    check(
        "table_figure_example_titles_are_not_headings",
        not title_heading_lines,
        f"title heading lines: {title_heading_lines[:10]}",
    )
    check(
        "table_figure_example_titles_are_bold",
        not non_bold_title_lines and bool(bold_title_lines),
        f"non-bold title lines: {non_bold_title_lines[:10]}; bold title samples: {bold_title_lines[:3]}",
    )
    check(
        "table_figure_example_titles_use_colon_space_format",
        not malformed_title_lines,
        f"malformed title lines: {malformed_title_lines[:10]}",
    )
    check(
        "admonitions_use_callout_format",
        not legacy_note_formatting,
        f"legacy note/warning/tip formatting: {legacy_note_formatting[:10]}",
    )
    check(
        "faq_pages_use_h1",
        not faq_heading_issues,
        f"faq heading issues: {faq_heading_issues[:10]}",
    )
    check(
        "table_cells_have_no_split_words",
        not split_word_cells,
        f"table cells with split words: {split_word_cells[:10]}",
    )
    check(
        "links_do_not_contain_on_page_references",
        not on_page_links,
        f"files with 'on page N' in links: {on_page_links[:10]}",
    )
    check(
        "no_adjacent_code_span_artifacts",
        not adjacent_code_artifacts,
        f"files with adjacent code span artifacts: {adjacent_code_artifacts[:10]}",
    )

    passed = sum(1 for item in checks if item["passed"])
    total = len(checks)
    score = passed / total if total else 0.0

    return {
        "all_passed": failures == 0,
        "score": score,
        "metric_name": "score",
        "metric_direction": "higher",
        "passed": passed,
        "failed": failures,
        "total": total,
        "details": checks,
    }


def main() -> None:
    payload = evaluate()
    path = summary_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
