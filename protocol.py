import json
import logging

class ConfirmationProtocolManager(object):

    def __init__(self,eom='ł',cb=b'y'):
        """
        Creates protocol manager
        :param eom: end of message string
        :param cb: confirmation byte
        """
        self.eom_byte_len = len(eom.encode("utf-8"))
        self.eom = eom
        self.cb = cb

    def receive(self,connection):
        """
        Downloads message ending with eom sign
        bytes -> string -> python data structure
        received bytes should be encoded with utf-8
        string should be in json format
        """
        whole_message = b""
        while True:
            data = connection.recv(16)
            whole_message = whole_message + data
            try:
                # in case whole_message contains only one byte
                # do not decode data because one char may be send in two packets
                # decoding will raise exception
                last_sign = whole_message[-self.eom_byte_len:].decode("utf-8")
            except Exception as e:
                logging.error(e)
                continue
            if last_sign[-len(self.eom):] == self.eom:
                whole_message = whole_message.decode("utf-8")
                whole_message = whole_message[:-len(self.eom)]
                connection.send(self.cb) #confirmation
                data = json.loads(whole_message)
                return data

    def sendall(self,sock, data_structure):
        """
        Sends data stucture with eom end of message,
        waits for confirmation byte
        """
        data_to_send = json.dumps(data_structure) + self.eom
        data_to_send_utf = data_to_send.encode("utf-8")
        sock.sendall(data_to_send_utf)
        b = sock.recv(1)
        if b!=self.cb:
            raise Exception('Confirmation byte is incorrect')




