from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from threading import *
import random
import time

class MiddleBox(object):
    def __init__(self, net, txt_file):
        self.net = net
        self.seed = None
        self.percent = None
        self.parse(txt_file)

    def parse(self, file):
        with open(file, 'r') as f:
            tokens = f.read().strip().split(" ")
            self.seed = tokens[1]
            self.percent = tokens[3]

    def drop(self):
        random.seed(a=self.seed) #Extract random seed from params file 
        return random.randrange(100) <= int(self.percent)

    def switchy_main(self):
        my_intf = self.net.interfaces()
        mymacs = [intf.ethaddr for intf in my_intf]
        myips = [intf.ipaddr for intf in my_intf]
        while True:
            gotpkt = True
            try:
                log_info("here") 
                timestamp, dev, pkt = self.net.recv_packet()
                log_info("here")
                log_debug("Device is {}".format(dev))
            except NoPackets:
                log_debug("No packets available in recv_packet")
                gotpkt = False
            except Shutdown:
                log_debug("Got shutdown signal")
                break

            if gotpkt:
                log_debug("I got a packet {}".format(pkt))
	   

            if dev == "middlebox-eth0":
                log_debug("Received from blaster")
                if not self.drop():  # if both conditions fail, then drop the pkt as evil thing in network
                    pkt[Ethernet].src = self.net.interface_by_name("middlebox-eth1").ethaddr
                    pkt[Ethernet].dst = "20:00:00:00:00:01"
                    log_info("SENDING PACKET TO BLASTEE") 
                    self.net.send_packet("middlebox-eth1", pkt)
                log_debug("random pkt drop")

            elif dev == "middlebox-eth1":
                log_debug("Received from blastee")
                pkt[Ethernet].src = self.net.interface_by_name("middlebox-eth0").ethaddr
                pkt[Ethernet].dst = "10:00:00:00:00:01"
                log_info("SENDING PACKET TO BLASTER") 
                self.net.send_packet("middlebox-eth0", pkt)

            else:
                log_debug("Oops :))")

def main(net):
    mbox = MiddleBox(net, "middlebox_params.txt")
    mbox.switchy_main()
    net.shutdown()
