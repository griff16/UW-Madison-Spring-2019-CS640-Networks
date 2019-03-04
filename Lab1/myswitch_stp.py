from switchyard.lib.userlib import *
from spanningtreemessage import *
from time import sleep

def mk_stp_pkt(root_id, hops, hwsrc="20:00:00:00:00:01", hwdst="ff:ff:ff:ff:ff:ff"):
    spm = SpanningTreeMessage(root=root_id, hops_to_root=hops)
    pkt = Ethernet(src=hwsrc,
                   dst=hwdst,
                   ethertype=EtherType.SLOW) + spm
    xbytes = pkt.to_bytes()
    p = Packet(raw=xbytes)
    return p

def flood (input_port, my_interfaces, net, packet):  # handle mode situation
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
                packet[1].hops_to_root(packet[1].hops_to_root())  # update packet root
                id = packet[1].root()  # update root id
                hops = packet[1].hops_to_root()  # update switch hops
                mode[input_port] = True  # set the port to true
                flood(input_port, my_interfaces, net, packet)
            elif packet[1].root() == id:
                if packet[1].hops_to_root() + 1 < hops:
                    mode[input_port] = True  # set the port to true
                    packet[1].hops_to_root(packet[1].hops_to_root())  # update packet root
                    hops = packet[1].hops_to_root()  # update switch hops
                    flood(input_port, my_interfaces, net, packet)
                elif packet[1].hops_to_root() + 1 > hops:
                    pass
                else:
                    if input_port in mode:  # this mode check fix me?
                        mode[input_port] = False
        sleep(2)
    net.shutdown()
