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

def flood (input_port, my_interfaces, net, packet, cache, option):  # handle mode situation
    if option == 0:
        pass
    else:
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

    id = minMac(mymacs)  # own id
    rootID = id
    hops = 0  # keeping track of hops
    inPort = None  # keeping track of the inputPort of the root
    cache = dict()  # for regular packet use
    mode = {}  # initializing ports to forwarding mode
    for intf in my_interfaces:
        mode[intf] = True

    while True:
        try:
            pkt = mk_stp_pkt(rootID, hops)  # creating the header
            timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            if rootID == id:
                flood(input_port, my_interfaces, net, pkt, cache, option=1)  # regular packet, flood with 0
            sleep(2)
            continue
        except Shutdown:
            return

        if not packet.has_header(SpanningTreeMessage):  # when the packet is a regular pkt
            flood(input_port, my_interfaces, net, pkt, cache, option=0)  # regular packet, flood with 0
        else:
            if packet[1].root() < rootID:
                packet[1].hops_to_root(packet[1].hops_to_root())  # update packet root
                rootID = packet[1].root()  # update rootID
                inPort = input_port  # update input_port
                mode[input_port] = True  # set the port to true
                hops = packet[1].hops_to_root()  # update switch hops
                flood(input_port, my_interfaces, net, pkt, cache, option=1)
            elif packet[1].root() == rootID:
                if packet[1].hops_to_root() + 1 < hops:
                    packet[1].hops_to_root(packet[1].hops_to_root())  # update packet root
                    mode[input_port] = True  # set the port to true
                    hops = packet[1].hops_to_root()  # update switch hops
                    flood(input_port, my_interfaces, net, pkt, cache, option=1)
                elif packet[1].hops_to_root() + 1 == hops and input_port != inPort:
                    mode[input_port] = False
            sleep(2)
    net.shutdown()
