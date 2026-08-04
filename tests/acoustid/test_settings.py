import importlib
import os
import sys
from dataclasses import FrozenInstanceError, asdict

import pytest

from beetsplug.noqlenmeta.acoustid import AcoustIDSettings, default_acoustid_settings

EXPECTED_DEFAULTS = {
    "enabled": False,
    "reuse_existing": True,
    "compute_missing": False,
    "lookup": True,
    "use_for_identity": True,
    "min_score": 0.90,
    "min_margin": 0.05,
    "max_results": 5,
    "max_recordings_per_result": 10,
    "timeout_seconds": 15.0,
    "requests_per_second": 3.0,
    "cache_entries": 256,
    "fpcalc": "fpcalc",
}


def settings(**changes: object) -> AcoustIDSettings:
    values = {**EXPECTED_DEFAULTS, **changes}
    return AcoustIDSettings.from_mapping(values)


def test_defaults_are_exact_fresh_and_immutable() -> None:
    first = default_acoustid_settings()
    second = default_acoustid_settings()

    assert asdict(first) == EXPECTED_DEFAULTS
    assert first == second
    assert first is not second
    with pytest.raises(FrozenInstanceError):
        first.enabled = True  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "lower", "upper"),
    [
        ("min_score", 0.0, 1.0),
        ("min_margin", 0.0, 1.0),
        ("timeout_seconds", 1.0, 60.0),
        ("requests_per_second", 0.001, 3.0),
    ],
)
def test_numeric_boundaries_are_accepted(field: str, lower: float, upper: float) -> None:
    assert getattr(settings(**{field: lower}), field) == lower
    assert getattr(settings(**{field: upper}), field) == upper


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("min_score", -0.001),
        ("min_score", 1.001),
        ("min_margin", -0.001),
        ("min_margin", 1.001),
        ("timeout_seconds", 0.999),
        ("timeout_seconds", 60.001),
        ("requests_per_second", 0.0),
        ("requests_per_second", 3.001),
    ],
)
def test_numbers_outside_bounds_are_rejected(field: str, invalid: float) -> None:
    with pytest.raises(ValueError, match=field):
        settings(**{field: invalid})


@pytest.mark.parametrize(
    "field", ["min_score", "min_margin", "timeout_seconds", "requests_per_second"]
)
@pytest.mark.parametrize("invalid", [True, float("nan"), float("inf"), -float("inf")])
def test_numeric_settings_reject_booleans_and_nonfinite_values(field: str, invalid: object) -> None:
    with pytest.raises(ValueError, match=field):
        settings(**{field: invalid})


@pytest.mark.parametrize(
    ("field", "lower", "upper"),
    [
        ("max_results", 1, 20),
        ("max_recordings_per_result", 1, 50),
        ("cache_entries", 0, 4096),
    ],
)
def test_integer_boundaries_are_accepted(field: str, lower: int, upper: int) -> None:
    assert getattr(settings(**{field: lower}), field) == lower
    assert getattr(settings(**{field: upper}), field) == upper


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("max_results", 0),
        ("max_results", 21),
        ("max_recordings_per_result", 0),
        ("max_recordings_per_result", 51),
        ("cache_entries", -1),
        ("cache_entries", 4097),
    ],
)
def test_integer_settings_reject_out_of_range_values(field: str, invalid: int) -> None:
    with pytest.raises(ValueError, match=field):
        settings(**{field: invalid})


@pytest.mark.parametrize("field", ["max_results", "max_recordings_per_result", "cache_entries"])
@pytest.mark.parametrize("invalid", [True, 1.5])
def test_integer_settings_reject_booleans_and_nonintegers(field: str, invalid: object) -> None:
    with pytest.raises(ValueError, match=field):
        settings(**{field: invalid})


@pytest.mark.parametrize(
    "field", ["enabled", "reuse_existing", "compute_missing", "lookup", "use_for_identity"]
)
def test_boolean_settings_require_actual_booleans(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        settings(**{field: 1})


@pytest.mark.parametrize("fpcalc", [None, "", " "])
def test_fpcalc_requires_nonempty_string(fpcalc: object) -> None:
    with pytest.raises(ValueError, match="fpcalc"):
        settings(fpcalc=fpcalc)


def test_complete_mapping_rejects_missing_and_unknown_keys() -> None:
    missing = dict(EXPECTED_DEFAULTS)
    missing.pop("lookup")
    with pytest.raises(ValueError, match="missing AcoustID setting: lookup"):
        AcoustIDSettings.from_mapping(missing)
    with pytest.raises(ValueError, match="unknown AcoustID setting"):
        AcoustIDSettings.from_mapping({**EXPECTED_DEFAULTS, "client_key": "secret"})
    sensitive = "/private/value"
    with pytest.raises(ValueError) as captured:
        AcoustIDSettings.from_mapping({**EXPECTED_DEFAULTS, sensitive: "raw-payload"})
    assert sensitive not in str(captured.value)
    assert "raw-payload" not in str(captured.value)


def test_import_defaults_and_validation_do_not_access_environment(monkeypatch) -> None:
    class NoEnvironment(dict):
        def __getitem__(self, key):
            raise AssertionError("environment access is forbidden")

        def get(self, key, default=None):
            raise AssertionError("environment access is forbidden")

    monkeypatch.setattr(os, "environ", NoEnvironment())
    monkeypatch.setattr(
        os,
        "getenv",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("environment access")),
    )
    for module_name in tuple(sys.modules):
        if module_name.startswith("beetsplug.noqlenmeta.acoustid"):
            sys.modules.pop(module_name)
    package = importlib.import_module("beetsplug.noqlenmeta.acoustid")
    module = importlib.import_module("beetsplug.noqlenmeta.acoustid.settings")

    assert module.default_acoustid_settings().enabled is False
    assert module.AcoustIDSettings.from_mapping(EXPECTED_DEFAULTS).lookup is True
    assert "client_key" not in asdict(module.default_acoustid_settings())
    assert package.default_acoustid_settings().lookup is True
