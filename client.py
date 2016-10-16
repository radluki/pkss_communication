import socket
import json
import logging
import argparse
import warnings

from protocol import ConfirmationProtocolManager
from config_logger import configure_logger


"""
Client tasks:
1) Open socket, establish connection
2) Send calculation results
3) Request specific data
4) Receive the data
"""


class Client(object):

    def __init__(self,ip,port,protocol=ConfirmationProtocolManager()):
        self.ip = ip
        self.port = port
        self.protocol = protocol

    def _connect(self):
        ip = self.ip
        port = self.port
        # connection configuration
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (ip,port)
        logging.info('connecting to %s port %s' % server_address)
        sock.connect(server_address)
        # Connection established
        return sock

    def exchange_data(self, data, request):
        """
        High level communication with server
        :param data: python data structure to send
        :param request: list of strings, names of requested variables
        :param ip:
        :param port:
        :return: downloaded, requested data
        """
        try:
            sock = self._connect()
            # Send Results
            #print_with_trim("Sending simulation results: %s", dict_to_send,file)
            logging.info("Results: %s", data)
            logging.info('Request: %s', request)
            data_to_send = dict()
            data_to_send["data"] = data
            data_to_send["request"] = request
            self.protocol.sendall(sock, data_to_send)

            # get the response
            received_data = self.protocol.receive(sock)
            logging.info("Answer: %s", received_data)
            #print_with_trim("received data: %s", received_data,file)
        finally:
            logging.info('closing socket')
            sock.close()
        return received_data


def parse_args():
    """Parses arguments from terminal"""
    parser = argparse.ArgumentParser(description="Sets up client app")
    parser.add_argument(dest='ip')
    parser.add_argument(dest='port')
    parser.add_argument(dest='outputfile')
    parser.add_argument('-r', '--request', dest='request', metavar='requested_variables', nargs='*')
    parser.add_argument('-f', '--file', dest='file', metavar='file_to_send')
    parser.add_argument('-s', '--string', dest='string', metavar='string_to_send',help="Example: -s \"{\"a\":1,\"b\":2}\"")
    parser.add_argument('-l', '--logfile', dest='logfile')
    parser.add_argument('-c', '--console', dest='console',action='store_true')

    args = parser.parse_args()

    if not (args.file is None):
        if not (args.string is None):
            warnings.warn("String will be overwritten by file contents")
        with open(args.file, "r") as f:
            args.string = " ".join(list(f))

    args.string = json.loads(args.string)
    args.port = int(args.port)

    return args


if __name__=="__main__":
    args = parse_args()

    # TODO remove f operations
    f = open('port.txt')
    port = int(f.__next__()) # overwriting args
    args.port = port

    configure_logger(args,logging.DEBUG)
    client = Client(args.ip,args.port)
    data_received = client.exchange_data(args.string,args.request)
    with open(args.outputfile,"w+") as of:
        json.dump(data_received,of)
    print(data_received)
