"""Loader for SCIP (Sourcegraph Code Intelligence Protocol) indexes.

SCIP dumps live outside the git tree, in a per-repo cache directory:
``<bare-repo>/.scip/<sha>.scip`` for a specific commit, with an
``HEAD.scip`` fallback.

The loader returns an :class:`Index` wrapper that exposes per-document
occurrence lookup and per-symbol definition lookup.  Indexes are cached
in-memory keyed by ``(repo_path, sha)``.
"""

import os
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from klaus import scip_pb2  # type: ignore[attr-defined]

_DEFINITION_ROLE: int = scip_pb2.SymbolRole.Definition  # type: ignore[attr-defined]

_CACHE_LOCK = threading.Lock()
_CACHE: "OrderedDict[Tuple[str, str], Optional[Index]]" = OrderedDict()
_CACHE_MAX_ENTRIES = 16


@dataclass(frozen=True)
class Range:
    """Half-open [start, end) range in a document, 0-based."""

    start_line: int
    start_char: int
    end_line: int
    end_char: int

    @classmethod
    def from_proto(cls, raw: List[int]) -> "Range":
        if len(raw) == 4:
            return cls(raw[0], raw[1], raw[2], raw[3])
        if len(raw) == 3:
            return cls(raw[0], raw[1], raw[0], raw[2])
        raise ValueError(f"SCIP range must have 3 or 4 elements, got {len(raw)}")


@dataclass(frozen=True)
class Occurrence:
    range: Range
    symbol: str
    syntax_kind: int
    is_definition: bool


@dataclass(frozen=True)
class Definition:
    """Location of a symbol's definition within the index."""

    relative_path: str
    line: int  # 0-based


class Document:
    """Wrapper around a SCIP ``Document`` with sorted occurrences."""

    def __init__(self, relative_path: str, occurrences: List[Occurrence]):
        self.relative_path = relative_path
        self.occurrences = sorted(
            occurrences,
            key=lambda o: (o.range.start_line, o.range.start_char),
        )

    def occurrences_on_line(self, line: int) -> List[Occurrence]:
        # Linear scan is fine for typical line counts; occurrences are sorted.
        return [o for o in self.occurrences if o.range.start_line == line]


class Index:
    """Parsed SCIP index providing document and symbol lookup."""

    def __init__(self, proto: "scip_pb2.Index"):  # type: ignore[name-defined]
        self._documents: Dict[str, Document] = {}
        self._definitions: Dict[str, Definition] = {}

        for doc in proto.documents:
            occurrences = [
                Occurrence(
                    range=Range.from_proto(list(occ.range)),
                    symbol=occ.symbol,
                    syntax_kind=occ.syntax_kind,
                    is_definition=bool(occ.symbol_roles & _DEFINITION_ROLE),
                )
                for occ in doc.occurrences
            ]
            self._documents[doc.relative_path] = Document(
                doc.relative_path, occurrences
            )
            for occ in occurrences:
                if (
                    occ.is_definition
                    and occ.symbol
                    and occ.symbol not in self._definitions
                ):
                    self._definitions[occ.symbol] = Definition(
                        relative_path=doc.relative_path,
                        line=occ.range.start_line,
                    )

    def get_document(self, relative_path: str) -> Optional[Document]:
        return self._documents.get(relative_path)

    def get_definition(self, symbol: str) -> Optional[Definition]:
        return self._definitions.get(symbol)


def _scip_path_for(repo_path: str, sha: str) -> Optional[str]:
    scip_dir = os.path.join(repo_path, ".scip")
    if not os.path.isdir(scip_dir):
        return None
    candidate = os.path.join(scip_dir, f"{sha}.scip")
    if os.path.isfile(candidate):
        return candidate
    fallback = os.path.join(scip_dir, "HEAD.scip")
    if os.path.isfile(fallback):
        return fallback
    return None


def load_index(repo_path: str, sha: str) -> Optional[Index]:
    """Return the SCIP index for ``sha`` in ``repo_path``, or ``None``.

    Returns ``None`` (cached) when no SCIP dump is available, so callers
    don't probe the filesystem on every request.
    """
    key = (repo_path, sha)
    with _CACHE_LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            return _CACHE[key]

    path = _scip_path_for(repo_path, sha)
    index: Optional[Index]
    if path is None:
        index = None
    else:
        proto = scip_pb2.Index()  # type: ignore[attr-defined]
        with open(path, "rb") as f:
            proto.ParseFromString(f.read())
        index = Index(proto)

    with _CACHE_LOCK:
        _CACHE[key] = index
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_MAX_ENTRIES:
            _CACHE.popitem(last=False)
    return index


def clear_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()
