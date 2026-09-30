"""Billing confirmation must not initialize the catalogue it does not use."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main, mock

from loop_engine.core.service_runtime import billing_policy_checks as fixtures


class BillingOperatorBootstrapTests(TestCase):
    def test_confirmation_uses_policies_without_loading_search_or_catalogue(self):
        with TemporaryDirectory() as directory:
            path, _application = fixtures.configured(Path(directory))
            before = fixtures.stored(path)
            with mock.patch("loop_engine.core.service_runtime.catalogue_serving.load_catalogue_view",
                            side_effect=AssertionError("billing must not load catalogue")):
                status, report, _text = fixtures.apply(path)
            self.assertEqual(status, 0)
            self.assertTrue(report["every_installed_policy_current"])
            self.assertFalse(report["changed"])
            self.assertEqual(report["provider_calls"], 0)
            self.assertEqual(report["tenants_registered"], 0)
            self.assertEqual(fixtures.stored(path), before)

    def test_restoring_full_bootstrap_is_detected(self):
        from loop_engine.core.service_runtime import http_entrypoint
        with TemporaryDirectory() as directory:
            path, _application = fixtures.configured(Path(directory))
            with mock.patch.object(http_entrypoint, "load_host_billing_context", http_entrypoint.load_host_application), \
                    mock.patch("loop_engine.core.service_runtime.catalogue_serving.load_catalogue_view",
                               side_effect=AssertionError("wrong full bootstrap")), self.assertRaises(AssertionError):
                fixtures.apply(path)


if __name__ == "__main__":
    main()
