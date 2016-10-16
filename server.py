import socket
import time
import argparse
import logging
import getpass
import os
from multiprocessing import Process, Lock, Manager

from protocol import ConfirmationProtocolManager
from config_logger import configure_logger
from database_updater import DatabaseUpdater
from database_updater import recreate_database_updater

# logging configuration is set during argument parsing
# logging.basicConfig(level=logging.INFO,filename='server.log',\
# format='%(levelname)s - %(asctime)s:\t\t\t%(message)s')


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
    WAIT_FOR_N = "WAIT_FOR_N"
    WAIT_TIME = "WAIT_TIME"
    TIME = "time"
    CONFIG_STATES = {WAIT_FOR_N, WAIT_TIME, TIME}

    def __init__(self, ip, port, db_updater, wait_time=1e-5, protocol=ConfirmationProtocolManager()):
        """
        :param ip:
        :param port:
        :param db_updater: object with fielsds - login,password,database,table
        :param protocol: object with methods sendall, receive compatible with python data structures
        """
        self.ip = ip
        self.port = port
        self.protocol = protocol

        self.sock = None
        self.find_free_port()
        # TCP/IT blocks port after closing it
        # blocking time can last even 4 minutes

        self._manager = Manager()
        self.state = self._manager.dict() # state shared by many processes
        self.initialize_state(db_updater.table.COLUMNS,wait_time)
        # program can send data to database and reset it
        # when all data is gathered and serving processes do not need current state any more

        db_dict = db_updater.get_db_dict() # way of sending db_updater to separate process

        self.enter_lock = Lock()
        self.exit_lock = Lock()
        self.db_updater = Process(target=Server.update_database, \
                                  args=(self.state, db_dict, self.enter_lock,self.exit_lock))

    def initialize_socket(self):
        server_address = (self.ip, self.port)
        logging.info('starting up on %s port %s' % server_address)

        if self.sock is not None:
            self.sock.close()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock.bind(server_address)
        sock.listen(1)
        self.sock = sock

    def find_free_port(self):
        """Finds free tcp/ip port starting from self.port"""
        while True:
            try:
                self.initialize_socket()
                break
            except Exception as e:
                logging.error(e)
                self.port += 1

    @classmethod
    def serve_connection(cls,protocol,connection,state,enter_lock,exit_lock):
        """
        Downloads data from client
        and sends requested state variables

        Static function used as target for serving processes
        """
        try:
            logging.info('%d Acquiring enter lock' % os.getpid())
            enter_lock.acquire()
            state[cls.WAIT_FOR_N] += 1
            enter_lock.release()

            logging.info('%d Downloading simulation results'%os.getpid())
            received_data = protocol.receive(connection)
            results = received_data["results"]
            request = received_data["request"]
            logging.info('%d Received Results: %s' % (os.getpid(),results))
            logging.info('%d Received Request: %s' % (os.getpid(), request))
            for k,v in results.items():
                if k in state.keys():
                    state[k] = v

            logging.info('%d Waiting for full state update'%os.getpid())

            logging.info('%d Acquiring exit lock' % os.getpid())
            exit_lock.acquire()
            exit_lock.release()

            data_to_send = {key:val for key,val in state.items() if key in set(request)}
            data_to_send[cls.TIME] = state[cls.TIME]

            exit_lock.acquire()
            state[cls.WAIT_FOR_N] -= 1
            exit_lock.release()


            logging.info('%d Sending: %s ' % (os.getpid(),data_to_send))
            protocol.sendall(connection,data_to_send)


        finally:
            # Clean up the connection
            logging.info("%d Closing connection",os.getpid())
            connection.close()

    @classmethod
    def update_database(cls, state, db_dict, enter_lock, exit_lock):
        """Communicates with database"""
        # enter_lock = locks[0]
        # exit_lock = locks[1]
        try:
            database_updater = recreate_database_updater(db_dict)
            exit_lock.acquire()
            while True:
                if not (None in state.values()): # state gathered
                    enter_lock.acquire()
                    exit_lock.release()

                    state_cp = state.copy()

                    while state[cls.WAIT_FOR_N] != 0:
                        time.sleep(state[cls.WAIT_TIME])
                    # state sent

                    Server.reset_state(state)
                    exit_lock.acquire()
                    enter_lock.release()

                    database_updater.send(state_cp)
                    database_updater.commit()
                    logging.info('Next iteration, time: {}'.format(state[cls.TIME]))


        finally:
            logging.error('TERMINATION of update_database')

    @classmethod
    def reset_state(cls,state):
        """
        When iteration is complete resets current state
        When names are set it initializes state
        """
        for k in state.keys():
            if k not in cls.CONFIG_STATES:
                state[k] = None
        state[cls.TIME] += 1

    def initialize_state(self,names,wait_time):
        for k in names:
            if k not in self.CONFIG_STATES:
                self.state[k] = None
        self.state[self.TIME] = int(1)
        self.state[self.WAIT_FOR_N] = 0
        self.state[self.WAIT_TIME] = wait_time



    def start(self):
        """
        Server main loop. Listens for connections
        and creates new prosecces that serve them
        """
        try:
            self.db_updater.start()
            while True:
                logging.info('waiting for connection')
                connection, client_address = self.sock.accept()
                logging.info('connection from %s, creating separate process: %d' % (client_address))
                p = Process(target=Server.serve_connection, \
                            args=(self.protocol,connection, self.state,self.enter_lock,self.exit_lock))
                p.start()
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

        database_updater = DatabaseUpdater(login, password, base)
    else:
        database_updater = DatabaseUpdater('root', 'luki', 'luki_testing')


    configure_logger(args.logfile,args.console,logging.DEBUG)
    server = Server(args.ip,args.port,database_updater)
    # TODO remove f operations (debug)
    f = open("port.txt","w")
    f.write(str(server.port))
    f.close()
    server.start()






