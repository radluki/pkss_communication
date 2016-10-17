import socket
import time
import argparse
import logging
import getpass
import os
import sys
from multiprocessing import Process, Lock, Manager

from enum import Enum
from protocol import ConfirmationProtocolManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.CRITICAL,filename='logs/server.log',\
                    format='%(levelname)s - %(asctime)s:\t%(message)s')


class Mode(Enum):
    LOGIN = 1
    DEBUG = 2
    SIMULATION = 3


try:
    from database_updater import DatabaseUpdater
    MODE = Mode.DEBUG
except Exception as e:
    from database_updater import DatabaseUpdaterSimulator
    print(e,file=sys.stderr)
    print("Unable to import DatabaseUpdater to server")


class Server(object):
    """
    Server gathers state variables from client apps
    and it saves those variables in database. Clients
    send requests for variables to the server along with data
    in response appropriate data is sent.
    """
    WAIT_FOR_N = "WAIT_FOR_N"
    WAIT_TIME = "WAIT_TIME"
    TIME = "time"
    #TODO change this
    DB_UPDATE_TIME = 2 #sek
    CONFIG_STATES = {WAIT_FOR_N, WAIT_TIME, TIME}

    def __init__(self, ip, port, db_updater, wait_time=1e-5, protocol=ConfirmationProtocolManager()):
        """
        :param ip: phisical ip address of host machine
        :param port: indicates where to start searching for free tcp/ip port
        :param db_updater: DatabaseUpdater (production mode), DatabaseUpdaterSimulator(sim mode)
        :param protocol: object with methods send and receive allows for python data structures exchange via tcp/ip
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
        self.db_updater = Process(target=Server.manager, \
                                  args=(self.state, db_dict, self.enter_lock,self.exit_lock))

    def initialize_socket(self):
        server_address = (self.ip, self.port)
        logger.info('starting up on %s port %s' % server_address)

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
                logger.error(e)
                self.port += 1

    @classmethod
    def server(cls, protocol, connection, state, enter_lock, exit_lock):
        """
        Downloads data from client
        and sends requested state variables

        Static function used as target for serving processes
        """
        #while True:
        if 1:
            try:


                logger.info('%d Downloading simulation results'%os.getpid())
                received_data = protocol.receive(connection)
                data = received_data["data"]
                request = received_data["request"]
                logger.info('%d Received Results: %s' % (os.getpid(),data))
                logger.info('%d Received Request: %s' % (os.getpid(), request))

                logger.info('%d Acquiring enter lock' % os.getpid())
                enter_lock.acquire()
                state[cls.WAIT_FOR_N] += 1
                enter_lock.release()

                for k,v in data.items():
                    if k in state.keys():
                        state[k] = v

                logger.info('%d Waiting for full state update'%os.getpid())

                logger.info('%d Acquiring exit lock' % os.getpid())
                #exit_lock.acquire()
                #exit_lock.release()
                exit_lock.acquire()
                data_to_send = {key:val for key,val in state.items() if key in set(request)}
                data_to_send[cls.TIME] = state[cls.TIME]


                state[cls.WAIT_FOR_N] -= 1
                exit_lock.release()


                logger.info('%d Sending: %s ' % (os.getpid(),data_to_send))
                protocol.send(connection, data_to_send)


            finally:
                # Clean up the connection
                logger.info("%d Closing connection",os.getpid())
                #connection.close()

    @classmethod
    def manager(cls, state, db_dict, enter_lock, exit_lock):
        """Communicates with database and blocks exit and entrance to the server"""
        try:
            database_updater = db_dict['class'].recreate_database_updater(db_dict)
            exit_lock.acquire()
            t = time.time()
            while True:
                if time.time() - t > cls.DB_UPDATE_TIME:
                    t = time.time()
                    database_updater.commit()
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

                    database_updater.add(state_cp)
                    logger.info('Next iteration, time: {}'.format(state[cls.TIME]))


        finally:
            logger.error('TERMINATION of manager')

    @classmethod
    def reset_state(cls,state):
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
        and creates server processes that serve them
        """
        try:
            self.db_updater.start()
            while True:
                logger.info('waiting for connection')
                connection, client_address = self.sock.accept()
                logger.info('connection from %s, creating separate process: %d' % (client_address))
                p = Process(target=Server.server, \
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
    parser.add_argument('-ho',dest='host')

    args = parser.parse_args()

    if args.host is None:
        args.host = 'localhost'
    # args conversions
    args.port = int(args.port)
    if args.logfile is None:
        args.logfile = "server.log"

    return args


if __name__ == "__main__":
    args = parse_server_args()
    print('Database configuration')

    if MODE == Mode.LOGIN:
        login = input('Login: ')
        password = getpass.getpass()
        base = input('Database: ')

        database_updater = DatabaseUpdater(login, password, base)
    elif MODE == Mode.DEBUG:
        database_updater = DatabaseUpdater('luki', 'luki', 'luki_testing',args.host)
    elif MODE == Mode.SIMULATION:
        from database_updater import DatabaseUpdaterSimulator
        database_updater = DatabaseUpdaterSimulator('luki', 'luki', 'luki_testing',args.host)
    else:
        raise Exception('Unrecoginzed MODE')

    server = Server(args.ip,args.port,database_updater)
    # TODO remove f operations (debug)
    f = open("port.txt","w")
    f.write(str(server.port))
    f.close()
    print("Server running on ip {} port {}".format(server.ip,server.port))
    server.start()






