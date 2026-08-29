"""Minimal YAML frontmatter for BOT.md / SKILL.md."""

from __future__ import annotations

from typing import Any


class FrontmatterError(ValueError):
    pass


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    raw = text.lstrip("\ufeff")
    if not raw.startswith("---"):
        return {}, text
    lines = raw.splitlines()
    if lines[0].strip() != "---":
        return {}, text
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        raise FrontmatterError("Unclosed frontmatter")
    return parse_simple_yaml("\n".join(lines[1:end])), "\n".join(lines[end + 1 :]).lstrip("\n")


def parse_simple_yaml(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    pending_key: tuple[int, Any, str] | None = None
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        while stack and indent <= stack[-1][0] and stack[-1][0] >= 0:
            stack.pop()
        container = stack[-1][1]
        if stripped.startswith("- "):
            item = _scalar(stripped[2:].strip())
            if pending_key is not None:
                parent_indent, parent, key = pending_key
                if not isinstance(parent.get(key), list):
                    parent[key] = []
                container = parent[key]
                pending_key = None
                stack.append((parent_indent, container))
            if not isinstance(container, list):
                raise FrontmatterError(f"List item without a list: {stripped}")
            container.append(item)
            i += 1
            continue
        if ":" not in stripped:
            raise FrontmatterError(f"Expected key: value: {stripped}")
        key, rest = stripped.split(":", 1)
        key, rest = key.strip(), rest.strip()
        if not isinstance(container, dict):
            raise FrontmatterError(f"Cannot set {key!r} on a list")
        if rest in ("|", ">"):
            block, i = _read_block(lines, i + 1, indent)
            container[key] = " ".join(block.split()) if rest == ">" else block
            pending_key = None
            continue
        if rest == "":
            nxt = _next(lines, i + 1)
            if nxt and nxt[1].startswith("- ") and nxt[0] > indent:
                container[key] = []
                pending_key = (indent, container, key)
            elif nxt and nxt[0] > indent:
                child: dict[str, Any] = {}
                container[key] = child
                stack.append((indent, child))
                pending_key = None
            else:
                container[key] = ""
                pending_key = None
        else:
            container[key] = _scalar(rest)
            pending_key = None
        i += 1
    return root


def _read_block(lines: list[str], start: int, parent_indent: int) -> tuple[str, int]:
    chunks: list[str] = []
    i = start
    while i < len(lines):
        raw = lines[i]
        if not raw.strip():
            chunks.append("")
            i += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent <= parent_indent:
            break
        chunks.append(raw.strip())
        i += 1
    return "\n".join(chunks).strip(), i


def _next(lines: list[str], start: int) -> tuple[int, str] | None:
    for raw in lines[start:]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        return len(raw) - len(raw.lstrip(" ")), raw.strip()
    return None


def _scalar(value: str) -> Any:
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_scalar(p.strip().strip("'\"")) for p in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def as_str_tuple(value: Any) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        return tuple(p for p in value.replace(",", " ").split() if p)
    if isinstance(value, list):
        return tuple(str(v) for v in value)
    return (str(value),)
