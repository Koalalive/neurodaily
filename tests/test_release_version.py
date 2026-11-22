import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from zipfile import ZipFile

from scripts import verify_release_version as release


class ReleaseVersionTests(unittest.TestCase):
    def test_release_order_and_retry(self):
        published = {"tag_name": "v1.0.7", "draft": False, "prerelease": False}
        self.assertFalse(release.should_publish([published], "v1.0.7"))
        self.assertTrue(release.should_publish([{**published, "draft": True}], "v1.0.7"))
        self.assertTrue(release.should_publish([published], "v1.0.8"))
        with self.assertRaisesRegex(ValueError, "newer release"):
            release.should_publish([published], "v1.0.6")

    def test_docker_visibility_requires_known_matching_repository_metadata(self):
        info = {"namespace": "koalalive", "name": "neurodaily"}
        auth = {"access_token": "temporary-token-fixture"}
        env = {"DOCKERHUB_USERNAME": "test-publisher", "DOCKERHUB_TOKEN": "test-secret"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(release, "_hub_request", side_effect=[auth, {**info, "is_private": True}, None]):
                self.assertIs(release.verify_docker_destination("1.0.7", source_private=True), False)
            with mock.patch.object(release, "_hub_request", side_effect=[auth, {**info, "is_private": False},
                                                                         {"name": "1.0.7"}]):
                self.assertIs(release.verify_docker_destination("1.0.7", source_private=False), True)
            for value, source_private in ((False, True), (None, False), ("false", False)):
                with self.subTest(value=value, source_private=source_private), \
                        mock.patch.object(release, "_hub_request", side_effect=[auth, {**info, "is_private": value}]) as api:
                    with self.assertRaises(ValueError):
                        release.verify_docker_destination("latest", source_private=source_private)
                    self.assertEqual(api.call_count, 2)

    def test_wheel_must_match_the_checkout_including_data(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            (root / "neurodaily").mkdir()
            (root / "neurodaily/cli.py").write_bytes(b"def main(): pass\n")
            (root / "neurodaily/options.json").write_bytes(b"{}\n")
            (root / "pyproject.toml").write_text('[tool.setuptools.package-data]\nneurodaily = ["*.json"]\n',
                                                encoding="utf-8")
            target = root / "neurodaily-1.0.7-py3-none-any.whl"
            with ZipFile(target, "w") as wheel:
                wheel.writestr("neurodaily-1.0.7.dist-info/METADATA", "Name: neurodaily\nVersion: 1.0.7\n")
                wheel.writestr("neurodaily-1.0.7.dist-info/entry_points.txt",
                               "[console_scripts]\nneurodaily = neurodaily.cli:main\n")
                wheel.write(root / "neurodaily/cli.py", "neurodaily/cli.py")
                wheel.write(root / "neurodaily/options.json", "neurodaily/options.json")
            self.assertEqual(release.verify_wheel(root, root, "1.0.7"), target)
            (root / "neurodaily/options.json").write_bytes(b'{"changed":true}\n')
            with self.assertRaisesRegex(ValueError, "Wheel source differs"):
                release.verify_wheel(root, root, "1.0.7")
