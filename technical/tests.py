from unittest.mock import MagicMock, patch

from django.db import OperationalError
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework import status


class HealthCheckTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

    def test_health_check_success(self) -> None:
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("technical.views.connections")
    def test_health_check_db_error(self, mock_connections: MagicMock) -> None:
        mock_conn = mock_connections.__getitem__.return_value
        mock_conn.cursor.side_effect = OperationalError("DB connection error")

        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
