#!/usr/bin/env python3

'''
Basic IPv4 router (static routing) in Python.
'''

import sys
import os
import time
from switchyard.lib.address import *

from switchyard.lib.packet.util import *
from switchyard.lib.userlib import *

class Router(object):
    def __init__(self, net):
        self.net = net
        # other initialization stuff here
        self.my_interfaces = self.net.interfaces()
        self.ipaddrlist = [interfaces.ipaddr for interfaces in self.my_interfaces] 
        self.arp_table = {}
        f = open("forwarding_table.txt", "r")
        self.router_table = []
        for row in f:
            self.router_table.append(row.rstrip().split(" "))

    def findMatch(self, pkt):
        destaddr = IPv4Address(pkt.hey_header(Ethernet).dst)
        index = None

        for row in self.router_table:
            prefix = IPv4Address(row[0])
            if (int(row[1]) & int(destaddr)) == int(prefix):
                index = row
        return row[-1], row[-2] if index is not None else None, None

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
                ipv4 = pkt.get_header(IPv4)

                if arp is not None:
                    log_info("ARP PACKET") 
                    if arp.operation == ArpOperation.Request:
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
                elif ipv4 is not None:  # handling ipv4 packet
                    outport, nxthop = self.findMatch(pkt)
                    if nxthop is not None or nxthop is not None:  # otherwise drop the pkt
                        ipv4.ttl = ipv4.ttl - 1

                        if nxthop in self.arp_table:  # if in the table then use it
                            pkt = ipv4 + Ethernet(src=self.net.interface_by_name(outport).ethaddr, dst=self.arp_table[nxthop], ethertype = Ethernet.IPv4)
                            self.net.send_packet(outport, pkt)
                        else:  # ARP querry
                            ethsrc = self.net.interface_by_name(outport)
                            reply_pkt = create_ip_arp_request(ethsrc.ethaddr, "2", nxthop)

                            # create Eth header
                            ethHeader = Ethernet(ethsrc.ethaddr, dst = reply_pkt.get_header(Arp).senderprotoaddr, ethertype=EtherType.IPv4)

                            # send the pkt that has IPv4 and new Eth header
                            self.net.send_packet(outport, ethHeader+ipv4)

                    print("")
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
