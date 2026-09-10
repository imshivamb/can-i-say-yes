from collections.abc import Iterator

import pytest

from adapters.files.runtime import reset_runtime
from adapters.files.world import DATA_ROOT


@pytest.fixture(autouse=True)
def _clean_runtime() -> Iterator[None]:
    reset_runtime(DATA_ROOT)
    yield
    reset_runtime(DATA_ROOT)
