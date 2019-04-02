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
        self.router_table = []
        self.queue = []

        f = open("forwarding_table.txt", "r")
        for row in f:
            self.router_table.append(row.rstrip().split(" "))
        for intf in self.my_interfaces:
            prefix = int(intf.ipaddr) & int(intf.netmask)
            self.router_table.append([IPv4Address(prefix),intf.netmask,None,intf.name])

    def findMatch(self, pkt):  # return output port and next hop which can be None
        destaddr = IPv4Address(pkt.get_header(IPv4).dst)
        index = None
        longest = -1

        if destaddr in self.ipaddrlist:  # drop packet case
            return None, None

        for row in self.router_table:
            tokens = row.split(" ")
            netowork = IPv4Address(tokens[0]+"/"+tokens[1])

            if destaddr in netowork:
                if netowork.prefixlen > longest:
                    longest = netowork.prefixlen
                    index = tokens

        if index is None:
            return None, None
        else:
            if len(index) == 3:
                return row[-1], destaddr
            else:
                return row[-1], row[-2]

    def router_main(self):
        '''
        Main method for router; we stay in a loop in this method, receiving
        packets until the end of time.
        '''
        while True:
            gotpkt = True
            try:
                timestamp,dev,pkt = self.net.recv_packet(timeout=1.0)
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
                    outport, nxthop = self.findMatch(pkt)  # return None, None when there is no hit, or the dst is for the router

                    if outport is not None:  # pkt has found a hit from the table
                        port = self.net.interface_by_name(outport)
                        ipv4.ttl = ipv4.ttl - 1

                        if nxthop in self.arp_table:  # if in the table then use it
                            pkt[Ethernet].src = port.ethaddr
                            pkt[Ethernet].dst = self.arp_table[nxthop]
                            self.net.send_packet(outport, pkt)
                        else:  # ARP querry
                            self.net.send_packet(outport, create_ip_arp_request(port.ethaddr, port.ipaddr, nxthop))

                            # count = 1
                            # while count <= 3:
                            #     try:
                            #         timestamp,inport,packet = self.net.recv_packet(timeout=1.0)
                            #
                            #         # create Eth header
                            #         ethHeader = Ethernet(ethsrc.ethaddr, dst=packet.get_header(Arp).senderhwaddr, ethertype=EtherType.IPv4)
                            #
                            #         # send the pkt that has IPv4 and new Eth header
                            #         self.net.send_packet(outport, ethHeader+ipv4)
                            #     except NoPackets:
                            #         count = count + 1
                            #         log_debug("No packets available from arp request")
                    else:  # otherwise drop the pkt
                        log_info("ipv4 packt has been dropped")
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
