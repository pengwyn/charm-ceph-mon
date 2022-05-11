#! /usr/bin/python3

from ops.main import main

import ops_openstack.core

import ceph_hooks as hooks


class CephMonCharm(ops_openstack.core.OSBaseCharm):

    # General charm control callbacks.
    def on_install(self, event):
        hooks.install()

    def on_config(self, event):
        hooks.config_changed()

    def on_pre_series_upgrade(self, event):
        hooks.pre_series_upgrade()

    def on_upgrade(self, event):
        hooks.upgrade_charm()

    def on_post_series_upgrade(self, event):
        hooks.post_series_upgrade()

    # Relations.
    def on_mon_relation_joined(self, event):
        hooks.mon_relation_joined()

    def on_bootstrap_source_relation_changed(self, event):
        hooks.bootstrap_source_relation_changed()

    def on_prometheus_relation_joined_or_changed(self, event):
        hooks.prometheus_relation()

    def on_prometheus_relation_departed(self, event):
        hooks.prometheus_left()

    def on_mon_relation(self, event):
        hooks.mon_relation()

    def on_osd_relation(self, event):
        hooks.osd_relation()

    def on_dashboard_relation_joined(self, event):
        hooks.dashboard_relation()

    def on_radosgw_relation(self, event):
        hooks.radosgw_relation()

    def on_rbd_mirror_relation(self, event):
        hooks.rbd_mirror_relation()

    def on_mds_relation(self, event):
        hooks.mds_relation_joined()

    def on_admin_relation(self, event):
        hooks.admin_relation_joined()

    def on_client_relation(self, event):
        hooks.client_relation()

    def on_nrpe_relation(self, event):
        hooks.upgrade_nrpe_config()

    def __init__(self, *args):
        super().__init__(*args)
        self._stored.is_started = True
        fw = self.framework

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
