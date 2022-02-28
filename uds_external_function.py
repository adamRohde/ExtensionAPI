import socket
import sys
import struct
import threading
import fcntl, os
import errno


# This class helps to connect to a CODESYS Control runtime
# and provide an implementation of an external function
class ExternalFunctionBase(threading.Thread):

    def __init__(self, q_send_to_plc, q_receive_from_plc):
        self.sock = None
        self.q_receive_from_PLC = q_receive_from_plc
        self.q_send_to_PLC = q_send_to_plc
        threading.Thread.__init__(self)
        self.functionName = self.__class__.__name__
        self.dir = '/home/adam/Desktop/ExtensionAPI'
        self.endpoint = os.path.join(self.dir, self.functionName + '.sock')
        try:
            getattr(self, 'Call')
        except:
            print('Your class does not have a method with name "Call"')
            return None

    def run(self):
        try:
            if not os.path.exists(self.dir):
                os.makedirs(self.dir)
        except socket.error as msg:
            if msg.errno == 13:
                print("Could not create " + self.dir + ": permission denied.")
                print(
                    "Either run this script with sufficient permissions or create the directory with sufficient permissions (e.g. sudo mkdir " + self.dir + "; sudo chown $(whoami) " + self.dir + ")")
            else:
                print(msg)
            return False
        try:
            os.unlink(self.endpoint)
        except socket.error as msg:
            if msg.errno != 13 and msg.errno != 2:
                print(msg)
                return False

        try:
            # create unix domain socket
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            print("Starting server for external function " + self.functionName)
            # bind the socket to CODESYS runtime
            self.sock.bind(self.endpoint)
            self.sock.listen(1)
        except socket.error as msg:
            if msg.errno == 13:
                print("Could not bind socket: permission denied on " + self.endpoint)
                print(
                    "Either run this script with sufficient permissions or change permissions on " + self.dir + " (e.g. sudo chown $(whoami) " + self.dir + ")")
            else:
                print(msg)
            return False

        while True:
            try:
                connection, client_address = self.sock.accept()
            except socket.error as msg:
                if self.sock != None:
                    self.sock.close()
                    return False

            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            while True:
                try:
                    request = connection.recv(1000)
                    if request:
                        dictParams = {}
                        format = "IiI"
                        msgId, msgType, rcvDataSize = struct.unpack_from(format, request)
                        # print('Request received: MsgId: %u, MsgType: %d, dataSize: %u' % (msgId, msgType, rcvDataSize))
                        if rcvDataSize > 0:
                            format = "%ip" % rcvDataSize
                            data = request[12:]  # 12 bytes header
                            if not data:
                                print("Unexpected data size")
                                break
                            liParamsRaw = [x.decode("UTF-8") for x in data.split(b'\x00')]
                            for param in liParamsRaw:
                                if ':=' in param:
                                    paramName, paramLiteral = param.split(':=')
                                    paramType, paramValue = paramLiteral.split('#')
                                    dictParams[paramName] = paramType, paramValue

                        # print('Call function "' + self.functionName + '" with parameters ' + str(dictParams))
                        func = getattr(self, 'Call')

                        # Call the external function
                        dictRetParams = func(dictParams)
                        if dictRetParams:
                            params = b''
                            # print('Return parameters "' + str(dictRetParams))
                            for paramName, (paramType, paramValue) in dictRetParams.items():
                                params += (str(paramName) + ':=' + str(paramType) + '#' + str(
                                    paramValue)).encode() + b'\00'
                            format = "IiII"
                            response = struct.pack(format, msgId, msgType, len(params), 0) + params
                        else:
                            # Return error code (here: 1=ERR_FAILED)
                            format = "IiII"
                            response = struct.pack(format, msgId, msgType, 0, 1)
                        connection.sendall(response)
                        continue
                    else:
                        break
                except socket.error as msg:
                    if msg.errno == errno.EAGAIN or msg.errno == errno.EWOULDBLOCK or msg.errno == None:
                        continue
                    else:
                        print(msg)
                        break


# end of class

# The name of the class defines the name of the external function
class objectDetection(ExternalFunctionBase):

    # This is the effective call of the external function.
    # Input parameters are passed as dict of tuple of strings (paramType, paramValue) with parameter name as index.
    # E.g. {'parameterIn1': ('DINT', '11'), 'parameterIn2': ('DINT', '22')}
    # Return parameters must be in the same format.
    def Call(self, dictParams):
        in1 = float(dictParams['confidence_threshold'][1])
        print("confidence in", in1)
        self.q_receive_from_PLC.put(in1)
        data = self.q_send_to_PLC.get()
        object_detect_data = str(data[0])
        dictRetParams = {}
        dictRetParams['parameterOut1'] = 'STRING', object_detect_data
        dictRetParams['parameterOut2'] = 'REAL', data[1]
        return dictRetParams

    # example for external function:

if __name__ == "__main__":
    extFunc = objectDetection()
    extFunc.start()
