from switchyard.lib.userlib import *
from spanningtreemessage import *
import time 

def mk_stp_pkt(root_id, hops, hwsrc="20:00:00:00:00:01", hwdst="ff:ff:ff:ff:ff:ff"):
    spm = SpanningTreeMessage(root=root_id, hops_to_root=hops)
    Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
    pkt = Ethernet(src=hwsrc,
                   dst=hwdst,
                   ethertype=EtherType.SLOW) + spm
    xbytes = pkt.to_bytes()
    p = Packet(raw=xbytes)
    return p

def helper (input_port, my_interfaces, net, mode, packet, option):  # helper method to flood packets
    log_info("HELPER SECTIONNNNNNNNNNNNNNNNNNNNNNNNNNN")
    log_info("inputport:"+ str(input_port))
    log_info("mode:"+str(mode))
    log_info("helper method packet:"+str(packet))
    if option == 1:
        packet[0].src = "20:00:00:00:00:01"
    for intf in my_interfaces:
        if input_port == None or (input_port != intf.name and mode[input_port]):
            net.send_packet(intf.name, packet)

def flood (input_port, my_interfaces, mymacs, net, packet, cache, mode, option):  # handle mode situation
    log_info("FLODDDDDDDDDDDDDDDDD SECTIONNNNNNNNNNNNNNNNNNNNN")
    if option == 0:  # pkt is regular pkt
        log_info("pkt is regular pkt!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        if packet[0].dst in mymacs:
            log_debug ("Packet intended for me")
        else:
            if packet[0].src in cache:  # check src
                if input_port != cache[packet[0].src]:  # when the port is not the same
                    cache[packet[0].src] = input_port
            else:  # table does not contain entry for src address
                if len(cache) == 5:
                    cache.pop(list(cache)[0])
                cache[packet[0].src] = input_port

            log_info("sendinggggggggg out packet:" + str(packet))
            if packet[0].dst not in cache or packet[0].dst == "FF:FF:FF:FF:FF:FF":  # check destination
                log_info("not in cache case")
                log_info(packet[0].dst)
                helper(input_port, my_interfaces, net, mode, packet, option)  # flood it
            else:  # update the cache and send
                log_info("update cache case")
                cache[packet[0].dst] = cache.pop(packet[0].dst)
                net.send_packet(cache[packet[0].dst], packet)
    else:  # pkt is stp packet
        log_info("pkt is stp packet !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        helper(input_port, my_interfaces, net, mode, packet, option)  # flood it

def minMac (mymacs):  # return the lowest mac addr in the switch
    result = mymacs[0]
    for min in mymacs:
        if result > min:
            result = min
    return result

def main (net):
    my_interfaces = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_interfaces]

    sent = time.time()
    id = minMac(mymacs)  # own id
    rootID = id          # possibile rootID
    hops = 0             # keeping track of hops
    inPort = None        # keeping track of the inputPort of the root
    cache = dict()       # for regular packet use
    mode = {}            # initializing ports to forwarding mode
    for intf in my_interfaces:
        mode[intf.name] = True

    pkt = mk_stp_pkt(rootID, hops)  # creating the header
    for intf in  my_interfaces:
        net.send_packet(intf, pkt)

    while True:
        try:
            timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            if rootID == id and time.time() - sent >= 2:
                log_info("NO PACKET CASE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1")
                p = mk_stp_pkt(rootID, hops)
                log_info("packet:"+str(p))
                helper(None, my_interfaces, net, mode, p, 1)  # regular packet, flood with 0
            continue
        except Shutdown:
            return

        log_info("PACKET:"+str(packet))
        log_info("has header:"+str(packet.has_header(SpanningTreeMessage)))
        log_info("input:"+str(input_port))
        log_info("mode:"+str(mode))
        log_info("cache:"+str(cache))
        log_info("rootID:"+str(rootID))
        log_info("hops:"+ str(hops))
        log_info("port stored:"+str(inPort))

        if not packet.has_header(SpanningTreeMessage):                           # when the packet is a regular pkt
            log_info("CASE OF REG PACKET!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            flood(input_port, my_interfaces, mymacs, net, packet, cache, mode, option=0)  # regular packet, flood with 0
        else:
            log_info("CASE OF STP PACKET!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            if packet[1].root < rootID:
                log_info("NEW ROOT CASE root < rootID!!!!!!!!!!!!!!!!!!!!!")
                packet[1].hops_to_root = packet[1].hops_to_root + 1  # update packet root
                rootID = packet[1].root                         # update rootID
                inPort = input_port                               # update input_port
                mode[input_port] = True                           # set the port to true
                hops = packet[1].hops_to_root                   # update switch hops
                log_info("after modifying rootID:" + str(rootID))
                log_info("after modifying hops:" + str(hops))
                flood(input_port, my_interfaces, mymacs, net, packet, cache, mode, option=1)
            elif packet[1].root == rootID:
                log_info("ROOT ====== rootID")
                if packet[1].hops_to_root + 1 < hops:
                    log_info("UPDATE HOPS!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    packet[1].hops_to_root = packet[1].hops_to_root + 1  # update packet root
                    mode[input_port] = True                           # set the port to true
                    hops = packet[1].hops_to_root                   # update switch hops
                    flood(input_port, my_interfaces, mymacs, net, packet, cache, mode, option=1)
                elif packet[1].hops_to_root + 1 == hops and input_port != inPort:
                    log_info("BLOCKING SECTION")
                    log_info("BEFORE BLOCKING mode:"+ mode)
                    mode[input_port] = False
                    log_info("AFTER BLOCKING mode:"+ mode)
    net.shutdown()
