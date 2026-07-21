from __future__ import annotations

import copy

import pytest

from bi_storchcam.config_store import validate_config
from bi_storchcam.defaults import DEFAULT_CONFIG


@pytest.fixture
def config() -> dict:
    return validate_config(copy.deepcopy(DEFAULT_CONFIG))
