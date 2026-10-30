from unittest.mock import patch
from django.test import SimpleTestCase


class DiceViewsTest(SimpleTestCase):
    def test_initial_comparison_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Бросить кости")

    @patch("client.views.roll", return_value=3)
    def test_direct_route_uses_secure_go_port(self, roll):
        response = self.client.get("/grpc")
        self.assertContains(response, "Direct gRPC + mTLS | Value: 3")
        roll.assert_called_once_with("127.0.0.1:8443")

    @patch("client.views.roll", return_value=5)
    def test_nginx_route_uses_proxy_port(self, roll):
        response = self.client.get("/nginx")
        self.assertContains(response, "nginx + mTLS")
        roll.assert_called_once_with("127.0.0.1:9448")

    @patch("client.views.roll", side_effect=OSError("certificate missing"))
    def test_rpc_error_returns_503(self, _roll):
        with self.assertLogs("client.views", level="ERROR"):
            response = self.client.get("/grpc")
        self.assertEqual(response.status_code, 503)

    @patch("client.views.roll", side_effect=[2, 6])
    def test_comparison_calls_both_paths(self, roll):
        response = self.client.post("/")
        self.assertContains(response, "Значение: 2")
        self.assertContains(response, "Значение: 6")
        self.assertEqual([call.args[0] for call in roll.call_args_list], ["127.0.0.1:8443", "127.0.0.1:9448"])
