#!/usr/bin/env python3

'''
Basic IPv4 router (static routing) in Python.
'''

import sys
import os
import time

from switchyard.lib.packet.util import *
from switchyard.lib.userlib import *

class Router(object):
    def __init__(self, net):
        self.net = net
        # other initialization stuff here
        self.my_interfaces = self.net.interfaces()
        self.ipaddrlist = [interfaces.ipaddr for interfaces in self.my_interfaces] 
        self.arp_table = {} 

    def router_main(self):    
        '''
        Main method for router; we stay in a loop in this method, receiving
        packets until the end of time.
        '''
        while True:
            gotpkt = True
            try:
                timestamp,dev,pkt = self.net.recv_packet(timeout=1.0)
                log_info(self.ipaddrlist) 
                arp = pkt.get_header(Arp) 
                if (arp is not None):
                    log_info("ARP PACKET") 
                    if(arp.operation == ArpOperation.Request):
                        log_info("ARP REQUEST RECEIVED") 
                        if arp.targetprotoaddr in self.ipaddrlist:
                            log_info("SENDING ARP REPLY") 
                            ethsrc = self.net.interface_by_ipaddr(arp.targetprotoaddr)  
                            reply_pkt = create_ip_arp_reply(ethsrc.ethaddr, arp.senderhwaddr, arp.targetprotoaddr, arp.senderprotoaddr) 
                            self.net.send_packet(dev, reply_pkt) 
                    else:  # this should probably change to arp.operation == ArpOperation.Reply
                        log_info("ARP REPLY RECEIVED")
                        if arp.targetprotoaddr in self.ipaddrlist:
                            self.arp_table[arp.senderprotoaddr] = arp.senderhwaddr
                            log_info(self.arp_table) 
                else:
                    log_info("DROPPED PACKET")                      
            except NoPackets:
                log_debug("No packets available in recv_packet")
                gotpkt = False
            except Shutdown:
                log_debug("Got shutdown signal")
                break

            if gotpkt:
                log_debug("Got a packet: {}".format(str(pkt)))



def main(net):
    '''
    Main entry point for router.  Just create Router
    object and get it going.
    '''
    r = Router(net)
    r.router_main()
    net.shutdown()
