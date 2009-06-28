from telepathy.interfaces import CHANNEL_INTERFACE, CONNECTION_INTERFACE_REQUESTS, \
     CHANNEL_TYPE_DBUS_TUBE
from telepathy.constants import CONNECTION_HANDLE_TYPE_ROOM, \
     SOCKET_ACCESS_CONTROL_CREDENTIALS

from coherence.extern.telepathy.client import Client

class TubePublisher(Client):
    logCategory = "tube_publisher"

    def __init__(self, manager, protocol, account, muc_id, tubes_to_offer):
        Client.__init__(self, manager, protocol, account, muc_id)
        self._tubes_to_offer = tubes_to_offer

    def muc_joined(self):
        super(TubePublisher, self).muc_joined()
        self.info("muc joined. Offering the tubes")

        for interface in self._tubes_to_offer.keys():
            self.conn[CONNECTION_INTERFACE_REQUESTS].CreateChannel({
                CHANNEL_INTERFACE + ".ChannelType": CHANNEL_TYPE_DBUS_TUBE,
                CHANNEL_INTERFACE + ".TargetHandleType": CONNECTION_HANDLE_TYPE_ROOM,
                CHANNEL_INTERFACE + ".TargetID": self.muc_id,
                CHANNEL_TYPE_DBUS_TUBE + ".ServiceName": interface})

    def got_tube(self, tube):
        super(TubePublisher, self).got_tube(tube)
        initiator_handle = tube.props[CHANNEL_INTERFACE + ".InitiatorHandle"]
        if initiator_handle == self.self_handle:
            self.info("offering my tube located at %r", tube.object_path)
            service_name = tube.props[CHANNEL_TYPE_DBUS_TUBE + ".ServiceName"]
            params = self._tubes_to_offer[service_name]
            address = tube[CHANNEL_TYPE_DBUS_TUBE].Offer(params,
                                                         SOCKET_ACCESS_CONTROL_CREDENTIALS)
            tube.local_address = address
            self.info("local tube address: %r", address)

class TubeConsumer(Client):
    logCategory = "tube_consumer"

    def __init__(self, manager, protocol,
                 account, muc_id, found_peer_callback=None,
                 disapeared_peer_callback=None, existing_client=False):
        Client.__init__(self, manager, protocol,
                        account, muc_id, existing_client=existing_client)
        self.found_peer_callback = found_peer_callback
        self.disapeared_peer_callback = disapeared_peer_callback

    def got_tube(self, tube):
        super(TubeConsumer, self).got_tube(tube)
        if self.pre_accept_tube(tube):
            self.info("accepting tube %r", tube.object_path)
            tube_iface = tube[CHANNEL_TYPE_DBUS_TUBE]
            tube.local_address = tube_iface.Accept(SOCKET_ACCESS_CONTROL_CREDENTIALS)
        else:
            self.warning("tube %r not allowed", tube)

    def pre_accept_tube(self, tube):
        return True

    def tube_closed_cb(self, tube):
        self.disapeared_peer_callback(tube)
        super(TubeConsumer, self).tube_closed_cb(tube)
