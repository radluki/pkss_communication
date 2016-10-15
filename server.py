import socket
import sys
from protocol import *
from config_logger import *
from multiprocessing import Process
from multiprocessing import Manager
import time
import argparse
import logging
import os

# logging configuration is set during argument parsing
# logging.basicConfig(level=logging.INFO,filename='server.log',format='%(levelname)s - %(asctime)s:\t\t\t%(message)s')


class Server(object):
    """
    Server tasks:
    1) Wait for connections:
    2) Create processes that manage connections

    Connection manager:
    1) Receive simulation results
    2) Receive data request
    3) Send data with time
    4) End connection
    """
    def __init__(self,ip,port,vars=['a', 'b', 'c', 'time'],protocol=ConfirmationProtocolManager()):
        self.ip = ip
        self.port = port
        self.sock = None
        self.protocol = protocol
        self.find_port()
        self._manager = Manager()
        self.state = self._manager.dict()
        self.reset_state(vars)
        self.id = 0

    def open_server_socket(self):
        # create local variables
        ip = self.ip
        port = self.port
        # check if sock is already open
        if self.sock is not None:
            self.sock.close()
        # create new sock
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (ip, port)
        # logging
        logging.info('starting up on %s port %s' % server_address)
        # activating socket
        sock.bind(server_address)
        sock.listen(1)
        self.sock = sock

    @staticmethod
    def serve_connection(protocol,connection,state,id):
        """
        Downloads data from client
        and sends requested state variables

        Static function used as target for serving processes
        """
        try:
            logging.info('%d Downloading simulation results'%id)
            received_data = protocol.receive(connection)
            results = received_data["results"]
            request = received_data["request"]
            logging.info('%d Received Results: %s' % (id,results))
            logging.info('%d Received Request: %s' % (id, request))
            for k,v in results.items():
                if k in state.keys():
                    state[k] = v

            logging.info('%d Waiting for full state update'%id)
            while None in state.values():
                time.sleep(0.1)

            data_to_send = {key:val for key,val in state.items() if key in set(request)}
            data_to_send['time'] = state['time']
            logging.info('%d Sending: %s ' % (id,data_to_send))
            protocol.sendall(connection,data_to_send)

        finally:
            # Clean up the connection
            logging.info("%d Closing connection",id)
            connection.close()

    def reset_state(self,names=None):
        """
        When iteration is complete resets current state
        When names are set it initializes state
        """
        state = self.state
        if names is None:
            for k in state.keys():
                if k != "time":
                    state[k] = None
            state['time'] += 1
        else:
            for k in names:
                state[k] = None
            state['time'] = 0


    def update_database(self):
        """Communicates with database"""
        # TODO database
        pass

    def find_port(self):
        """Finds free tcp/ip port starting from self.port"""
        while True:
            try:
                self.open_server_socket()
                break
            except Exception as e:
                logging.error(e)
                self.port += 1

    def start(self):
        """
        Server main loop. Listens for connections
        and creates new prosecces that serve them
        """
        try:
            while True:
                logging.info('waiting for connection')
                connection, client_address = self.sock.accept()
                # Check if iteration is complete
                if not (None in self.state.values()):
                    self.update_database()
                    self.reset_state()
                logging.info('connection from %s, creating separate process: %d' % (client_address,self.id))
                p = Process(target=Server.serve_connection, args=(self.protocol,connection, self.state, self.id))
                p.start()
                self.id += 1
        except:
            self.sock.close()


def parse_server_args():
    parser = argparse.ArgumentParser(description="Sets up server app")
    parser.add_argument(dest='ip')
    parser.add_argument(dest='port')
    parser.add_argument('-l', '--logfile', dest='logfile')
    parser.add_argument('-c',dest='console',action='store_true')
    args = parser.parse_args()

    # args conversions
    args.port = int(args.port)
    if args.logfile is None:
        args.logfile = "server.log"

    return args


if __name__ == "__main__":
    args = parse_server_args()
    configure_logger(args,logging.DEBUG)
    server = Server(args.ip,args.port)
    # TODO remove f operations (debug)
    f = open("port.txt","w")
    f.write(str(server.port))
    f.close()
    server.start()






