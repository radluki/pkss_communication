import json
import sys
import time
import argparse

from client import Client


def inc_dict(di):
    for k in di.keys():
        di[k] += 1
    return di


def parse_args():
    parser = argparse.ArgumentParser(description="test case 1")
    parser.add_argument(dest='ip')
    parser.add_argument('-p',dest='port')
    parser.add_argument(dest='num_of_iter')
    parser.add_argument('-l', '--logfile', dest='logfile')
    parser.add_argument('-f',dest='file')
    args = parser.parse_args()

    args.file = 'input/'+args.file
    args.logfile = 'output/'+args.logfile
    if args.port is None:
        f = open('../port.txt')
        args.port = int(f.readline())
    else:
        args.port = int(args.port)
    if args.logfile is None:
        args.logfile = sys.stdout
    else:
        args.logfile = open(args.logfile,'w+')

    return args


if __name__ == '__main__':

    args = parse_args()
    ip = args.ip
    port = args.port

    c = Client(ip,port)

    with open(args.file) as f:
        data = json.load(f)

    request = data["request"]
    data = data["data"]

    assert isinstance(request,list)
    assert isinstance(data, dict)

    t = time.time()
    n = args.num_of_iter
    my_data = []
    received_data = []
    print('Starting Data exchange')
    for i in range(int(n)):
        received_data.append(c.exchange_data(data,request))
        my_data.append(data.copy())
        data = inc_dict(data)
        if i%10 == 0:
            print(data)
            print(received_data[-1])

    t = time.time() - t
    for i in reversed(range(1,31)):
        print("{} - {}".format(received_data[-i], my_data[-i]))

    print("Sent {} dicts in {} s".format(n,t))
    args.logfile.close()




