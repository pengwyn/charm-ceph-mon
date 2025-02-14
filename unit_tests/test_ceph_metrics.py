#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import pathlib
import tempfile
import textwrap

from unittest.mock import patch
import unittest

from ops.testing import Harness

import ceph_metrics  # noqa: avoid circ. import
import charm
import helpers


@helpers.patch_network_get()
class TestCephMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Run once before tests begin."""
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.tmp = pathlib.Path(cls.tempdir.name)
        cls.rules_dir = cls.tmp / "rules"
        cls.rules_dir.mkdir()
        cls.rules = textwrap.dedent(
            """
            groups:
              - name: "testgroup"
                rules: []
            """
        )

    @classmethod
    def tearDownClass(cls):
        cls.tempdir.cleanup()

    def setUp(self):
        super().setUp()
        self.harness = Harness(charm.CephMonCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()
        self.harness.set_leader(True)
        self.harness.charm.metrics_endpoint._alert_rules_path = self.rules_dir

    def test_init(self):
        self.assertEqual(
            self.harness.charm.metrics_endpoint._relation_name,
            "metrics-endpoint",
        )

    @patch("ceph_metrics.ceph_utils.is_bootstrapped", return_value=True)
    @patch("ceph_metrics.ceph_utils.is_mgr_module_enabled", return_value=False)
    @patch("ceph_metrics.ceph_utils.mgr_enable_module")
    @patch("ceph_metrics.ceph_utils.mgr_disable_module")
    def test_add_remove_rel(
        self,
        mgr_disable_module,
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

        self.harness.remove_relation(rel_id)
        mgr_disable_module.assert_called_once()

    def get_alert_rules(self, rel_id):
        app_rel_data = self.harness.get_relation_data(
            rel_id, self.harness.model.app
        )
        return json.loads(app_rel_data["alert_rules"])

    @patch("ceph_metrics.ceph_utils.is_bootstrapped", return_value=True)
    @patch("ceph_metrics.CephMetricsEndpointProvider._set_alert_rules")
    def test_update_alert_rules_empty(
        self,
        set_alert_rules,
        _is_bootstrapped,
    ):
        """Test: no alert rules created with empty alert rules file."""
        rel_id = self.harness.add_relation("metrics-endpoint", "prometheus")
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.add_resource("alert-rules", "")
        self.harness.charm.metrics_endpoint.update_alert_rules()
        set_alert_rules.assert_called_with({})

    @patch("ceph_metrics.ceph_utils.is_bootstrapped", return_value=True)
    def test_update_alert_rules_invalid(self, _is_bootstrapped):
        rel_id = self.harness.add_relation("metrics-endpoint", "prometheus")
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.add_resource("alert-rules", "not-a-rule")
        self.harness.charm.metrics_endpoint.update_alert_rules()
        self.assertTrue(
            self.harness.charm.metrics_endpoint.have_alert_rule_errors()
        )

    @patch("ceph_metrics.ceph_utils.is_bootstrapped", return_value=True)
    def test_update_alert_rules(self, _is_bootstrapped):
        rel_id = self.harness.add_relation("metrics-endpoint", "prometheus")
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.add_resource("alert-rules", self.rules)
        self.harness.charm.metrics_endpoint.update_alert_rules()
        alert_rules = self.get_alert_rules(rel_id)
        self.assertTrue(alert_rules.get("groups"))
