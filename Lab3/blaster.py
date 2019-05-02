#!/usr/bin/env python3
from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from threading import *
import os
import time
from queue import Queue

class Blaster(object):
    def __init__(self, net, blaster_file):
        self.net = net
        self.num_packets = 0 
        self.length_variable_payload = 0 
        self.sender_window = 0 
        self.coarse_timeout = 0.0 
        self.recv_timeout = 0.0
        self.packet_window = []          
        self.parse(blaster_file) 
        self.intf = self.net.interface_by_name('blaster-eth0')
        self.lhs = 1
        self.rhs = 1
        self.retransmission_queue = Queue()
        self.num_coarse_timeouts = 0
        self.num_retrans_packets = 0
        self.total_packets_sent = 0


    def parse(self, blaster_file):
        with open(blaster_file, 'r') as f:
            tokens = f.read().strip().split(" ") 
            self.num_packets = int(tokens[1]) 
            self.length_variable_payload = int(tokens[3]) 
            self.sender_window = int(tokens[5]) 
            self.coarse_timeout = float(tokens[7])/1000
            self.recv_timeout = float(tokens[9])/1000
        self.packet_window = [False] * (int(self.num_packets) + 1) 
            
    def print_output(self, total_time, num_ret, num_tos, throughput, goodput):
        print("Total TX time (s): " + str(total_time))
        print("Number of reTX: " + str(num_ret))
        print("Number of coarse TOs: " + str(num_tos))
        print("Throughput (Bps): " + str(throughput))
        print("Goodput (Bps): " + str(goodput))


    def construct_packet(self, seq_num):
        pkt = Ethernet()  + IPv4(protocol=IPProtocol.UDP) + UDP() 
        pkt[UDP].src = 4444
        pkt[UDP].dst = 5555
        pkt += seq_num.to_bytes(4, 'big')
        pkt += self.length_variable_payload.to_bytes(2, 'big')
        pkt += os.urandom(self.length_variable_payload)
        return pkt

    def send_packet(self, seq_num):
        if seq_num == 1:
            self.first_packet_send_time = time.time()

        self.total_packets_sent += 1
        pkt = self.construct_packet(seq_num)
        self.net.send_packet(self.intf.name, pkt)

    def update_window(self):

        if (self.rhs - self.lhs + 1) <= self.sender_window and self.rhs <= self.num_packets and not self.packet_window[self.rhs]:
            log_info("SENT PKT " + str(self.rhs))
            self.send_packet(self.rhs)
            self.rhs += 1

    def deconstruct_packet(self, packet):
        contents = packet.get_header(RawPacketContents)
        seq_num = int.from_bytes(contents.data[:4], 'big')
        log_info("GOT ACK " + str(seq_num))

        self.packet_window[seq_num] = True
        if seq_num == self.lhs:
            while self.lhs < self.rhs and self.packet_window[self.lhs]:
                self.lhs += 1

            self.window_timestamp = time.time()

    def check_timeout(self):
        cur_time = time.time()
        if cur_time - self.window_timestamp > self.coarse_timeout:
            self.num_coarse_timeouts += 1
            for i, packet_sent in enumerate(self.packet_window[self.lhs:self.rhs]):
                if not packet_sent:
                    self.retransmission_queue.put(self.lhs + i)

            self.window_timestamp = time.time()

    def switchy_main(self):
        my_interfaces = self.net.interfaces()
        mymacs = [intf.ethaddr for intf in my_interfaces]
        self.window_timestamp = time.time()

        while True:
            gotpkt = True
            try:
                timestamp, dev, packet = self.net.recv_packet(timeout=self.recv_timeout)
                self.deconstruct_packet(packet)
                if (self.lhs == self.num_packets + 1):
                    self.last_packet_ackd_time = time.time()
                    print("End of transmission. Successfully received ACK for {} packets".format(self.num_packets))
                    raise Shutdown("Finished reliable transmission of all packets")

            except NoPackets:
                log_debug("No packets available in recv_packet")
                gotpkt = False
            except Shutdown:
                log_debug("Got shutdown signal")
                break

            if gotpkt:
                log_debug("I got a packet from {}".format(dev))
                log_debug("Pkt: {}".format(packet))

            self.check_timeout()
            retransmitted_packet = False
            while not self.retransmission_queue.empty():
                seq_num = self.retransmission_queue.get()
                if not self.packet_window[seq_num]:
                    self.num_retrans_packets += 1
                    log_info("Resending packet with seq_num %s" % seq_num)
                    self.send_packet(seq_num)
                    retransmitted_packet = True
                    break

            if not retransmitted_packet:
                self.update_window()

def main(net):
    blaster = Blaster(net, 'blaster_params.txt')
    log_info(vars(Blaster(net, 'blaster_params.txt')))
    blaster.switchy_main()
    total_time = blaster.last_packet_ackd_time - blaster.first_packet_send_time
    throughput = ((blaster.total_packets_sent * blaster.length_variable_payload) / total_time) 
    goodput = ((blaster.num_packets * blaster.length_variable_payload) / total_time) 
    blaster.print_output(total_time, blaster.num_retrans_packets, blaster.num_coarse_timeouts, throughput, goodput) 
    net.shutdown()
