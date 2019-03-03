from switchyard.lib.userlib import *
import time 

def main(net):
    my_interfaces = net.interfaces() 
    mymacs = [intf.ethaddr for intf in my_interfaces]
    cache = {}

    while True:
        try:
            timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            return
	
        def helper(x):
            return x[1][1]

        if packet[0].src not in cache: #table does not contain entry for src address 
            if len(cache.keys()) >= 5:
                LRU = sorted(cache.items(), key=helper) 
                cache.pop(LRU[0][0], None)
            cache[packet[0].src] = (input_port, timestamp)                      

        log_debug ("In {} received packet {} on {}".format(net.name, packet, input_port))
        if packet[0].dst in mymacs:
            log_debug ("Packet intended for me")
        else:
            if packet[0].dst not in cache:  # check destination
                for intf in my_interfaces:  # flood the packet
                    if input_port != intf.name:
                        net.send_packet(intf.name, packet)
            else:  # update the cache and send
                cache[packet[0].dst] = (cache[packet[0].dst][0], time.time())
                net.send_packet(cache[packet[0].dst][0], packet)
    net.shutdown()
