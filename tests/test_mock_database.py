import asyncio
from beanie import init_beanie
from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest

from models.admin import Admin
from models.user import Student
from tests.conftest import mock_no_authentication


class TestMockAuthentication:
    @classmethod
    def setup_class(cls):
        mock_no_authentication()

    @pytest.mark.anyio
    async def test_mock_databases(self, client_test: AsyncClient):
        # generate data
        await Admin(
            fullname="admin", email="admin@admin.com", password="admin"
        ).create()

        await Student(
            fullname="student",
            email="student@student.com",
            password="student",
            role="baseUser",
            phone="0909090909",

        ).create()

        response = await client_test.get("user")

        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_mock_database(self, client_test: AsyncClient):
        await Admin(
            fullname="admin", email="admin@admin.com", password="admin"
        ).create()

        await Student(
            fullname="student",
            email="student@student.com",
            password="student",
            role="baseUser",
            phone="0909090909",
        ).create()

        response = await client_test.get("student")

        assert response.status_code == 200
