from __future__ import annotations

import copy
import json
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.db import AsyncSessionLocal
from app.redis_client import redis_client

DEFAULT_SERVICE_ID = "default"
POLICY_CACHE_TTL_SECONDS = 5 * 60

DEFAULT_POLICIES: dict[str, dict[str, Any]] = {
    "score_weights": {"0": 0, "1": 20, "2": 45, "3": 70, "4": 90},
    "entropy_bonus": {"threshold_bits": 60, "bonus_points": 10},
    "breach_penalty": {"points": 30},
    "pattern_penalty": {
        "keyboard": 10,
        "repeat": 8,
        "dictionary": 10,
        "date": 6,
        "sequence": 8,
    },
    "risk_thresholds": {
        "critical": [0, 25],
        "high": [26, 50],
        "medium": [51, 70],
        "low": [71, 90],
        "minimal": [91, 100],
    },
    "password_requirements": {
        "min_length": 8,
        "max_length": 128,
        "require_uppercase": False,
        "require_digit": False,
        "require_special": False,
        "require_lowercase": False,
    },
    "breach_cache_ttl": {"seconds": 86400},
}


class PolicyValidationError(ValueError):
    pass


def _copy_default(name: str) -> dict[str, Any]:
    default_value = DEFAULT_POLICIES.get(name)
    if default_value is None:
        raise KeyError(f"Unknown policy: {name}")
    return copy.deepcopy(default_value)


def _normalize_service_id(service_id: str | None) -> str:
    if service_id is None:
        return DEFAULT_SERVICE_ID
    normalized = service_id.strip()
    return normalized or DEFAULT_SERVICE_ID


def _cache_key(service_id: str, name: str) -> str:
    return f"policy:{service_id}:{name}"


def _all_cache_key(service_id: str) -> str:
    return f"policy:{service_id}:ALL"


def _as_policy_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return None
        if isinstance(loaded, dict):
            return loaded

    return None


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_missing_service_id_column(exc: ProgrammingError) -> bool:
    return 'column "service_id" does not exist' in str(exc).lower()


def _ensure_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PolicyValidationError(f"{name} must be an object")
    return value


def validate_policy_value(name: str, value: Any) -> dict[str, Any]:
    data = _ensure_dict(value, name)

    if name == "score_weights":
        expected_keys = ["0", "1", "2", "3", "4"]
        if sorted(data.keys()) != expected_keys:
            raise PolicyValidationError("score_weights must contain keys 0..4")

        cleaned: dict[str, Any] = {}
        for key in expected_keys:
            item = data[key]
            if not _is_int(item) or item < 0 or item > 100:
                raise PolicyValidationError(f"score_weights[{key}] must be an integer in range 0..100")
            cleaned[key] = item
        return cleaned

    if name == "entropy_bonus":
        threshold_bits = data.get("threshold_bits")
        bonus_points = data.get("bonus_points")
        if not _is_int(threshold_bits):
            raise PolicyValidationError("entropy_bonus.threshold_bits must be an integer >= 0")
        if not _is_int(bonus_points):
            raise PolicyValidationError("entropy_bonus.bonus_points must be an integer in range 0..100")
        threshold_bits_int = cast(int, threshold_bits)
        bonus_points_int = cast(int, bonus_points)
        if threshold_bits_int < 0:
            raise PolicyValidationError("entropy_bonus.threshold_bits must be an integer >= 0")
        if bonus_points_int < 0 or bonus_points_int > 100:
            raise PolicyValidationError("entropy_bonus.bonus_points must be an integer in range 0..100")
        return {"threshold_bits": threshold_bits_int, "bonus_points": bonus_points_int}

    if name == "breach_penalty":
        points = data.get("points")
        if not _is_int(points):
            raise PolicyValidationError("breach_penalty.points must be an integer in range 0..100")
        points_int = cast(int, points)
        if points_int < 0 or points_int > 100:
            raise PolicyValidationError("breach_penalty.points must be an integer in range 0..100")
        return {"points": points_int}

    if name == "pattern_penalty":
        keys = ["keyboard", "repeat", "dictionary", "date", "sequence"]
        if sorted(data.keys()) != sorted(keys):
            raise PolicyValidationError("pattern_penalty must contain keyboard, repeat, dictionary, date, and sequence")

        cleaned = {}
        for key in keys:
            points = data.get(key)
            if not _is_int(points):
                raise PolicyValidationError(f"pattern_penalty.{key} must be an integer in range 0..100")
            points_int = cast(int, points)
            if points_int < 0 or points_int > 100:
                raise PolicyValidationError(f"pattern_penalty.{key} must be an integer in range 0..100")
            cleaned[key] = points_int
        return cleaned

    if name == "risk_thresholds":
        labels = ["critical", "high", "medium", "low", "minimal"]
        if sorted(data.keys()) != sorted(labels):
            raise PolicyValidationError("risk_thresholds must contain critical, high, medium, low, and minimal")

        cleaned: dict[str, Any] = {}
        previous_max: int | None = None
        for label in labels:
            current = data[label]
            if (
                not isinstance(current, list)
                or len(current) != 2
                or not _is_int(current[0])
                or not _is_int(current[1])
            ):
                raise PolicyValidationError(f"risk_thresholds.{label} must be [min, max] integer pair")

            current_min = current[0]
            current_max = current[1]
            if current_min > current_max:
                raise PolicyValidationError(f"risk_thresholds.{label} min must be <= max")
            if current_min < 0 or current_max > 100:
                raise PolicyValidationError(f"risk_thresholds.{label} must stay within 0..100")

            if previous_max is None:
                if current_min != 0:
                    raise PolicyValidationError("risk_thresholds must start at 0")
            elif current_min != previous_max + 1:
                raise PolicyValidationError("risk_thresholds ranges must be contiguous with no gaps")

            previous_max = current_max
            cleaned[label] = [current_min, current_max]

        if previous_max != 100:
            raise PolicyValidationError("risk_thresholds must end at 100")

        return cleaned

    if name == "password_requirements":
        bool_keys = [
            "require_uppercase",
            "require_digit",
            "require_special",
            "require_lowercase",
        ]

        min_length = data.get("min_length")
        max_length = data.get("max_length")
        if not _is_int(min_length):
            raise PolicyValidationError("password_requirements.min_length must be an integer >= 6")
        if not _is_int(max_length):
            raise PolicyValidationError("password_requirements.max_length must be an integer <= 256")
        min_length_int = cast(int, min_length)
        max_length_int = cast(int, max_length)
        if min_length_int < 6:
            raise PolicyValidationError("password_requirements.min_length must be an integer >= 6")
        if max_length_int > 256:
            raise PolicyValidationError("password_requirements.max_length must be an integer <= 256")
        if min_length_int >= max_length_int:
            raise PolicyValidationError("password_requirements.min_length must be less than max_length")

        cleaned = {
            "min_length": min_length_int,
            "max_length": max_length_int,
        }

        for key in bool_keys:
            item = data.get(key)
            if not isinstance(item, bool):
                raise PolicyValidationError(f"password_requirements.{key} must be a boolean")
            cleaned[key] = item

        return cleaned

    if name == "breach_cache_ttl":
        seconds = data.get("seconds")
        if not _is_int(seconds):
            raise PolicyValidationError("breach_cache_ttl.seconds must be an integer > 0")
        seconds_int = cast(int, seconds)
        if seconds_int <= 0:
            raise PolicyValidationError("breach_cache_ttl.seconds must be an integer > 0")
        return {"seconds": seconds_int}

    raise PolicyValidationError(f"Unknown policy name: {name}")


async def get_policy(service_id: str, name: str) -> dict[str, Any]:
    normalized_service_id = _normalize_service_id(service_id)
    key = _cache_key(normalized_service_id, name)

    cached = _as_policy_dict(await redis_client.get(key))
    if cached is not None:
        return cached

    async with AsyncSessionLocal() as db:
        try:
            row = (
                (
                    await db.execute(
                        text(
                            """
                            SELECT value
                            FROM policy_configs
                            WHERE service_id = :service_id AND name = :name
                            LIMIT 1
                            """
                        ),
                        {"service_id": normalized_service_id, "name": name},
                    )
                )
                .mappings()
                .first()
            )

            if row is None and normalized_service_id != DEFAULT_SERVICE_ID:
                row = (
                    (
                        await db.execute(
                            text(
                                """
                                SELECT value
                                FROM policy_configs
                                WHERE service_id = :service_id AND name = :name
                                LIMIT 1
                                """
                            ),
                            {"service_id": DEFAULT_SERVICE_ID, "name": name},
                        )
                    )
                    .mappings()
                    .first()
                )
        except Exception as exc:
            if not _is_missing_service_id_column(exc):
                try:
                    await db.rollback()
                except Exception:
                    pass
                row = None
            else:
                await db.rollback()

                row = (
                    (
                        await db.execute(
                            text(
                                """
                                SELECT value
                                FROM policy_configs
                                WHERE name = :name
                                LIMIT 1
                                """
                            ),
                            {"name": name},
                        )
                    )
                    .mappings()
                    .first()
                )

    if row is None:
        value = _copy_default(name)
    else:
        value = _as_policy_dict(row["value"])
        if value is None:
            value = _copy_default(name)

    await redis_client.set(key, value, expire_seconds=POLICY_CACHE_TTL_SECONDS)
    return value


async def get_all_policies(service_id: str) -> dict[str, dict[str, Any]]:
    normalized_service_id = _normalize_service_id(service_id)
    key = _all_cache_key(normalized_service_id)

    cached = _as_policy_dict(await redis_client.get(key))
    if cached is not None:
        return {name: _ensure_dict(value, name) for name, value in cached.items()}

    merged: dict[str, dict[str, Any]] = {}

    async with AsyncSessionLocal() as db:
        try:
            default_rows = (
                (
                    await db.execute(
                        text(
                            """
                            SELECT name, value
                            FROM policy_configs
                            WHERE service_id = :service_id
                            """
                        ),
                        {"service_id": DEFAULT_SERVICE_ID},
                    )
                )
                .mappings()
                .all()
            )

            for row in default_rows:
                maybe = _as_policy_dict(row["value"])
                if maybe is not None:
                    merged[row["name"]] = maybe

            if normalized_service_id != DEFAULT_SERVICE_ID:
                service_rows = (
                    (
                        await db.execute(
                            text(
                                """
                                SELECT name, value
                                FROM policy_configs
                                WHERE service_id = :service_id
                                """
                            ),
                            {"service_id": normalized_service_id},
                        )
                    )
                    .mappings()
                    .all()
                )

                for row in service_rows:
                    maybe = _as_policy_dict(row["value"])
                    if maybe is not None:
                        merged[row["name"]] = maybe
        except Exception as exc:
            if not _is_missing_service_id_column(exc):
                try:
                    await db.rollback()
                except Exception:
                    pass
            else:
                await db.rollback()

                legacy_rows = (
                    (
                        await db.execute(
                            text(
                                """
                                SELECT name, value
                                FROM policy_configs
                                """
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
                for row in legacy_rows:
                    maybe = _as_policy_dict(row["value"])
                    if maybe is not None:
                        merged[row["name"]] = maybe

    for policy_name in DEFAULT_POLICIES:
        merged.setdefault(policy_name, _copy_default(policy_name))

    await redis_client.set(key, merged, expire_seconds=POLICY_CACHE_TTL_SECONDS)
    return merged


async def invalidate_policy_cache(service_id: str, name: str | None = None) -> None:
    normalized_service_id = _normalize_service_id(service_id)

    if name is not None:
        await redis_client.delete(_cache_key(normalized_service_id, name))
        await redis_client.delete(_all_cache_key(normalized_service_id))
        return

    await redis_client.delete(_all_cache_key(normalized_service_id))

    names: set[str] = set(DEFAULT_POLICIES.keys())
    async with AsyncSessionLocal() as db:
        try:
            rows = (
                (
                    await db.execute(
                        text(
                            """
                            SELECT name
                            FROM policy_configs
                            WHERE service_id = :service_id
                            """
                        ),
                        {"service_id": normalized_service_id},
                    )
                )
                .mappings()
                .all()
            )
            for row in rows:
                names.add(row["name"])
        except Exception as exc:
            if not _is_missing_service_id_column(exc):
                try:
                    await db.rollback()
                except Exception:
                    pass
            else:
                await db.rollback()

                rows = (
                    (
                        await db.execute(
                            text(
                                """
                                SELECT name
                                FROM policy_configs
                                """
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
                for row in rows:
                    names.add(row["name"])

    for policy_name in names:
        await redis_client.delete(_cache_key(normalized_service_id, policy_name))


def get_default_policy_value(name: str) -> dict[str, Any]:
    return _copy_default(name)
