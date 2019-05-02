import os
import time
from queue import Queue
from switchyard.lib.userlib import *

class Blaster(object):
    def __init__(self, net, params_file):
        self.net = net
        self.parse_params(params_file)
        self.intf = self.net.interface_by_name('blaster-eth0')
        self.middlbox_eth = EthAddr('40:00:00:00:00:01')
        self.lhs, self.rhs = 1, 1
        self.retransmission_queue = Queue()
        self.num_coarse_timeouts = 0
        self.num_retrans_packets = 0
        self.total_packets_sent = 0

    def parse_params(self, params_file):
        params_map = {
            '-b': {'name': 'blastee_ip', 'type': IPv4Address},
            '-n': {'name': 'num_packets', 'type': int},
            '-l': {'name': 'length_variable_payload', 'type': int},
            '-w': {'name': 'sender_window', 'type': int},
            '-t': {'name': 'coarse_timeout', 'type': float},
            '-r': {'name': 'recv_timeout', 'type': float}
        }
        with open(params_file, 'r') as fp:
            params = fp.readline().strip().split()
            while '' in params:
                params.remove('')
            i = 0
            while i < len(params):
                if params[i] in params_map:
                    setattr(self, params_map[params[i]]['name'],
                            params_map[params[i]]['type'](params[i + 1]))
                    if params[i] in ['-t', '-r']:
                        attr = getattr(self, params_map[params[i]]['name'])
                        setattr(self, params_map[params[i]]['name'], attr / 1000)

                    if params[i] == '-n':
                        self.packet_window = [False] * (self.num_packets + 1)
                    i += 2
                    continue
                i += 1

    def print_output(self, total_time, num_ret, num_tos, throughput, goodput):
        print("Total TX time (s): " + str(total_time))
        print("Number of reTX: " + str(num_ret))
        print("Number of coarse TOs: " + str(num_tos))
        print("Throughput (Bps): " + str(throughput))
        print("Goodput (Bps): " + str(goodput))

    def construct_packet(self, seq_num):
        pkt = Ethernet() + IPv4(protocol=IPProtocol.UDP) + UDP()
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
            log_info("SENT PKT " +  self.rhs)
            self.send_packet(self.rhs)
            self.rhs += 1

    def deconstruct_packet(self, packet):
        contents = packet.get_header(RawPacketContents)
        seq_num = int.from_bytes(contents.data[:4], 'big')
        log_info("GOT ACK " + seq_num)

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
        self.window_timestamp = time.time()
        while True:
            try:
                timestamp, dev, pkt = self.net.recv_pkt(timeout=self.recv_timeout)
                log_debug("Device is {}".format(dev))

                self.deconstruct_packet(pkt)
                if (self.lhs == self.num_packets + 1):
                    self.last_packet_ackd_time = time.time()
                    print("End of transmission. Successfully received ACK for %d packets" % self.num_packets)
                    raise Shutdown("Transmission is Over")

            except NoPackets:
                log_debug("No packets available in recv_packet")
                gotpkt = False
            except Shutdown:
                log_debug("Received signal for shutdown!")
                break
            if gotpkt:
                log_debug("I got a packet from {}".format(dev))
                log_debug("Pkt: {}".format(pkt))

            self.check_timeout()
            retransmitted_packet = False
            while not self.retransmission_queue.empty():
                seq_num = self.retransmission_queue.get()
                if not self.packet_window[seq_num]:
                    self.num_retrans_packets += 1
                    log_info("Resend seq_num {} pkt".format(seq_num))
                    self.send_packet(seq_num)
                    retransmitted_packet = True
                    break

            if not retransmitted_packet:
                self.update_window()

def main(net):
    blaster = Blaster(net, 'blaster_params.txt')
    blaster.switchy_main()

    total_time = blaster.last_packet_ackd_time - blaster.first_packet_send_time
    throughput = ((blaster.total_packets_sent * blaster.length_variable_payload) / total_time) 
    goodput = ((blaster.num_packets * blaster.length_variable_payload) / total_time) 
    blaster.print_output(total_time, blaster.num_retrans_packets, blaster.num_coarse_timeouts, throughput, goodput) 
    net.shutdown()
