from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from munshi_synthesizer.schema import OccurrenceRecord

logger = logging.getLogger(__name__)


class ZvecRetriever:
    """Wrapper around zvec-grep (zg) CLI to perform parallel semantic vector lookups."""

    def __init__(self, data_dir: Path, top_k: int = 10):
        self.data_dir = data_dir
        self.top_k = top_k
        self.zg_path = shutil.which("zg")

    def search(self, query: str) -> list[OccurrenceRecord]:
        """Runs zg query --human and converts text outputs to OccurrenceRecords."""
        if not self.zg_path:
            logger.warning("zvec-grep (zg) CLI binary not found in PATH. Skipping vector search.")
            return []

        if not self.data_dir.exists():
            logger.warning("Data directory %s does not exist. Skipping zvec-grep.", self.data_dir)
            return []

        cmd = [
            self.zg_path,
            "query",
            "--human", query,
            "--limit", str(self.top_k),
        ]

        try:
            res = subprocess.run(
                cmd,
                cwd=self.data_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode != 0:
                logger.warning("zvec-grep failed (%d): %s", res.returncode, res.stderr.strip())
                return []

            raw_output = res.stdout.strip()
        except Exception as e:
            logger.warning("Exception running zvec-grep: %s", e)
            return []

        if not raw_output:
            return []

        # zg outputs blocks separated by double newlines or file headers
        blocks = re.split(r"\n(?=[#\w./-]+:\d+:|\n)", raw_output)
        records = []

        for block in blocks:
            text = block.strip()
            if len(text) < 30:
                continue

            # 1. Search anywhere in the block for a referenced markdown file
            match_path = re.search(r"([\w-]+(?:\.md)?)", text)
            if match_path and ".md" in text:
                # If an actual .md filename was matched, strip the extension for doc_id
                matched_file = re.search(r"([\w.-]+\.md)", text)
                doc_id = Path(matched_file.group(1)).stem if matched_file else "zvec_source"
            else:
                doc_id = "zvec_source"

            # 2. Extract explicit page anchor if present in text
            page_match = re.search(r'<span id="page-(\d+)"></span>', text)
            page_num = int(page_match.group(1)) if page_match else None

            records.append(
                OccurrenceRecord(
                    doc_id=doc_id,
                    page_num=page_num,
                    context_snippet=text,
                    source_type="zvec_vector",
                )
            )

        return records