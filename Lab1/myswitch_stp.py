from switchyard.lib.userlib import *
from spanningtreemessage import *

class MySwitch_stp:
    def __init__(self, root, hops_to_root = 0):
        self.curRoot = root
        self.hopsToRoot = hops_to_root




def minMac (mymacs):  # return the lowest mac addr in the switch
    minMac = "FF:FF:FF:FF:FF:FF"
    for min in mymacs:
        if minMac < min:
            minMac = min
    return minMac

def main (net):
    my_interfaces = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_interfaces]

    min = minMac(mymacs)

    # creating the header
    spm = SpanningTreeMessage(min)
    Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
    pkt = Ethernet(src="11:22:11:22:11:22", dst="22:33:22:33:22:33", ethertype=EtherType.SLOW) + spm

    # flood the STP
    for intf in my_interfaces:  # flood the packet
        net.send_packet(intf.name, packet)
