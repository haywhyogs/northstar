"""Integration test fixtures. Needs the local SQL Server (or the CI service container) with migrations applied."""

import pytest
from fastapi.testclient import TestClient

from northstar_payments.api.main import app
from tests.integration.helpers import Person, make_customer


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def alice() -> Person:
    return make_customer()


@pytest.fixture
def bob() -> Person:
    return make_customer()
