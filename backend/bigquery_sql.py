"""Safe loading and rendering for the project's reviewed BigQuery SQL files."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Mapping


SQL_DIRECTORY = Path(__file__).resolve().parent / "sql"
SQL_TOKEN_PATTERN = re.compile(r"{{([A-Z_]+)}}")
TABLE_PATH_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._:-]*"
    r"\.[A-Za-z_][A-Za-z0-9_]*"
    r"\.[A-Za-z_][A-Za-z0-9_]*$"
)
DATASET_PATH_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._:-]*"
    r"\.[A-Za-z_][A-Za-z0-9_]*$"
)


@lru_cache(maxsize=8)
def _load_sql(filename: str) -> str:
    """Cache immutable SQL resources instead of reading disk for every job."""
    if Path(filename).name != filename or not filename.endswith(".sql"):
        raise ValueError("Invalid SQL resource name")
    return (SQL_DIRECTORY / filename).read_text(encoding="utf-8")


def render_sql(filename: str, table_identifiers: Mapping[str, str]) -> str:
    """Render table names while keeping every row value as a query parameter.

    BigQuery does not support parameters for identifiers. Restricting both the
    marker names and identifier characters makes this tiny substitution layer
    safe without introducing a general-purpose templating language.
    """
    sql = _load_sql(filename)
    found_tokens = set(SQL_TOKEN_PATTERN.findall(sql))
    supplied_tokens = set(table_identifiers)
    if found_tokens != supplied_tokens:
        raise RuntimeError("BigQuery SQL placeholders do not match their bindings")

    for token, table_path in table_identifiers.items():
        pattern = DATASET_PATH_PATTERN if token.endswith("_DATASET") else TABLE_PATH_PATTERN
        if not pattern.fullmatch(table_path):
            raise ValueError(f"Invalid BigQuery resource identifier for {token}")
        sql = sql.replace("{{" + token + "}}", table_path)

    if SQL_TOKEN_PATTERN.search(sql):
        raise RuntimeError("Unresolved placeholder in BigQuery SQL")
    return sql
