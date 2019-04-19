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
from dynamicroutingmessage import DynamicRoutingMessage


class Q_Pkt(object):
    def __init__(self, time=None, retries=None, outport=None):
        self.pkt_list = []
        self.time = time
        self.retries = retries
        self.outport = outport 

    def addPkt(self, pkt):
        self.pkt_list.append(pkt) 
    
    def updateTime(self, val):
        self.time = val 

    def updateRetries(self, val):
        self.retries = val 

    def getPktList(self):
        return self.pkt_list

    def getTime(self):
        return self.time

    def getRetries(self):
        return self.retries

    def getOutport(self):
        return self.outport 


class Router(object):
    def __init__(self, net):
        self.net = net
        # other initialization stuff here
        self.my_interfaces = self.net.interfaces()
        self.ipaddrlist = [interfaces.ipaddr for interfaces in self.my_interfaces] 
        self.arp_table = {}
        self.router_table = []
        self.queue = {}
        self.dyn_table = []  

        f = open("forwarding_table.txt", "r")
        for row in f:
            item = row.rstrip().split(" ")
            prefix = item[0]
            mask = item[1]
            hop = item[2]
            outport = item[3] 
            self.router_table.append([IPv4Address(prefix), IPv4Address(mask), IPv4Address(hop), outport])
        for intf in self.my_interfaces:
            prefix = int(intf.ipaddr) & int(intf.netmask)
            self.router_table.append([IPv4Address(prefix),intf.netmask,None,intf.name])
     
    def queue_helper(self):
        remove_list = [] 
        for ip in self.queue:
            if time.time() - self.queue[ip].getTime() >= 1:
                if self.queue[ip].getRetries() >= 3: 
                    remove_list.append(ip) 
            else:
                output = self.queue[ip].getOutport()
                sender = self.net.interface_by_name(output) 
                self.net.send_packet(output, create_ip_arp_request(sender.ethaddr, sender.ipaddr, ip))
                self.queue[ip].updateTime(time.time()) 
                newRetries = self.queue[ip].getRetries() + 1 
                self.queue[ip].updateRetries(newRetries) 
        
        for val in remove_list:
            del self.queue[val] 
    
   
    def findMatch(self, pkt):  # return output port and next hop which can be None
       

        destaddr = pkt.get_header(IPv4).dst
        log_info(destaddr)     
        # check DYN first 
        log_info("MATCH TIME")
        dyn_index = None 
        dyn_longest = 0 

        for i in self.dyn_table:
            dyn_network = IPv4Network(str(i[0].advertised_prefix) + '/' + str(i[0].advertised_mask))
            
            if destaddr in dyn_network:
                log_info("DYN MATCH") 
                pre = dyn_network.prefixlen
                dyn_longest = pre
                dyn_index = i 
    
        index = None
        longest = 0
        log_info(self.router_table) 
        for row in self.router_table:
            network = IPv4Network(str(row[0])+'/'+str(row[1]))

            if destaddr in network:
                pre = network.prefixlen
                if pre > longest:
                    longest = pre
                    index = row
       
        if destaddr in self.ipaddrlist: #drop packet 
            return None, None 
        
        log_info(dyn_index)
        log_info(dyn_index[1]) 
        log_info(dyn_index[0])  
        if dyn_index:
            return dyn_index[1], dyn_index[0].next_hop 


        if index is None:
            return None, None
        else:
            if index[2] is None:
                log_info("NO HOP CASE")
                log_info(index[3]) 
                return index[3], destaddr
            else:
                log_info("HOP CASE") 
                return index[3], index[2]

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
                dyn = pkt.get_header(DynamicRoutingMessage) 
                if dyn is not None:
                    log_info("DYN") 
                    self.dyn_table.append([dyn,dev]) # dev is the input port of the packet
                    log_info(self.dyn_table)
                    log_info(len(self.dyn_table)) 
                    if len(self.dyn_table) > 5:
                        log_info("POPPING DYN")
                        self.dyn_table.pop(0)
    
                if arp is not None:
                    log_info("ARP PACKET") 
                    if arp.operation == ArpOperation.Request:
                        log_info("ARP REQUEST RECEIVED") 
                        if arp.targetprotoaddr in self.ipaddrlist:
                            log_info("SENDING ARP REPLY") 
                            ethsrc = self.net.interface_by_ipaddr(arp.targetprotoaddr)  
                            reply_pkt = create_ip_arp_reply(ethsrc.ethaddr, arp.senderhwaddr, arp.targetprotoaddr, arp.senderprotoaddr)
                            self.net.send_packet(dev, reply_pkt)
                    if arp.operation == ArpOperation.Reply:  # this should probably change to arp.operation == ArpOperation.Reply
                        log_info("ARP REPLY RECEIVED")
                        if arp.targetprotoaddr in self.ipaddrlist:
                            self.arp_table[arp.senderprotoaddr] = arp.senderhwaddr
                        log_info("SENDING ARP REPLY - QUEUE")                         
                        if arp.senderprotoaddr in self.queue:
                            k = arp.senderprotoaddr 
                            dest_port = self.queue[k].getOutport() 
                            for packet in self.queue[k].getPktList(): 
                                 if not packet.get_header(Ethernet):
                                      packet += Ethernet()
                                 packet[Ethernet].src = self.net.interface_by_name(dest_port).ethaddr
                                 log_info("CLEARS ETHADDR") 
                                 packet[Ethernet].dst = arp.senderhwaddr
                                 log_info("CLEARS DST = K") 
                                 self.net.send_packet(dest_port, packet)  
                                 log_info("CLEARS SEND") 
                            del self.queue[k]
                
                self.queue_helper() 

                if ipv4 is not None:  # handling ipv4 packet
                    log_info("IPv4") 
                    outport, nxthop = self.findMatch(pkt)  # return None, None when there is no hit, or the dst is for the router

                    if outport is not None:  # pkt has found a hit from the table
                        port = self.net.interface_by_name(outport)
                        ipv4.ttl = ipv4.ttl - 1

                        if nxthop in self.arp_table:  # if in the table then use it
                            if not pkt.get_header(Ethernet): 
                                pkt += Ethernet() 
                            pkt[Ethernet].src = port.ethaddr
                            pkt[Ethernet].dst = self.arp_table[nxthop]
                            self.net.send_packet(outport, pkt)
                        else:  # ARP querry
                            if nxthop in self.queue:
                                self.queue[nxthop].addPkt(pkt) 
                            log_info("HERE")
                            log_info(outport)
                            log_info(nxthop)  
                            self.net.send_packet(outport, create_ip_arp_request(port.ethaddr, port.ipaddr, nxthop))
                            # add it to queue
                            log_info("ADDING TO QUEUE") 
                            queue_entry = Q_Pkt(time.time(), 1, outport) 
                            queue_entry.addPkt(pkt) 
                            self.queue[nxthop] = queue_entry
                    else:  # otherwise drop the pkt
                        log_info("ipv4 packt has been dropped")
            except NoPackets:
                log_debug("No packets available in recv_packet")
                gotpkt = False
            except Shutdown:
                log_debug("Got shutdown signal")
                break

            if gotpkt:
                log_debug("Got a packet: {}".format(str(pkt)))
            else:
                self.queue_helper() 

def main(net):
    '''
    Main entry point for router.  Just create Router
    object and get it going.
    '''
    r = Router(net)
    r.router_main()
    net.shutdown()

