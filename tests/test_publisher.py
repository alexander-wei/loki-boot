"""Exercise the real Bash script and jq parser without AWS or Loki access."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "loki-boot/debian/loki-boot.sh"
METADATA_URI = "http://169.254.170.2/v4/test-container"

MOCK = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
root = pathlib.Path(os.environ["MOCK_ROOT"])
config = json.loads((root / "config.json").read_text())
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / "calls.jsonl").open("a") as f:
    f.write(json.dumps([name, args]) + "\n")
if name == "curl":
    if args[-1].endswith("/loki/api/v1/push"):
        (root / "payload.json").write_text(args[args.index("--data-raw") + 1])
        sys.exit(config.get("push_status", 0))
    count_file = root / "count"
    count = int(count_file.read_text()) if count_file.exists() else 0
    count_file.write_text(str(count + 1))
    responses = config["responses"]
    response = responses[min(count, len(responses) - 1)]
    body = response.get("body", "")
    print(body if isinstance(body, str) else json.dumps(body))
    sys.exit(response.get("status", 0))
elif name == "hostname":
    print(config.get("host_addresses", "10.1.2.3"))
    sys.exit(config.get("host_status", 0))
elif name != "sleep":
    sys.exit(99)
'''


def network(*addresses, mode="awsvpc"):
    return {"Networks": [{"NetworkMode": mode, "IPv4Addresses": list(addresses)}]}


class PublisherTests(unittest.TestCase):
    def run_publisher(self, responses=None, env=None, **config):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mock = root / "mock"
            mock.write_text(MOCK)
            mock.chmod(0o755)
            for command in ("curl", "hostname", "sleep"):
                (root / command).symlink_to(mock)
            config["responses"] = responses or [{"body": network("10.0.1.247")}]
            (root / "config.json").write_text(json.dumps(config))
            process_env = {
                k: v for k, v in os.environ.items()
                if k not in {"PRIVATE_IP", "ECS_CONTAINER_METADATA_URI_V4",
                             "ECS_CONTAINER_METADATA_URI", "AWS_EXECUTION_ENV"}
            }
            process_env.update(
                PATH=f"{root}:{os.environ['PATH']}", MOCK_ROOT=str(root),
                SERVICE_NAME="test-service", LOKI_URL="https://loki.example",
                LOKI_USER="test-user", LOKI_TOKEN="test-token",
                ECS_CONTAINER_METADATA_URI_V4=METADATA_URI,
            )
            process_env.update(env or {})
            result = subprocess.run(
                ["bash", str(SCRIPT)], env=process_env, capture_output=True,
                text=True, timeout=10,
            )
            calls_file = root / "calls.jsonl"
            calls = ([json.loads(line) for line in calls_file.read_text().splitlines()]
                     if calls_file.exists() else [])
            payload_file = root / "payload.json"
            payload = json.loads(payload_file.read_text()) if payload_file.exists() else None
        return result, calls, payload

    def assert_published(self, result, payload, ip="10.0.1.247"):
        self.assertEqual(result.returncode, 0, result.stderr)
        stream = payload["streams"][0]
        self.assertEqual(stream["stream"], {"service_name": "test-service"})
        timestamp, line = stream["values"][0]
        self.assertTrue(timestamp.isdigit())
        self.assertEqual(json.loads(line), {"private_ip": ip, "timestamp": timestamp})

    def test_container_metadata_and_payload(self):
        result, calls, payload = self.run_publisher()
        self.assert_published(result, payload)
        args = calls[0][1]
        self.assertEqual(args[-1], METADATA_URI)
        for flag, value in (("--noproxy", "*"), ("--connect-timeout", "2"), ("--max-time", "5")):
            self.assertEqual(args[args.index(flag) + 1], value)
        self.assertNotIn("hostname", [name for name, _ in calls])

    def test_task_fallback(self):
        result, calls, payload = self.run_publisher([
            {"body": {}},
            {"body": {"Containers": [network("10.0.1.247")]}}
        ])
        self.assert_published(result, payload)
        self.assertEqual(calls[1][1][-1], METADATA_URI + "/task")

    def test_transient_fetch_json_and_address_failures_retry(self):
        for response in ({"status": 7}, {"status": 28}, {"body": "not json"}, {"body": {}}):
            with self.subTest(response=response):
                result, calls, payload = self.run_publisher([
                    response, response, {"body": network("10.0.1.247")}
                ])
                self.assert_published(result, payload)
                self.assertIn(["sleep", ["2"]], calls)
                self.assertIn("attempt 1/5", result.stderr)

    def test_permanent_failures_are_bounded_and_never_publish(self):
        for body in ("bad json", {}, network("10.2.3.4", mode="bridge"),
                     network("999.1.2.3"), network("::1"), {"Networks": "wrong type"}):
            with self.subTest(body=body):
                result, calls, payload = self.run_publisher([{"body": body}])
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIsNone(payload)
                self.assertEqual(sum(name == "curl" for name, _ in calls), 10)
                self.assertEqual(sum(name == "sleep" for name, _ in calls), 4)
                self.assertNotIn("hostname", [name for name, _ in calls])
                self.assertIn("set PRIVATE_IP explicitly", result.stderr)

    def test_v3_metadata(self):
        result, calls, payload = self.run_publisher(env={
            "ECS_CONTAINER_METADATA_URI_V4": "", "ECS_CONTAINER_METADATA_URI": METADATA_URI
        })
        self.assert_published(result, payload)
        self.assertEqual(calls[0][1][-1], METADATA_URI)

    def test_v4_precedence_and_trailing_slash(self):
        result, calls, payload = self.run_publisher(env={
            "ECS_CONTAINER_METADATA_URI_V4": METADATA_URI + "/",
            "ECS_CONTAINER_METADATA_URI": "http://wrong-v3-endpoint"
        })
        self.assert_published(result, payload)
        self.assertEqual(calls[0][1][-1], METADATA_URI)

    def test_explicit_override_skips_discovery(self):
        result, calls, payload = self.run_publisher(env={"PRIVATE_IP": "10.8.7.6"})
        self.assert_published(result, payload, "10.8.7.6")
        self.assertEqual(len(calls), 1)  # Only the Loki push.

    def test_invalid_override_does_not_fall_back(self):
        for ip in ("999.1.2.3", "127.0.0.1", "169.254.170.2", "0.0.0.0",
                   "224.0.0.1", "01.2.3.4", "::1", "not-an-ip"):
            with self.subTest(ip=ip):
                result, calls, payload = self.run_publisher(env={"PRIVATE_IP": ip})
                self.assertEqual(result.returncode, 1)
                self.assertIsNone(payload)
                self.assertEqual(calls, [])

    def test_skips_invalid_candidates(self):
        result, _, payload = self.run_publisher([{
            "body": network(None, "999.1.2.3", "127.0.0.1", "10.0.1.247")
        }])
        self.assert_published(result, payload)

    def test_non_ecs_host_fallback(self):
        result, _, payload = self.run_publisher(
            env={"ECS_CONTAINER_METADATA_URI_V4": ""},
            host_addresses="::1 127.0.0.1 169.254.1.1 10.2.3.4 10.2.3.5"
        )
        self.assert_published(result, payload, "10.2.3.4")

    def test_missing_host_address_or_failed_hostname_never_publishes(self):
        for config in ({"host_addresses": ""}, {"host_status": 1}):
            with self.subTest(config=config):
                result, _, payload = self.run_publisher(
                    env={"ECS_CONTAINER_METADATA_URI_V4": ""}, **config
                )
                self.assertEqual(result.returncode, 1)
                self.assertIsNone(payload)
                self.assertIn("usable host IPv4", result.stderr)

    def test_ecs_without_metadata_never_uses_hostname(self):
        result, calls, payload = self.run_publisher(env={
            "ECS_CONTAINER_METADATA_URI_V4": "", "AWS_EXECUTION_ENV": "AWS_ECS_FARGATE"
        })
        self.assertEqual(result.returncode, 1)
        self.assertEqual(calls, [])
        self.assertIsNone(payload)
        self.assertIn("metadata URI is missing", result.stderr)

    def test_loki_failure_remains_visible(self):
        result, _, payload = self.run_publisher(push_status=22)
        self.assertEqual(result.returncode, 22)
        self.assertIsNotNone(payload)


if __name__ == "__main__":
    unittest.main()
