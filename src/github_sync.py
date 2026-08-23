"""Pull-based sync: given a GitHub repo URL, fetch README.md/ROI.md (the files
stage-0-supplax actually generates with a known structure) and parse them into
the fields automation_new/api_sync_automation already know how to fill.
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
    req = urllib.request.Request(f"https://api.github.com/repos/{owner}/{repo}", headers=_github_headers())
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("default_branch", "main")


def fetch_raw_file(owner, repo, path, branch):
    """Returns the file's text content, or None if it doesn't exist (a repo
    bootstrapped by an older stage-0-supplax run, or one that isn't an
    automation, may not have ROI.md - that's a real case, not an error)."""
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


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


_ROI_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def parse_roi_md(text):
    """Splits ROI.md (see stage-0-supplax's templates/ROI.md) into its
    section headers -> body text, with the template's own guidance comments
    stripped out so an unfilled section reads as empty, not as its own
    instructions."""
    if not text:
        return {}
    headers = list(_ROI_HEADER_RE.finditer(text))
    sections = {}
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = _HTML_COMMENT_RE.sub("", text[start:end]).strip()
        sections[m.group(1).strip()] = body
    return sections


def roi_fields_from_sections(sections):
    """Maps ROI.md's section names to ROIEntry's columns. Confidence is read
    from the template's own "Estimated" / "Measured (as of ...)" convention -
    see stage-0-supplax's templates/ROI.md."""
    confidence_text = sections.get("Confidence", "")
    confidence = "measured" if confidence_text.lower().startswith("measured") else "estimated"
    measured_value = None
    if confidence == "measured":
        for line in sections.get("Actual Results", "").splitlines():
            if line.strip():
                measured_value = line.strip()
                break
    return {
        "hypothesis": sections.get("Hypothesis") or None,
        "metric_description": sections.get("How We'll Measure It") or None,
        "confidence": confidence,
        "measured_value": measured_value,
    }
