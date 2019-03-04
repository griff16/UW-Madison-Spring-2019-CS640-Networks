# class MySwitch:
#      def __init__(self, switch_id, net):
#             self.switch_id = "FF:FF:FF:FF:FF:FF"
#             self.net = net
#             self.root = self.switch_id
#             self.hops = 0
#
#
#      def make_pkt(self, hops, source, dest):
#             spm = SpanningTreeMessage("00:11:22:33:44:55", hops_to_root=hops)
#             Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
#             pkt = Ethernet(src=source,
#                            dst=dest,
#                            ethertype=EtherType.SLOW) + spm
#             xbytes = pkt.to_bytes()
#             p = Packet(raw=xbytes)
#             return p
#
#       def flood(self):
#             packet = self.make_pkt(0, "eth0", "FF:FF:FF:FF:FF:FF")
#
#             interfaces = self.net.interfaces()
#             for intf in interfaces:
#                 self.net.send_packet(intf.name, packet)
#
#       def forward(self, packet):
#             if packet[0] == self.root:
#                 continue
