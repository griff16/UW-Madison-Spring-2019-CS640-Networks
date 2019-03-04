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

def helper (input_port = None, my_interfaces = None, net = None, mode={}, packet=None):  # helper method to flood packets
    for intf in my_interfaces:
        if input_port == None or (input_port != intf.name and mode[input_port]):
            net.send_packet(intf.name, packet)

def flood (input_port, my_interfaces, mymacs, net, packet, cache, mode, option):  # handle mode situation
    if option == 0:  # pkt is regular pkt
        if packet[0].dst in mymacs:
            log_debug ("Packet intended for me")
        else:
            log_info(packet[0].src, packet[0].dst)
            if packet[0].src in cache:  # check src
                if input_port != cache[packet[0].src]:  # when the port is not the same
                    cache[packet[0].src] = input_port
            else:  # table does not contain entry for src address
                if len(cache) == 5:
                    cache.pop(list(cache)[0])
                cache[packet[0].src] = input_port

            if packet[0].dst not in cache or packet[0].dst == "FF:FF:FF:FF:FF:FF":  # check destination
                helper(input_port, my_interfaces, net, packet)  # flood it
            else:  # update the cache and send
                cache[packet[0].dst] = cache.pop(packet[0].dst)
                net.send_packet(cache[packet[0].dst], packet)
    else:  # pkt is stp packet
        helper(input_port, my_interfaces, net, packet)  # flood it

    sleep(2)

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
    rootID = id          # possibile rootID
    hops = 0             # keeping track of hops
    inPort = None        # keeping track of the inputPort of the root
    cache = dict()       # for regular packet use
    mode = {}            # initializing ports to forwarding mode
    for intf in my_interfaces:
        mode[intf] = True

    pkt = mk_stp_pkt(rootID, hops)  # creating the header
    for intf in  my_interfaces:
        net.send_packets(intf, pkt)

    while True:
        try:

            timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            if rootID == id:
                flood(input_port, my_interfaces, mymacs, net, pkt, cache, option=1)  # regular packet, flood with 0
            sleep(2)
            continue
        except Shutdown:
            return

        if not packet.has_header(SpanningTreeMessage):                           # when the packet is a regular pkt
            flood(input_port, my_interfaces, mymacs, net, pkt, cache, mode, option=0)  # regular packet, flood with 0
        else:
            if packet[1].root() < rootID:
                packet[1].hops_to_root(packet[1].hops_to_root())  # update packet root
                rootID = packet[1].root()                         # update rootID
                inPort = input_port                               # update input_port
                mode[input_port] = True                           # set the port to true
                hops = packet[1].hops_to_root()                   # update switch hops
                flood(input_port, my_interfaces, mymacs, net, pkt, cache, mode, option=1)
            elif packet[1].root() == rootID:
                if packet[1].hops_to_root() + 1 < hops:
                    packet[1].hops_to_root(packet[1].hops_to_root())  # update packet root
                    mode[input_port] = True                           # set the port to true
                    hops = packet[1].hops_to_root()                   # update switch hops
                    flood(input_port, my_interfaces, mymacs, net, pkt, cache, mode, option=1)
                elif packet[1].hops_to_root() + 1 == hops and input_port != inPort:
                    mode[input_port] = False
            sleep(2)
    net.shutdown()
