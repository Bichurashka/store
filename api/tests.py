from django.db import OperationalError
from django.test import TestCase
from unittest.mock import patch
from rest_framework import status
from django.test import Client
from django.urls import reverse


class HealthCheckTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_check_success(self):
        response = self.client.get(reverse('health_check'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('api.views.connections')
    def test_health_check_db_error(self, mock_connections):
        mock_conn = mock_connections.__getitem__.return_value
        mock_conn.cursor.side_effect = OperationalError("DB connection error")

        response = self.client.get(reverse('health_check'))
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
