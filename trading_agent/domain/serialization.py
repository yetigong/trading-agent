"""Serialization helpers for domain dataclasses."""

from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Union, get_args, get_origin


def to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if is_dataclass(obj):
        return {f.name: to_dict(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_dict(v) for v in obj]
    return obj


def _coerce_value(value: Any, field_type: Any) -> Any:
    if value is None:
        return None
    origin = get_origin(field_type)
    if origin is Union:
        args = [a for a in get_args(field_type) if a is not type(None)]
        field_type = args[0] if args else field_type
        origin = get_origin(field_type)
    if origin is list:
        inner = get_args(field_type)[0]
        return [_coerce_value(v, inner) for v in value]
    if is_dataclass(field_type) and isinstance(value, dict):
        return field_type(**{f.name: _coerce_value(value.get(f.name), f.type) for f in fields(field_type)})
    if field_type is datetime and isinstance(value, str):
        return datetime.fromisoformat(value)
    return value
