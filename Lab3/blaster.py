#!/usr/bin/env python3

import os
from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from queue import Queue
from random import randint
import time


class Blaster(object):
    def __init__(self, net, file):
        self.net = net
        self.parsing(file)
        self.num = 0
        self.length = 0
        self.sw = 0
        self.ctimeouts = 0  # coarse_timeouts
        self.rtimeouts = 0  # recv_timeouts
        self.q = Queue()
        self.lhs = 1
        self.rhs = 1
        self.total = 0  # number of packets totally sent
        self.map = {}
        self.intf = self.net.interface_by_name('blaster-eth0')
        self.midboxeth = EthAddr('40:00:00:00:00:01')

    def parsing(self, file):
        with open(file, 'r') as f:
            tokens = f.read().strip().split(" ")
            self.num = tokens[1]
            self.length = tokens[3]
            self.sw = tokens[5]
            self.timeouts = tokens[7]
            self.rtimeouts = tokens[9]

    def mkPkt(self, seqNum):
        pkt = Ethernet(src=self.intf.ethaddr, dst=self.midboxeth) + IPv4(src=self.intf.ipaddr, dst="192.168.100.2") + UDP()
        pkt += seqNum.to_bytes(4, 'big')
        pkt += self.length_variable_payload.to_bytes(2, 'big')
        pkt += os.urandom(self.length_variable_payload)
        return pkt

    def forward(self, seqNum):
        pkt = self.mkPkt(seqNum)
        self.map[pkt] = time.time()
        self.net.send_packet("blaster-eth0", pkt)
        self.rhs += 1
        self.total += 1

    def check(self):
        if self.rhs - self.lhs <= self.sw and self.rhs <= self.total:
            return True
        else:
            return False

    def print_output(total_time, num_ret, num_tos, throughput, goodput):
        print("Total TX time (s): " + str(total_time))
        print("Number of reTX: " + str(num_ret))
        print("Number of coarse TOs: " + str(num_tos))
        print("Throughput (Bps): " + str(throughput))
        print("Goodput (Bps): " + str(goodput))

    def switchy_main(self):
        my_intf = self.net.interfaces()
        mymacs = [intf.ethaddr for intf in my_intf]
        myips = [intf.ipaddr for intf in my_intf]

        while True:
            gotpkt = True
            try:
                #Timeout value will be parameterized!
                timestamp,dev,pkt = self.net.recv_packet(timeout=self.rtimeouts)

            

            except NoPackets:
                log_debug("No packets available in recv_packet")
                gotpkt = False
            except Shutdown:
                log_debug("Got shutdown signal")
                break

            while not self.q.empty():
                pass

            if self.check():
                self.forward(self.rhs)

def main(net):
    b = Blaster(net, 'blaster.txt')
    b.switchy_main()
    b.print_output()
    net.shutdown()
