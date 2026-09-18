import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts.validate_repo import (
    compile_repo,
    helm_chart_reference,
    validate_argocd_applications,
    validate_commit_message,
    validate_root_app,
)


class ValidateRepoTests(unittest.TestCase):
    def create_repo(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repo_root = Path(temp_dir.name)
        (repo_root / "bootstrap").mkdir()
        (repo_root / "applications").mkdir()
        return repo_root

    def write_root_app(self, repo_root: Path, source_path: str = "applications") -> None:
        (repo_root / "bootstrap" / "root-app.yaml").write_text(
            "apiVersion: argoproj.io/v1alpha1\n"
            "kind: Application\n"
            "spec:\n"
            "  source:\n"
            f"    path: {source_path}\n",
            encoding="utf-8",
        )

    def test_compile_repo_succeeds_for_valid_repo(self) -> None:
        repo_root = self.create_repo()
        self.write_root_app(repo_root)

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = compile_repo(repo_root)

        self.assertEqual(result, 0)

    def test_validate_root_app_fails_when_source_path_is_missing(self) -> None:
        repo_root = self.create_repo()
        self.write_root_app(repo_root, source_path="missing-applications")

        errors = validate_root_app(repo_root)

        self.assertEqual(len(errors), 1)
        self.assertIn("missing-applications", errors[0])

    def test_validate_commit_message_rejects_invalid_messages(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = validate_commit_message("bad message")

        self.assertEqual(result, 1)

    def test_helm_chart_reference_supports_oci_registries(self) -> None:
        reference = helm_chart_reference(
            "unused",
            "quay.io/strimzi-helm",
            "strimzi-kafka-operator",
            True,
        )

        self.assertEqual(reference, "oci://quay.io/strimzi-helm/strimzi-kafka-operator")

    def test_validate_argocd_applications_rejects_missing_values_file(self) -> None:
        repo_root = self.create_repo()
        (repo_root / "applications" / "example.yaml").write_text(
            "apiVersion: argoproj.io/v1alpha1\n"
            "kind: Application\n"
            "metadata:\n"
            "  name: example\n"
            "spec:\n"
            "  destination:\n"
            "    server: https://kubernetes.default.svc\n"
            "    namespace: example\n"
            "  sources:\n"
            "    - chart: example\n"
            "      helm:\n"
            "        valueFiles:\n"
            "          - $values/values/example.yaml\n"
            "    - ref: values\n",
            encoding="utf-8",
        )

        errors = validate_argocd_applications(repo_root)

        self.assertEqual(len(errors), 1)
        self.assertIn("does not exist", errors[0])

    def test_validate_argocd_applications_accepts_existing_values_file(self) -> None:
        repo_root = self.create_repo()
        (repo_root / "values").mkdir()
        (repo_root / "values" / "example.yaml").write_text("enabled: true\n", encoding="utf-8")
        (repo_root / "applications" / "example.yaml").write_text(
            "apiVersion: argoproj.io/v1alpha1\n"
            "kind: Application\n"
            "metadata:\n"
            "  name: example\n"
            "spec:\n"
            "  destination:\n"
            "    server: https://kubernetes.default.svc\n"
            "    namespace: example\n"
            "  sources:\n"
            "    - chart: example\n"
            "      helm:\n"
            "        valueFiles:\n"
            "          - $values/values/example.yaml\n"
            "    - ref: values\n",
            encoding="utf-8",
        )

        errors = validate_argocd_applications(repo_root)

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
