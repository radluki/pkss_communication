import argparse
import json
import logging
import socket
import warnings

from protocol import ConfirmationProtocolManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.CRITICAL,filename='logs/client.log',\
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

    client = Client(args.ip,args.port)
    data_received = client.exchange_data(args.string,args.request)
    with open(args.outputfile,"w+") as of:
        json.dump(data_received,of)
    print(data_received)
