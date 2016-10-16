import json
import sys
import time

from client import Client


"""
test:
1) run server
2) run tester_1
3) run tester_2
Those are in my pycharmgit
"""


def inc_dict(di):
    for k in di.keys():
        di[k] += 1
    return di


if __name__ == '__main__':
    ip = '127.0.0.1'
    f = open('port.txt')
    port = int(f.readline())
    f.close()
    c = Client(ip,port)

    f = open(sys.argv[1],'r')
    data1 = json.load(f)
    f.close()

    f = open(sys.argv[2], 'r')
    data2 = json.load(f)
    f.close()

    d = [data1, data2]
    print("Starting tester")

    t = time.time()
    n = 300
    for i in range(int(n)):
        ind = i%2
        not_ind = (i+1)%2
        d[ind] = inc_dict(d[ind])
        d2s = {"request":list(d[not_ind].keys()),"results":d[ind]}
        d[not_ind] = c.exchange_data(d2s["results"],d2s["request"])
        print(d[not_ind]["time"])
        del d[not_ind]["time"]

    t = time.time() -t
    print("Sent {} dicts in {} s".format(n,t))




