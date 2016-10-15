from client import *
import json

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
    print(d)
    for i in range(int(1e5)):

        ind = i%2
        not_ind = (i+1)%2
        d[ind] = inc_dict(d[ind])
        d2s = {"request":list(d[not_ind].keys()),"results":d[ind]}
        d[not_ind] = c.exchange_data(d2s["results"],d2s["request"])
        del d[not_ind]["time"]


