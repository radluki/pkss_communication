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

"""
For debugging purposes clients do not need to have
installed sqlalchemy. MODE is automatically set to SIMULATION
and appropriate class DatabaseUpdaterSimulator is used
"""


class Mode(Enum):
    LOGIN = 1
    DEBUG = 2
    SIMULATION = 3


try:
    from database_updater import DatabaseUpdater
    MODE = Mode.DEBUG
except Exception as e:
    from database_updater_simulator import DatabaseUpdaterSimulator
    MODE = Mode.SIMULATION
    print(e,file=sys.stderr)
    print("Unable to import DatabaseUpdater to server",file=sys.stderr)
    print("Simulation mode is set",file=sys.stderr)
    print("All database operation will be simulated by module DatabaseUpdaterSimulator",file=sys.stderr)


logging.basicConfig(level=logging.DEBUG,filename='server.log',\
                    format='%(levelname)s - %(asctime)s:\t%(message)s')


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
    DB_UPDATE_TIME = "DB_UPDATE_TIME" #sek
    CONFIG_STATES = {WAIT_FOR_N, WAIT_TIME, TIME, DB_UPDATE_TIME}

    def __init__(self, ip, port, db_updater,db_update_time=1, wait_time=1e-5, protocol=ConfirmationProtocolManager()):
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
        self.initialize_state(db_updater.table.COLUMNS,wait_time,db_update_time)
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
                if time.time() - t > state[cls.DB_UPDATE_TIME]:
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

    def initialize_state(self,names,wait_time,db_update_time):
        for k in names:
            if k not in self.CONFIG_STATES:
                self.state[k] = None
        self.state[self.TIME] = int(1)
        self.state[self.WAIT_FOR_N] = 0
        self.state[self.WAIT_TIME] = wait_time
        self.state[self.DB_UPDATE_TIME] = db_update_time

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
    parser = argparse.ArgumentParser(description="To set up server app required is ip address")
    parser.add_argument('-ip',dest='ip',help='server phisical ip address')
    parser.add_argument('--port',dest='port',help='server phisical tcp port')
    parser.add_argument('--login',dest='login',action='store_true',\
                        help='Configure database manually, if not set default(debugging) settings are used')

    args = parser.parse_args()
    if args.ip is None:
        args.ip = '127.0.0.1'
    if args.port is None:
        args.port = 10000
    else:
        args.port = int(args.port) # parsed as string

    return args


if __name__ == "__main__":
    args = parse_server_args()
    if args.login and MODE!=Mode.SIMULATION:
        MODE = Mode.LOGIN
    if MODE == Mode.LOGIN:
        print('Database configuration')
        host = input('Database host: ')
        base = input('Database: ')
        login = input('Login: ')
        password = getpass.getpass()
        database_updater = DatabaseUpdater(login, password, base, host)
    elif MODE == Mode.DEBUG:
        database_updater = DatabaseUpdater('luki', 'luki', 'luki_testing','192.168.43.198')
    elif MODE == Mode.SIMULATION:
        database_updater = DatabaseUpdaterSimulator('luki', 'luki', 'luki_testing','localhost')
    else:
        raise Exception('Unrecoginzed MODE')

    server = Server(args.ip,args.port,database_updater)
    # TODO remove f operations (debug)
    f = open("port.txt","w")
    f.write(str(server.port))
    f.close()
    print("Starting server on ip {} port {}".format(server.ip,server.port))
    server.start()






