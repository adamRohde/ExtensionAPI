import sys

sys.path.append('/usr/local/lib/python3.8/dist-packages')
import uds_external_function
import real_time_object_detection
from queue import Queue


def main():
    q_send_to_PLC = Queue()
    q_receive_from_PLC = Queue()

    extFunc = uds_external_function.objectDetection(q_send_to_PLC, q_receive_from_PLC)
    extFunc.start()

    image_detect = real_time_object_detection.realTimeObjDetect(q_receive_from_PLC, q_send_to_PLC)
    image_detect.start()

if __name__ == '__main__':
    print(__doc__)
    main()
