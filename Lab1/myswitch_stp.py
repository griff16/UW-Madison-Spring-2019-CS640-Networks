from switchyard.lib.userlib import *
from spanningtreemessage import *
from time import sleep

def mk_stp_pkt(root_id, hops, hwsrc="20:00:00:00:00:01", hwdst="ff:ff:ff:ff:ff:ff"):
    spm = SpanningTreeMessage(root=root_id, hops_to_root=hops)
    Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
    pkt = Ethernet(src=hwsrc,
                   dst=hwdst,
                   ethertype=EtherType.SLOW) + spm
    xbytes = pkt.to_bytes()
    p = Packet(raw=xbytes)
    return p

def flood (input_port, my_interfaces, net, packet):
    for intf in my_interfaces:  # flood the packet
        if input_port != intf.name:
            net.send_packet(intf.name, packet)

def minMac (mymacs):  # return the lowest mac addr in the switch
    minMac = ethaddr()
    for min in mymacs:
        if minMac < min:
            minMac = min
    return minMac

def main (net):
    my_interfaces = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_interfaces]
    mode = {}
    id = minMac(mymacs)
    hops = 0

    # creating the header
    # spm = SpanningTreeMessage(id)
    # spm.hops_to_root("0")
    # pkt = Ethernet(src="11:22:11:22:11:22", dst="22:33:22:33:22:33", ethertype=EtherType.SLOW) + spm
    pkt = mk_stp_pkt(id, hops)

    # flood the STP
    for intf in my_interfaces:  # flood the packet
        net.send_packet(intf.name, pkt)
    # do we need to add recive packet here?
    sleep(2)

    while True:
        try:
            timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            return

        if packet.has_header(SpanningTreeMessage) == False:
            flood(input_port, my_interfaces, net, packet)
        else:
            if packet[1].root() < id:
                id = packet[1].root()
                # update hops?
                packet[1].hops_to_root(packet[1].hops_to_root())
                mode[input_port] = True
                flood(input_port, my_interfaces, net, packet)
            else:
                pass

