"""Minimal YAML frontmatter parser for SKILL.md / AGENT.md files.

The Agent Skills spec requires YAML frontmatter. This parser covers the
subset used by the spec (scalars, nested maps, flow/block lists) without
a third-party YAML dependency so the harness stays droppable.
"""

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
        raise FrontmatterError("Unclosed YAML frontmatter")
    yaml_text = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return parse_simple_yaml(yaml_text), body


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
            item = _parse_scalar(stripped[2:].strip())
            if pending_key is not None:
                parent_indent, parent, key = pending_key
                if not isinstance(parent.get(key), list):
                    parent[key] = []
                container = parent[key]
                pending_key = None
                # Stay on the parent indent so sibling `-` items are not popped.
                stack.append((parent_indent, container))
            if not isinstance(container, list):
                raise FrontmatterError(f"List item without a list at: {stripped}")
            container.append(item)
            i += 1
            continue

        if ":" not in stripped:
            raise FrontmatterError(f"Expected key: value, got: {stripped}")
        key, rest = stripped.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        if not isinstance(container, dict):
            raise FrontmatterError(f"Cannot set key {key!r} on a list")
        if rest == "|" or rest == ">":
            block, i = _read_block(lines, i + 1, indent)
            container[key] = " ".join(block.split()) if rest == ">" else block
            pending_key = None
            continue
        if rest == "":
            # Lookahead: nested map, list, or empty
            nxt = _next_content(lines, i + 1)
            if nxt is None:
                container[key] = "" if rest == "" else ""
                pending_key = None
            else:
                nindent, nstripped = nxt
                if nstripped.startswith("- ") and nindent > indent:
                    container[key] = []
                    pending_key = (indent, container, key)
                elif nindent > indent:
                    child: dict[str, Any] = {}
                    container[key] = child
                    stack.append((indent, child))
                    pending_key = None
                else:
                    container[key] = ""
                    pending_key = None
        else:
            container[key] = _parse_scalar(rest)
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
    text = "\n".join(chunks).strip()
    return text, i


def _next_content(lines: list[str], start: int) -> tuple[int, str] | None:
    for raw in lines[start:]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        return indent, raw.strip()
    return None


def _parse_scalar(value: str) -> Any:
    if value in ("null", "~", ""):
        return None
    if value in ("true", "True", "yes"):
        return True
    if value in ("false", "False", "no"):
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        parts = _split_flow(inner)
        return [_parse_scalar(p.strip()) for p in parts]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _split_flow(inner: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    quote = None
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            buf.append(ch)
            continue
        if ch == ",":
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def as_str_list(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(p for p in value.replace(",", " ").split() if p)
    if isinstance(value, list):
        return tuple(str(v) for v in value)
    return (str(value),)


def as_str_map(value: Any) -> dict[str, str]:
    if not value:
        return {}
    if not isinstance(value, dict):
        return {}
    return {str(k): str(v) for k, v in value.items()}
