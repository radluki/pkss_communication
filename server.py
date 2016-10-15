import socket
import sys
from protocol import *
from config_logger import *
from multiprocessing import Process, Lock, Manager
import time
import argparse
import logging
import getpass
import os
from database_updater import *

# logging configuration is set during argument parsing
# logging.basicConfig(level=logging.INFO,filename='server.log',format='%(levelname)s - %(asctime)s:\t\t\t%(message)s')

#TODO global
WAIT_TIME = 1e-5

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

    Usage:
    1) Initialize
    2) Start
    """
    def __init__(self, ip, port, database_updater, protocol=ConfirmationProtocolManager()):
        """

        :param ip:
        :param port:
        :param database_updater: object with fielsds - login,password,database,table
        :param protocol: object with methods sendall, receive compatible with python data structures
        """
        self.ip = ip
        self.port = port
        self.sock = None
        self.protocol = protocol
        self.find_port()
        self._manager = Manager()
        self.state = self._manager.dict() # state shared by many processes
        database_updater_dict = {"class":database_updater.__class__,
                                "login":database_updater.login,\
                                 "table":database_updater.table,\
                                 "password":database_updater.password,\
                                 "database":database_updater.database}
        Server.reset_state(self.state,database_updater.table.COLUMNS)
        self.state["num_of_p"] = 0 #number of processes dependant on state
        # program can send data to database when all data is gathered
        # program can increment state (reset it) when state is not needed by processes
        # and state was sent to database
        self.id = 0 # id of process (for logging)
        self.lock = Lock()
        p = Process(target=Server.update_database, args=(self.state, database_updater_dict, self.lock))
        p.start()

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
    def serve_connection(protocol,connection,state,id,lock):
        """
        Downloads data from client
        and sends requested state variables

        Static function used as target for serving processes
        """
        try:
            lock.acquire()
            state['num_of_p'] += 1
            lock.release()

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
                # TODO TIME DEPENDENCY
                time.sleep(WAIT_TIME)

            data_to_send = {key:val for key,val in state.items() if key in set(request)}
            data_to_send['time'] = state['time']

            lock.acquire()
            state['num_of_p'] -= 1
            lock.release()

            logging.info("{} waiting for database update".format(id))
            while not None in state.values():
                time.sleep(WAIT_TIME) #TODO TIME DEPENDANCY

            logging.info('%d Sending: %s ' % (id,data_to_send))
            protocol.sendall(connection,data_to_send)

        finally:
            # Clean up the connection
            logging.info("%d Closing connection",id)
            connection.close()


    @staticmethod
    def reset_state(state,names=None):
        """
        When iteration is complete resets current state
        When names are set it initializes state
        """
        if names is None:
            for k in state.keys():
                if k != "time":
                    state[k] = None
            state['time'] += 1
        else:
            for k in names:
                state[k] = None
            state['time'] = 1

    @staticmethod
    def update_database(state, dbu_parts,lock):
        """Communicates with database"""
        dbu_class = dbu_parts['class']
        del dbu_parts['class']
        database_updater = dbu_class(**dbu_parts)
        while True:
            # TODO TIME DEPENDENCY
            time.sleep(WAIT_TIME)
            if state['num_of_p']==0 and not (None in state.values()):
                lock.acquire()
                database_updater.send(state)
                Server.reset_state(state)
                state['num_of_p'] = 0
                logging.info('Next iteration, time: {}'.format(state['time']))
                lock.release()

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
                logging.info('connection from %s, creating separate process: %d' % (client_address,self.id))
                p = Process(target=Server.serve_connection, args=(self.protocol,connection, self.state, self.id,self.lock))
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

    print('Database configuration')
    if 0:
        login = input('Login: ')
        password = getpass.getpass()
        base = input('Database: ')

        database_updater = [DatabaseUpdater, login, password, base, State] #updater,...,table
    else:
        database_updater = DatabaseUpdater('root', 'luki', 'luki_testing', State)


    configure_logger(args,logging.DEBUG)
    server = Server(args.ip,args.port,database_updater)
    # TODO remove f operations (debug)
    f = open("port.txt","w")
    f.write(str(server.port))
    f.close()
    server.start()






