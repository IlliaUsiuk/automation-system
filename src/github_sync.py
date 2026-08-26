"""Pull-based sync: given a GitHub repo URL, fetch README.md/dashboard/ROI.md/
dashboard/SUMMARY.md (the files stage-0-supplax actually generates with a
known structure) and parse them into the fields automation_new/
api_sync_automation already know how to fill. dashboard/ROI.md and
dashboard/SUMMARY.md are a generated sync contract, not the automation's real
ROI/functionality writeups (those live at docs/roi_explained.md and
docs/functions.md instead) - see automation-portfolio-sync's SKILL.md.
No dependency added - stdlib urllib, same approach already used for the
ClickUp checks earlier in this project."""
import json
import os
import re
import urllib.error
import urllib.request

REPO_URL_RE = re.compile(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")


def parse_repo_url(url):
    """Returns (owner, repo) or None if this doesn't look like a GitHub repo URL."""
    m = REPO_URL_RE.match(url.strip())
    return (m.group(1), m.group(2)) if m else None


def _github_headers():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "supplax-automation-portfolio"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def default_branch(owner, repo):
    """Tries api.github.com first (gives the real default branch name in one
    call), but that endpoint is unauthenticated-rate-limited and has been
    observed to hang/timeout in this environment even well under the rate
    limit - raw.githubusercontent.com has not. Falls back to guessing
    main/master directly against the raw host, which is what every fetch
    call needs to work anyway."""
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{owner}/{repo}", headers=_github_headers())
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("default_branch") or "main"
    except Exception:
        pass

    for branch in ("main", "master"):
        req = urllib.request.Request(
            f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md",
            headers=_github_headers())
        try:
            with urllib.request.urlopen(req, timeout=10):
                return branch
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
    raise RuntimeError(f"could not resolve a branch for {owner}/{repo} (tried main, master)")


def fetch_raw_file(owner, repo, path, branch):
    """Returns the file's text content, or None if it doesn't exist (a repo
    bootstrapped by an older stage-0-supplax run, or one that isn't an
    automation, may not have dashboard/ROI.md - that's a real case, not an
    error)."""
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    req = urllib.request.Request(url, headers=_github_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def fetch_latest_commit(owner, repo, branch):
    """Returns {"message": <subject line>, "date": <ISO 8601 string>} for the
    latest commit on `branch`, or None. Deliberately raw - the caller doesn't
    interpret the message into a "stage"; a commit's type/wording doesn't
    reliably map to lifecycle phase (a `fix:` commit happens as often on
    day one as a year into production), so this is shown as a plain fact,
    not a guess dressed up as one."""
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?sha={branch}&per_page=1"
    req = urllib.request.Request(url, headers=_github_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    if not data:
        return None
    commit = data[0]["commit"]
    subject = commit["message"].splitlines()[0].strip()
    date = commit.get("author", {}).get("date") or commit.get("committer", {}).get("date")
    return {"message": subject, "date": date}


def parse_readme(text):
    """First '# Title' line as the name, first real paragraph after it as the
    one-liner - matches how stage-0-supplax's README.md template is shaped."""
    if not text:
        return None, None
    title = None
    one_liner = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if title is None:
            if stripped.startswith("# "):
                title = stripped[2:].strip()
            continue
        if not stripped.startswith("#") and not stripped.startswith("<!--"):
            one_liner = stripped
            break
    return title, one_liner


_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def parse_markdown_sections(text):
    """Splits any '## Header' -> body markdown file into a dict, with HTML
    guidance comments stripped so an unfilled section reads as empty rather
    than as its own template instructions. Shared by dashboard/ROI.md and
    dashboard/SUMMARY.md - both use the same '## Heading' convention."""
    if not text:
        return {}
    headers = list(_HEADER_RE.finditer(text))
    sections = {}
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = _HTML_COMMENT_RE.sub("", text[start:end]).strip()
        sections[m.group(1).strip()] = body
    return sections


# Back-compat alias - dashboard/ROI.md parsing specifically.
parse_roi_md = parse_markdown_sections


_BULLET_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*$", re.MULTILINE)


def _bullet_items(body):
    """'- Sales' / '- other-slug: shares a webhook' style lines -> list of
    raw strings (one per bullet), used for dashboard/SUMMARY.md's Departments
    and Connections sections."""
    return [m.group(1).strip() for m in _BULLET_RE.finditer(body or "")]


def summary_fields_from_sections(sections):
    """Maps dashboard/SUMMARY.md's sections to Automation's columns. This file
    exists specifically because README.md's prose is unreliable to scrape for
    an actual functional description - SUMMARY.md is a purpose-built,
    generated contract (automation-portfolio-sync regenerates it from the
    project's real docs/functions.md and docs/roi_explained.md each sync), so
    every field here is a fixed header, not best-effort guesswork."""
    name = sections.get("Name") or None
    one_liner = sections.get("One-liner") or None
    description = sections.get("What it does") or None
    departments = _bullet_items(sections.get("Departments", ""))
    status_raw = (sections.get("Status") or "").strip().lower()
    connections = []
    for item in _bullet_items(sections.get("Connections", "")):
        slug, _, rel = item.partition(":")
        connections.append({"slug": slug.strip(), "relationship_type": rel.strip() or None})
    return {
        "name": name,
        "one_liner": one_liner,
        "description": description,
        "departments": departments,
        "status": status_raw or None,
        "connections": connections,
        "pages": parse_pages_section(sections.get("Pages", "")),
        "current_stage_override": sections.get("Current Stage") or None,
    }


_SUBHEADER_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)


def parse_pages_section(body):
    """dashboard/SUMMARY.md's '## Pages' section holds one '### Page Name'
    sub-header per screen, body = its plain-language description. Returns an
    ordered list of {name, description} - order matters, it's shown in the
    same order on the dashboard."""
    if not body:
        return []
    headers = list(_SUBHEADER_RE.finditer(body))
    pages = []
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(body)
        desc = _HTML_COMMENT_RE.sub("", body[start:end]).strip()
        pages.append({"name": m.group(1).strip(), "description": desc})
    return pages


_BACKLOG_FIELD_RE = re.compile(r"^(Scope|Found|Changed|Rejected):\s*(.*)$")


def parse_backlog_md(text, limit=5):
    """Parses backlog/BACKLOG.md entries - each '## ...' heading is one
    round's entry (see stage-0-supplax's references/backlog-format.md), body
    holds Scope/Found/Changed/Rejected lines. Deliberately doesn't assume a
    fixed grammar for the heading text itself ("Round N of M — mode" in the
    spec, but real output has varied) - whatever's after '## ' is the label
    verbatim. Returns up to the last `limit` entries, in file order (oldest
    first) - callers show them newest-first themselves."""
    if not text:
        return []
    sections = parse_markdown_sections(text)
    entries = []
    for label, body in sections.items():
        fields = {"Scope": "", "Found": "", "Changed": "", "Rejected": ""}
        current = None
        for line in body.splitlines():
            field_match = _BACKLOG_FIELD_RE.match(line.strip())
            if field_match:
                current = field_match.group(1)
                fields[current] = field_match.group(2).strip()
            elif current and line.strip():
                fields[current] = (fields[current] + " " + line.strip()).strip()
        if not any(fields.values()):
            continue  # not an entry - e.g. a stray '## Something Else' heading
        entries.append({
            "round_label": label,
            "found": fields["Found"] or fields["Scope"],
            "changed": fields["Changed"] or None,
            "rejected": fields["Rejected"] or None,
        })
    return entries[-limit:] if limit else entries


_TODO_ITEM_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s+(.+?)\s*$", re.MULTILINE)


def parse_todo_md(text):
    """Parses TODO.md's plain '- [ ]'/'- [x]' checklist lines - the file
    stage-0-supplax already creates per project (empty at bootstrap, filled
    from real work as it happens). No fixed sections here, unlike
    dashboard/ROI.md and dashboard/SUMMARY.md - it's just a flat list, in
    file order. Returns a list of
    {text, done}, in the order they appear in the file."""
    if not text:
        return []
    return [{"text": m.group(2).strip(), "done": m.group(1).lower() == "x"}
            for m in _TODO_ITEM_RE.finditer(text)]


def roi_fields_from_sections(sections):
    """Maps dashboard/ROI.md's section names to ROIEntry's columns. Confidence is read
    from the template's own "Estimated" / "Measured (as of ...)" convention -
    see stage-0-supplax's templates/dashboard/ROI.md."""
    confidence_text = sections.get("Confidence", "")
    confidence = "measured" if confidence_text.lower().startswith("measured") else "estimated"
    measured_value = None
    if confidence == "measured":
        for line in sections.get("Actual Results", "").splitlines():
            if line.strip():
                measured_value = line.strip()
                break
    presentation_url = None
    for line in sections.get("Presentation", "").splitlines():
        if line.strip():
            presentation_url = line.strip()
            break
    return {
        "hypothesis": sections.get("Hypothesis") or None,
        "metric_description": sections.get("How We'll Measure It") or None,
        "confidence": confidence,
        "measured_value": measured_value,
        "presentation_url": presentation_url,
    }
