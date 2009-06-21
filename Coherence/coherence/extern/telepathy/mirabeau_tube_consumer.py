from coherence.extern.telepathy import tube
from coherence.extern.telepathy import client
from coherence.dbus_constants import BUS_NAME, OBJECT_PATH, DEVICE_IFACE, SERVICE_IFACE

from coherence import dbus_service


class MirabeauTubeConsumerMixin(tube.TubeConsumerMixin):
    pontoon = None
    device_peer = None
    service_peer = None
    initial_announce_done = False

    def __init__(self, found_peer_callback=None,
                 disapeared_peer_callback=None, got_devices_callback=None):
        super(MirabeauTubeConsumerMixin, self).__init__(found_peer_callback=found_peer_callback,
                                                        disapeared_peer_callback=disapeared_peer_callback)
        self.got_devices_callback = got_devices_callback
        self.debug("MirabeauTubeConsumer __init__")

    def pre_accept_tube(self, peer):
        initiator = peer.params["initiator"]
        return initiator in self.roster

    def _create_peer_remote_object(self, peer, interface):
        self.debug("_create_peer_remote_object %r %r", peer, interface)
        if interface == BUS_NAME:
            peer.remote_object = dbus_service.DBusPontoon(None, self.tube_conn)
        elif interface == DEVICE_IFACE:
            peer.remote_object = dbus_service.DBusDevice(None, self.tube_conn)
        elif interface == SERVICE_IFACE:
            peer.remote_object = dbus_service.DBusService(None, None, self.tube_conn)

    def _create_peer_object_proxy(self, peer, interface):
        self.debug("_create_peer_object_proxy %r %r", peer, interface)

        if interface == BUS_NAME:
            pontoon_tube = peer.remote_object.tube
            self.pontoon = pontoon_tube.get_object(peer.initiator_contact,
                                                   OBJECT_PATH)
        elif interface == DEVICE_IFACE:
            self.device_peer = peer
        elif interface == SERVICE_IFACE:
            self.service_peer = peer

        if not self.initial_announce_done:
            if self.pontoon and self.service_peer and self.device_peer:
                self.found_devices()
                self.initial_announce_done = True

    def found_devices(self):
        devices = []
        initiator_contact = self.device_peer.initiator_contact
        device_tube = self.device_peer.remote_object.tube
        service_tube = self.service_peer.remote_object.tube
        pontoon_devices = self.pontoon.get_devices()
        self.debug("%r devices registered in remote pontoon", len(pontoon_devices))
        for device_dict in pontoon_devices:
            device_path = device_dict["path"]
            self.debug("Getting object at %r from %r", device_path,
                       initiator_contact)
            proxy = device_tube.get_object(initiator_contact, device_path)
            try:
                infos = proxy.get_info(dbus_interface=DEVICE_IFACE)
            except Exception, exc:
                self.warning(exc)
                #import pdb; pdb.set_trace()
                continue
            service_proxies = []
            for service_path in device_dict["services"]:
                service_proxy = service_tube.get_object(initiator_contact,
                                                        service_path)
                service_proxies.append(service_proxy)
            proxy.services = service_proxies
            devices.append(proxy)
        self.got_devices_callback(devices)

class MirabeauTubeConsumer(MirabeauTubeConsumerMixin, client.Client):

    def __init__(self, connection, muc_id, found_peer_callback=None,
                 disapeared_peer_callback=None, got_devices_callback=None):
        MirabeauTubeConsumerMixin.__init__(self, found_peer_callback=found_peer_callback,
                                           disapeared_peer_callback=disapeared_peer_callback,
                                           got_devices_callback=got_devices_callback)
        client.Client.__init__(self, connection, muc_id)
