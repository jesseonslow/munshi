"""Pipeline step: enrich document metadata via authoritative DOI lookup (CrossRef)."""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from munshi_docproc.schema import DocumentRecord, MetadataSource

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = 15
_USER_AGENT = "munshi-docproc/0.2.0 (historical document processing; mailto:admin@mbras.org.my)"


def _http_get_json(url: str) -> dict | None:
    """Make a GET request and parse JSON response. Returns None on failure."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as e:
        logger.debug("CrossRef request failed for %s: %s", url, e)
        return None


def enrich_metadata_web(document: DocumentRecord) -> DocumentRecord:
    """Enrich document metadata strictly using CrossRef when a valid DOI is detected.
    
    Fuzzy search engines (OpenLibrary, DuckDuckGo) are deliberately excluded to prevent 
    false-positive bibliographic collisions in 19th/20th-century historical records.
    """
    if not document.doi:
        return document

    doi = document.doi.strip().rstrip(".")
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
    data = _http_get_json(url)

    if not data or "message" not in data:
        logger.debug("CrossRef: no result for DOI %s", doi)
        return document

    msg = data["message"]
    logger.info("CrossRef: found record for DOI %s", doi)

    # Title
    titles = msg.get("title", [])
    if titles and not document.title:
        document.title = titles[0]
        document.metadata_sources.append(
            MetadataSource(field="title", source="crossref", confidence=1.0, raw_value=titles[0])
        )

    # Authors
    authors = msg.get("author", [])
    if authors and not document.author:
        author_parts = []
        for a in authors:
            given = a.get("given", "")
            family = a.get("family", "")
            if given and family:
                author_parts.append(f"{given} {family}")
            elif family:
                author_parts.append(family)
        if author_parts:
            author_str = "; ".join(author_parts)
            document.author = author_str
            document.metadata_sources.append(
                MetadataSource(field="author", source="crossref", confidence=1.0, raw_value=author_str)
            )

    # Publication Year
    date_parts = msg.get("published-print", msg.get("published-online", msg.get("issued", {})))
    if date_parts and not document.year:
        parts = date_parts.get("date-parts", [[]])
        if parts and parts[0] and len(parts[0]) >= 1:
            try:
                year = int(parts[0][0])
                document.year = year
                document.metadata_sources.append(
                    MetadataSource(field="year", source="crossref", confidence=1.0, raw_value=str(year))
                )
            except (ValueError, TypeError):
                pass

    # Journal / Container Title
    container = msg.get("container-title", [])
    if container and not document.publication:
        document.publication = container[0]
        document.metadata_sources.append(
            MetadataSource(field="publication", source="crossref", confidence=1.0, raw_value=container[0])
        )

    # Volume & Issue
    if msg.get("volume") and not document.volume:
        document.volume = msg["volume"]
        document.metadata_sources.append(
            MetadataSource(field="volume", source="crossref", confidence=1.0, raw_value=msg["volume"])
        )
    if msg.get("issue") and not document.issue:
        document.issue = msg["issue"]
        document.metadata_sources.append(
            MetadataSource(field="issue", source="crossref", confidence=1.0, raw_value=msg["issue"])
        )

    # Page range
    if msg.get("page") and not document.page_range_label:
        document.page_range_label = msg["page"]
        document.metadata_sources.append(
            MetadataSource(field="page_range_label", source="crossref", confidence=1.0, raw_value=msg["page"])
        )

    # ISSN & ISBN
    issns = msg.get("ISSN", [])
    if issns and not document.issn:
        document.issn = issns[0]
        document.metadata_sources.append(
            MetadataSource(field="issn", source="crossref", confidence=1.0, raw_value=issns[0])
        )
    isbns = msg.get("ISBN", [])
    if isbns and not document.isbn:
        document.isbn = isbns[0]
        document.metadata_sources.append(
            MetadataSource(field="isbn", source="crossref", confidence=1.0, raw_value=isbns[0])
        )

    # URL
    if msg.get("URL") and not document.url:
        document.url = msg["URL"]
        document.metadata_sources.append(
            MetadataSource(field="url", source="crossref", confidence=1.0, raw_value=msg["URL"])
        )

    return document