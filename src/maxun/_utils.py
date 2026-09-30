"""Small internal helpers shared by the SDK modules."""

import dataclasses
import os
import warnings
from typing import Any, Dict, Mapping, Optional, Tuple, Union

_DOCUMENT_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def warn(message: str) -> None:
    """Warn the caller about something that will not behave as they expect."""
    warnings.warn(message, UserWarning, stacklevel=3)


def to_camel(key: str) -> str:
    if "_" not in key:
        return key
    head, *rest = key.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


def to_payload(value: Any, drop_none: bool = True) -> Any:
    """Turn a config dataclass or dict (snake_case or camelCase keys) into a
    camelCase JSON-ready dict, recursively. ``None`` values are dropped."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        value = {f.name: getattr(value, f.name) for f in dataclasses.fields(value)}
    if isinstance(value, Mapping):
        return {
            to_camel(str(k)): to_payload(v, drop_none)
            for k, v in value.items()
            if not (drop_none and v is None)
        }
    if isinstance(value, (list, tuple)):
        return [to_payload(v, drop_none) for v in value]
    return value


def get_field(source: Any, *names: str, default: Any = None) -> Any:
    """Read the first present field from a dataclass or dict, trying each name."""
    for name in names:
        if isinstance(source, Mapping):
            if source.get(name) is not None:
                return source[name]
        elif getattr(source, name, None) is not None:
            return getattr(source, name)
    return default


def document_content_type(file_name: str) -> str:
    ext = os.path.splitext(file_name or "")[1].lower()
    return _DOCUMENT_MIME_TYPES.get(ext, "application/pdf")


def load_document(file: Union[str, "os.PathLike[str]", bytes], file_name: Optional[str]) -> Tuple[str, bytes, str]:
    """Return ``(file_name, bytes, content_type)`` for a path or raw bytes."""
    if isinstance(file, (bytes, bytearray)):
        name = file_name or "document.pdf"
        data = bytes(file)
    else:
        path = os.fspath(file)
        name = file_name or os.path.basename(path)
        with open(path, "rb") as f:
            data = f.read()
    ext = os.path.splitext(name)[1].lower()
    if ext and ext not in _DOCUMENT_MIME_TYPES:
        raise ValueError(
            f'Unsupported document type "{ext}". Supported: PDF, DOCX, XLSX, CSV, JPG, PNG.'
        )
    return name, data, document_content_type(name)


def merge(*dicts: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for d in dicts:
        if d:
            out.update(d)
    return out
