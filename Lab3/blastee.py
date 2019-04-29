#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from threading import *
import time

def switchy_main(net):
    my_interfaces = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_interfaces]

    while True:
        gotpkt = True
        try:
            timestamp,dev,pkt = net.recv_packet()
            log_debug("Device is {}".format(dev))

            # extract seq and data from recieved packet  
            raw = pkt.get_header(RawPacketContents)
            seq = int.from_bytes(raw.data[:4], 'big') 
#            data = b64encode(raw.data[6:]).decode('utf-8') # can use to test if correct pkt 
            
            # construct ACK packet and send to middlebox 
            ack_pkt = Ethernet() + IPv4() + UDP()
            ack_pkt[1].protocol = IPProtocol.UDP

            ack_pkt += seq.to_bytes(4, 'big') 
            net.send_packet(dev, ack_pkt) 
            
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet from {}".format(dev))
            log_debug("Pkt: {}".format(pkt))


    net.shutdown()
