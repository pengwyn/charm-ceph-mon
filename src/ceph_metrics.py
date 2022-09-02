# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide ceph metrics to prometheus

Configure prometheus scrape jobs via the metrics-endpoint relation.
"""
import logging
from typing import Optional, Union, List

from charms.prometheus_k8s.v0 import prometheus_scrape
from charms_ceph import utils as ceph_utils
from ops.framework import BoundEvent


logger = logging.getLogger(__name__)

DEFAULT_CEPH_JOB = {
    "metrics_path": "/metrics",
    "static_configs": [{"targets": ["*:9283"]}],
}


class CephMetricsEndpointProvider(prometheus_scrape.MetricsEndpointProvider):
    def __init__(
        self,
        charm,
        relation_name: str = prometheus_scrape.DEFAULT_RELATION_NAME,
        jobs=None,
        alert_rules_path: str = prometheus_scrape.DEFAULT_ALERT_RULES_RELATIVE_PATH,  # noqa
        refresh_event: Optional[Union[BoundEvent, List[BoundEvent]]] = None,
    ):
        if jobs is None:
            jobs = [DEFAULT_CEPH_JOB]
        super().__init__(
            charm,
            relation_name=relation_name,
            jobs=jobs,
            alert_rules_path=alert_rules_path,
            refresh_event=refresh_event,
        )

    def _on_relation_changed(self, event):
        """Enable prometheus on relation change"""
        if self._charm.unit.is_leader() and ceph_utils.is_bootstrapped():
            logger.debug(
                "is_leader and is_bootstrapped, running rel changed: %s", event
            )
            ceph_utils.mgr_enable_module("prometheus")
            logger.debug("module_enabled")
            super()._on_relation_changed(event)
