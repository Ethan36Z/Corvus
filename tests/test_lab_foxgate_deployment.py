"""Offline deployment contracts; no listeners, credentials or live HTTP requests."""

import json
from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "deploy/lab/foxgate"


def block(text, opening):
    """Read a brace-delimited block from these static Nginx configuration files."""
    start = text.index(opening) + len(opening)
    depth = 1
    for end in range(start, len(text)):
        depth += (text[end] == "{") - (text[end] == "}")
        if depth == 0:
            return text[start:end]
    raise AssertionError(f"Unclosed block: {opening}")


class LabFoxGateDeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rendered = subprocess.run(
            ["docker", "compose", "-f", str(BUNDLE / "compose.yaml"),
             "config", "--format", "json"],
            check=True, capture_output=True, text=True,
        )
        cls.compose = json.loads(rendered.stdout)
        # Ignore comments so a commented-out security directive cannot satisfy a check.
        cls.nginx = re.sub(r"#.*", "", (BUNDLE / "nginx/nginx.conf").read_text())
        cls.routes = re.sub(r"#.*", "", (BUNDLE / "nginx/gated-locations.conf").read_text())

    def test_project_has_only_isolated_hardened_services_and_pinned_images(self):
        self.assertEqual(self.compose["name"], "foxgate-lab")
        self.assertEqual(set(self.compose["services"]), {"auth", "gateway"})
        for service in self.compose["services"].values():
            self.assertEqual(service["network_mode"], "host")
            self.assertNotIn("ports", service)
            self.assertNotIn("build", service)
            self.assertRegex(service["image"], r"@sha256:[a-f0-9]{64}$")
            self.assertEqual(service["pull_policy"], "never")
            self.assertEqual(service["user"], "1000:1000")
            self.assertTrue(service["read_only"])
            self.assertIn("ALL", service["cap_drop"])
            self.assertIn("no-new-privileges:true", service["security_opt"])
        self.assertEqual(self.compose["services"]["gateway"]["depends_on"]["auth"]["condition"],
                         "service_healthy")

    def test_credentials_are_lab_only_read_only_and_missing_files_are_not_created(self):
        auth = self.compose["services"]["auth"]
        sources = {v["source"] for v in auth["volumes"]}
        self.assertEqual(sources, {
            "/home/ethan/srv/shared/secrets/lab-access/gated.htpasswd",
            "/home/ethan/srv/shared/secrets/lab-access/session-hmac.key",
        })
        self.assertEqual(len(auth["volumes"]), 2)
        self.assertEqual({v["source"]: v["target"] for v in auth["volumes"]}, {
            "/home/ethan/srv/shared/secrets/lab-access/gated.htpasswd":
                "/run/secrets/gated.htpasswd",
            "/home/ethan/srv/shared/secrets/lab-access/session-hmac.key":
                "/run/secrets/session-hmac.key",
        })
        self.assertEqual(auth["environment"]["FOXGATE_HTPASSWD_FILE"],
                         "/run/secrets/gated.htpasswd")
        self.assertEqual(auth["environment"]["FOXGATE_SESSION_KEY_FILE"],
                         "/run/secrets/session-hmac.key")
        gateway_volumes = self.compose["services"]["gateway"]["volumes"]
        self.assertEqual(len(gateway_volumes), 2)
        self.assertEqual({v["source"]: v["target"] for v in gateway_volumes}, {
            str(BUNDLE / "nginx/nginx.conf"): "/etc/nginx/nginx.conf",
            str(BUNDLE / "nginx/gated-locations.conf"):
                "/etc/nginx/foxgate/gated-locations.conf",
        })
        for service in self.compose["services"].values():
            for volume in service["volumes"]:
                self.assertEqual(volume["type"], "bind")
                self.assertTrue(volume["read_only"])
                self.assertIs(volume["bind"]["create_host_path"], False)
        self.assertFalse(any("secrets" in v["source"]
                             for v in self.compose["services"]["gateway"]["volumes"]))
        self.assertEqual(auth["environment"]["FOXGATE_COOKIE_SECURE"], "true")
        self.assertEqual(auth["healthcheck"]["test"], ["CMD", "/app/foxgate-auth", "healthcheck"])

    def test_only_loopback_listeners_and_one_explicit_hostname(self):
        self.assertEqual(self.compose["services"]["auth"]["environment"]["FOXGATE_LISTEN_ADDR"],
                         "127.0.0.1:8101")
        self.assertEqual(re.findall(r"listen\s+([^;]+);", self.nginx),
                         ["127.0.0.1:8100 default_server", "127.0.0.1:8100"])
        self.assertEqual(re.findall(r"server_name\s+([^;]+);", self.nginx),
                         ["_", "lab-corvus.foxluma.com"])
        default = block(self.nginx, "server {")
        self.assertIn("default_server;", default)
        self.assertIn("return 404;", default)
        self.assertNotIn("proxy_pass", default)
        self.assertNotIn("include", default)
        self.assertEqual(default.split(), ["listen", "127.0.0.1:8100", "default_server;",
                                          "server_name", "_;", "return", "404;"])
        self.assertEqual(re.findall(r"\binclude\s+([^;]+);", self.nginx),
                         ["/etc/nginx/mime.types", "/etc/nginx/foxgate/gated-locations.conf"])
        self.assertNotRegex(self.routes, r"\b(?:listen|server_name|include)\b")

    def test_application_has_no_unauthenticated_bypass_or_other_origins(self):
        config = self.nginx + self.routes
        self.assertNotRegex(config, r"\bsatisfy\s+any\s*;")
        self.assertEqual(re.findall(r"\bauth_request\s+([^;]+);", config),
                         ["/_foxgate/verify"])
        app = block(self.routes, "location / {")
        self.assertIn("auth_request /_foxgate/verify;", app)
        self.assertIn("error_page 401 = @foxgate_unauthorized;", app)
        self.assertIn("proxy_pass http://127.0.0.1:3003;", app)
        self.assertIn("proxy_intercept_errors off;", app)
        self.assertIn("proxy_next_upstream off;", self.nginx)
        self.assertEqual(set(re.findall(r"proxy_pass\s+([^;]+);", self.routes)), {
            "http://127.0.0.1:8101/verify", "http://127.0.0.1:8101/login",
            "http://127.0.0.1:8101/logout", "http://127.0.0.1:8101",
            "http://127.0.0.1:3003",
        })
        self.assertEqual(re.findall(r"\blocation\s+([^{}]+)\{", config), [
            "= /_foxgate/verify ", "= /_foxgate/login ", "= /_foxgate/logout ",
            "@foxgate_unauthorized ", "/ ",
        ])
        self.assertIn("internal;", block(self.routes, "location = /_foxgate/verify {"))

    def test_only_html_unauthorized_requests_use_auth_safe_redirect_handler(self):
        redirect = block(self.routes, "location @foxgate_unauthorized {")
        self.assertIn("if ($foxgate_accepts_html = 0)", redirect)
        self.assertIn("return 401;", redirect)
        self.assertIn("rewrite ^ /login-redirect break;", redirect)
        self.assertIn("proxy_method GET;", redirect)
        self.assertIn("proxy_pass_request_body off;", redirect)
        self.assertIn("proxy_set_header X-FoxGate-Original-URI $request_uri;", redirect)
        self.assertIn("proxy_set_header X-FoxGate-Login-Path /_foxgate/login;", redirect)
        self.assertNotIn("error_page 403", self.routes)
        self.assertNotIn("error_page 500", self.routes)

    def test_supplied_forwarding_fields_are_replaced_and_app_auth_is_preserved(self):
        app = block(self.routes, "location / {")
        for header, value in {
            "Host": "lab-corvus.foxluma.com", "X-Forwarded-Host": "lab-corvus.foxluma.com",
            "X-Forwarded-Proto": "https", "X-Forwarded-Port": "443",
            "X-Forwarded-For": "$remote_addr", "X-Real-IP": "$remote_addr",
            "Forwarded": '\"\"', "X-Forwarded-Prefix": '\"\"',
            "X-Forwarded-Ssl": '\"\"', "X-Forwarded-Server": '\"\"',
            "Authorization": "$http_authorization", "Cookie": "$http_cookie",
        }.items():
            self.assertIn(f"proxy_set_header {header} {value};", app)
        self.assertNotIn("$proxy_add_x_forwarded_for", self.routes)
        self.assertNotIn("real_ip_header", self.nginx)

    def test_websocket_sse_and_explicit_body_and_timeout_limits(self):
        app = block(self.routes, "location / {")
        for directive in ("proxy_http_version 1.1;", "proxy_buffering off;",
                          "proxy_cache off;", "proxy_send_timeout 600s;",
                          "proxy_read_timeout 600s;",
                          "proxy_set_header Upgrade $http_upgrade;",
                          "proxy_set_header Connection $foxgate_connection_upgrade;"):
            self.assertIn(directive, app)
        self.assertIn("map $http_upgrade $foxgate_connection_upgrade", self.nginx)
        self.assertIn("client_max_body_size 10m;", self.nginx)
        self.assertIn("proxy_connect_timeout 5s;", self.nginx)
        self.assertIn("proxy_read_timeout 5s;", self.nginx)


if __name__ == "__main__":
    unittest.main()
