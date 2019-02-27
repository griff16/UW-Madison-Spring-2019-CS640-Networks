'''
Ethernet learning switch in Python.

Note that this file currently has the code to implement a "hub"
in it, not a learning switch.  (I.e., it's currently a switch
that doesn't learn.)
'''
from switchyard.lib.userlib import *

def main(net):
    my_interfaces = net.interfaces() 
    mymacs = [intf.ethaddr for intf in my_interfaces]
    cache = dict()

    while True:
        try:
            timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            return

        log_debug ("In {} received packet {} on {}".format(net.name, packet, input_port))
        if packet[0].dst in mymacs:
            log_debug ("Packet intended for me")
        else:
            if packet[0].src in cache:  # check src
                if input_port != cache[packet[0].src]:  # when the port is the same
                    cache[packet[0].src] = input_port
            else:  # table does not contain entry for src address
                if len(cache) == 5:
                    cache.pop(list(cache)[0])
                cache[packet[0].src] = input_port

            if packet[0].dst not in cache:  # check destination
                for intf in my_interfaces:  # flood the packet
                    if input_port != intf.name:
                        net.send_packet(intf.name, packet)
            else:  # update the cache and send
                cache[packet[0].dst] = cache.pop(cache[packet[0].dst])
                net.send_packet(cache[packet[0].dst], packet)
    net.shutdown()
