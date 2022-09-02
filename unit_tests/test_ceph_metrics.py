#!/usr/bin/env python3

# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import patch
import unittest

from ops import storage, model, framework
from ops.testing import Harness, _TestingModelBackend

import charm


class TestCephMetrics(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.harness = Harness(charm.CephMonCharm)

        # BEGIN: Workaround until network_get is implemented
        class _TestingOPSModelBackend(_TestingModelBackend):
            def network_get(self, endpoint_name, relation_id=None):
                network_data = {
                    "bind-addresses": [
                        {
                            "addresses": [{"value": "10.0.0.10"}],
                        }
                    ],
                }
                return network_data

        self.harness._backend = _TestingOPSModelBackend(
            self.harness._unit_name, self.harness._meta
        )
        self.harness._model = model.Model(
            self.harness._meta, self.harness._backend
        )
        self.harness._framework = framework.Framework(
            storage.SQLiteStorage(":memory:"),
            self.harness._charm_dir,
            self.harness._meta,
            self.harness._model,
        )
        # END Workaround
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()
        self.harness.set_leader(True)

    def test_init(self):
        self.assertEqual(
            self.harness.charm.metrics_endpoint._relation_name,
            "metrics-endpoint",
        )

    @patch("ceph_metrics.ceph_utils.is_bootstrapped", return_value=True)
    @patch("ceph_metrics.ceph_utils.is_mgr_module_enabled", return_value=False)
    @patch("ceph_metrics.ceph_utils.mgr_enable_module")
    def test_add_rel(
        self,
        mgr_enable_module,
        _is_mgr_module_enable,
        _is_bootstrapped,
    ):
        rel_id = self.harness.add_relation("metrics-endpoint", "prometheus")
        self.harness.add_relation_unit(rel_id, "prometheus/0")

        unit_rel_data = self.harness.get_relation_data(
            rel_id, self.harness.model.unit
        )
        self.assertEqual(
            unit_rel_data["prometheus_scrape_unit_address"], "10.0.0.10"
        )

        # Trigger relation change event as a side effect
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"foo": "bar"}
        )

        mgr_enable_module.assert_called_once()

        app_rel_data = self.harness.get_relation_data(
            rel_id, self.harness.model.app
        )
        jobs = app_rel_data["scrape_jobs"]
        self.assertEqual(
            jobs,
            (
                '[{"metrics_path": "/metrics", '
                '"static_configs": [{"targets": ["*:9283"]}]}]'
            ),
        )
