import argparse
import json
import logging
import socket
import warnings

from protocol import ConfirmationProtocolManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.CRITICAL,filename='client.log',\
                    format='%(levelname)s - %(asctime)s:\t%(message)s')


class Client(object):

    def __init__(self,ip,port,protocol=ConfirmationProtocolManager()):
        """
        Creates Client object
        :param ip: server ip
        :param port: server tcp/ip port
        :param protocol: object that sends and receives python data structures
        """
        self.ip = ip
        self.port = port
        self.protocol = protocol

    def _connect(self):
        """ Connects to server socket """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (self.ip,self.port)
        logger.info('connecting to %s port %s' % server_address)
        sock.connect(server_address)
        return sock

    def exchange_data(self, data, request):
        """
        High level communication with server
        :param data: python data structure to send
        :param request: list of requested variables' names
        :return: requested data
        """
        try:
            # when sock was object field and server run one process in a while time was worse
            sock = self._connect()
            logger.info("Results: %s", data)
            logger.info('Request: %s', request)
            data_to_send = dict()
            data_to_send["data"] = data
            data_to_send["request"] = request
            self.protocol.send(sock, data_to_send)

            received_data = self.protocol.receive(sock)
            logger.info("Answer: %s", received_data)
        finally:
            logger.info('error in client\'s exchange_data')
            sock.close()
        return received_data


