#! /usr/bin/python3
import logging

from ops.main import main

import charms.operator_libs_linux.v0.apt as apt
import charms.operator_libs_linux.v1.systemd as systemd

import ops_openstack.core
import charms_ceph.utils as ceph

import ceph_hooks as hooks
import ceph_metrics

import ops_actions


class CephMonCharm(ops_openstack.core.OSBaseCharm):

    release = 'quincy'

    PACKAGES = [
        'ceph', 'gdisk',
        'radosgw', 'lvm2', 'parted', 'smartmontools',
    ]

    # General charm control callbacks.

    # TODO: Figure out how to do hardening in an operator-framework
    # world
    def on_install(self, event):
        self.install_pkgs()
        rm_packages = ceph.determine_packages_to_remove()
        if rm_packages:
            apt.remove_package(packages=rm_packages, fatal=True)
        try:
            # we defer and explicitly run `ceph-create-keys` from
            # add_keyring_to_ceph() as part of bootstrap process
            # LP: #1719436.
            systemd.service_pause('ceph-create-keys')
        except systemd.SystemdError:
            pass
        hooks.assess_status(self)

    def on_config(self, event):
        hooks.config_changed()
        hooks.assess_status(self)

    def on_pre_series_upgrade(self, event):
        hooks.pre_series_upgrade()
        hooks.assess_status(self)

    def on_upgrade(self, event):
        self.metrics_endpoint.update_alert_rules()
        hooks.upgrade_charm()
        hooks.assess_status(self)

    def on_post_series_upgrade(self, event):
        hooks.post_series_upgrade()
        hooks.assess_status(self)

    # Relations.
    def on_mon_relation_joined(self, event):
        hooks.mon_relation_joined()
        hooks.assess_status(self)

    def on_bootstrap_source_relation_changed(self, event):
        hooks.bootstrap_source_relation_changed()
        hooks.assess_status(self)

    def on_prometheus_relation_joined_or_changed(self, event):
        hooks.prometheus_relation()
        hooks.assess_status(self)

    def on_prometheus_relation_departed(self, event):
        hooks.prometheus_left()
        hooks.assess_status(self)

    def on_mon_relation(self, event):
        hooks.mon_relation()
        hooks.assess_status(self)

    def on_osd_relation(self, event):
        hooks.osd_relation()
        hooks.assess_status(self)

    def on_dashboard_relation_joined(self, event):
        hooks.dashboard_relation()
        hooks.assess_status(self)

    def on_radosgw_relation(self, event):
        hooks.radosgw_relation()
        hooks.assess_status(self)

    def on_rbd_mirror_relation(self, event):
        hooks.rbd_mirror_relation()
        hooks.assess_status(self)

    def on_mds_relation(self, event):
        hooks.mds_relation_joined()
        hooks.assess_status(self)

    def on_admin_relation(self, event):
        hooks.admin_relation_joined()
        hooks.assess_status(self)

    def on_client_relation(self, event):
        hooks.client_relation()
        hooks.assess_status(self)

    def on_nrpe_relation(self, event):
        hooks.update_nrpe_config()
        hooks.assess_status(self)

    # Actions.

    def _observe_action(self, on_action, callable):
        def _make_method(fn):
            return lambda _, event: fn(event)

        method_name = 'on_' + str(on_action.event_kind)
        method = _make_method(callable)
        # In addition to being a method, the action callbacks _must_ have
        # the same '__name__' as their attribute name (this is how lookups
        # work in the operator framework world).
        method.__name__ = method_name

        inst = type(self)
        setattr(inst, method_name, method)
        self.framework.observe(on_action, getattr(self, method_name))

    def is_blocked_insecure_cmr(self):
        remote_block = False
        remote_unit_name = hooks.remote_unit()
        if remote_unit_name and hooks.is_cmr_unit(remote_unit_name):
            remote_block = not self.config['permit-insecure-cmr']
        return remote_block

    def __init__(self, *args):
        super().__init__(*args)
        self._stored.is_started = True

        if self.is_blocked_insecure_cmr():
            logging.error("Not running hook, CMR detected and not supported")
            return

        fw = self.framework

        self.metrics_endpoint = ceph_metrics.CephMetricsEndpointProvider(self)
        self._observe_action(self.on.change_osd_weight_action,
                             ops_actions.change_osd_weight.change_osd_weight)
        self._observe_action(self.on.copy_pool_action,
                             ops_actions.copy_pool.copy_pool)
        self._observe_action(self.on.create_crush_rule_action,
                             ops_actions.create_crush_rule.create_crush_rule)
        self._observe_action(
            self.on.create_erasure_profile_action,
            ops_actions.create_erasure_profile.create_erasure_profile_action)

        fw.observe(self.on.install, self.on_install)
        fw.observe(self.on.config_changed, self.on_config)
        fw.observe(self.on.pre_series_upgrade, self.on_pre_series_upgrade)
        fw.observe(self.on.upgrade_charm, self.on_upgrade)
        fw.observe(self.on.post_series_upgrade, self.on_post_series_upgrade)

        fw.observe(self.on.mon_relation_joined, self.on_mon_relation_joined)
        fw.observe(self.on.bootstrap_source_relation_changed,
                   self.on_bootstrap_source_relation_changed)
        fw.observe(self.on.prometheus_relation_joined,
                   self.on_prometheus_relation_joined_or_changed)
        fw.observe(self.on.prometheus_relation_changed,
                   self.on_prometheus_relation_joined_or_changed)
        fw.observe(self.on.prometheus_relation_departed,
                   self.on_prometheus_relation_departed)

        for key in ('mon_relation_departed', 'mon_relation_changed',
                    'leader_settings_changed',
                    'bootstrap_source_relation_departed'):
            fw.observe(getattr(self.on, key), self.on_mon_relation)

        fw.observe(self.on.osd_relation_joined,
                   self.on_osd_relation)
        fw.observe(self.on.osd_relation_changed,
                   self.on_osd_relation)

        fw.observe(self.on.dashboard_relation_joined,
                   self.on_dashboard_relation_joined)

        fw.observe(self.on.radosgw_relation_changed,
                   self.on_radosgw_relation)
        fw.observe(self.on.radosgw_relation_joined,
                   self.on_radosgw_relation)

        fw.observe(self.on.rbd_mirror_relation_changed,
                   self.on_rbd_mirror_relation)
        fw.observe(self.on.rbd_mirror_relation_joined,
                   self.on_rbd_mirror_relation)

        fw.observe(self.on.mds_relation_changed,
                   self.on_mds_relation)
        fw.observe(self.on.mds_relation_joined,
                   self.on_mds_relation)

        fw.observe(self.on.admin_relation_changed,
                   self.on_admin_relation)
        fw.observe(self.on.admin_relation_joined,
                   self.on_admin_relation)

        fw.observe(self.on.client_relation_changed,
                   self.on_client_relation)
        fw.observe(self.on.client_relation_joined,
                   self.on_client_relation)

        fw.observe(self.on.nrpe_external_master_relation_joined,
                   self.on_nrpe_relation)
        fw.observe(self.on.nrpe_external_master_relation_changed,
                   self.on_nrpe_relation)


if __name__ == '__main__':
    main(CephMonCharm)
