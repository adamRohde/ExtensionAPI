import sys

sys.path.append('/usr/local/lib/python3.8/dist-packages')
import uds_external_function
import real_time_object_detection
from queue import Queue


def main():
    confidence = 0.2

    q_send_to_PLC = Queue()
    q_receive_from_PLC = Queue()

    extFunc = uds_external_function.objectDetection(q_send_to_PLC, q_receive_from_PLC)
    extFunc.start()

    image_detect = real_time_object_detection.realTimeObjDetect(q_receive_from_PLC, q_send_to_PLC)
    image_detect.start()

    # while (True):
    #     to_plc = q_send_to_PLC.get()
    #     print("sending to plc", to_plc)
    #
    #     q_receive_from_PLC.put(to_plc)
    #     from_plc = q_receive_from_PLC.get()
    #     print(from_plc)


if __name__ == '__main__':
    print(__doc__)
    main()
