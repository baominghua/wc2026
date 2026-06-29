from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
DEPLOY_NAS = ROOT / "scripts" / "deploy-nas.ps1"


class DeployScriptTests(unittest.TestCase):
    def test_nas_deploy_uploads_package_to_project_storage_not_tmp(self):
        source = DEPLOY_NAS.read_text(encoding="utf-8")

        self.assertIn("$RemotePackage", source)
        self.assertIn(".deploy-wc2026-nas-docker.tar.gz", source)
        self.assertIn("${NasUser}@${NasHost}:$RemotePackage", source)
        self.assertIn("tar -xzf '$RemotePackage'", source)
        self.assertNotIn(":/tmp/wc2026-nas-docker.tar.gz", source)
        self.assertNotIn("tar -xzf /tmp/wc2026-nas-docker.tar.gz", source)


if __name__ == "__main__":
    unittest.main()
