# How to run?: python real_time_object_detection.py --prototxt MobileNetSSD_deploy.prototxt.txt --model MobileNetSSD_deploy.caffemodel
# python real_time.py --prototxt MobileNetSSD_deploy.prototxt.txt --model MobileNetSSD_deploy.caffemodel

# import packages
import sys

from imutils.video import VideoStream
from imutils.video import FPS
import numpy as np
import argparse
import imutils
import time
import cv2
import threading


class realTimeObjDetect(threading.Thread):

	def __init__(self, q_receive_from_plc, q_send_to_plc):
		threading.Thread.__init__(self)
		self.q_send_to_PLC = q_send_to_plc
		self.prototext = ''
		self.model = ''
		self.q_receive_from_PLC = q_receive_from_plc
		self.CLASSES = ["aeroplane", "background", "bicycle", "bird", "boat",
				   "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
				   "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
				   "sofa", "train", "tvmonitor"]
		self.COLORS = ''

	def run(self):
		# self.prototext = open('MobileNetSSD_deploy.prototxt.txt', 'r')
		# self.model = open('MobileNetSSD_deploy.caffemodel', 'rb')
		# prototext_content = self.prototext.read()
		# model_content = self.model.read()
		protobuf = cv2

		# Assigning random colors to each of the classes
		self.COLORS = np.random.uniform(0, 255, size=(len(self.CLASSES), 3))
		#self.COLORS = [15, 15, 15]
		# COLORS: a list of 21 R,G,B values, like ['101.097383   172.34857188 111.84805346'] for each label
		# length of COLORS = length of CLASSES = 21

		# load our serialized model
		# The model from Caffe: MobileNetSSD_deploy.prototxt.txt; MobileNetSSD_deploy.caffemodel;
		print("[INFO] loading model...")

		prototext_content = "./MobileNetSSD_deploy.prototxt.txt"
		model_content = "./MobileNetSSD_deploy.caffemodel"
		net = cv2.dnn.readNetFromCaffe(prototext_content, model_content)
		# print(net)
		# <dnn_Net 0x128ce1310>

		# initialize the video stream,
		# and initialize the FPS counter
		print("[INFO] starting video stream...")
		vs = VideoStream(src=0).start()
		# warm up the camera for a couple of seconds
		time.sleep(2.0)

		# FPS: used to compute the (approximate) frames per second
		# Start the FPS timer
		fps = FPS().start()


		while True:
			# grab the frame from the threaded video stream and resize it to have a maximum width of 400 pixels
			# vs is the VideoStream
			frame = vs.read()
			frame = imutils.resize(frame, width=400)
			#print(frame.shape) # (225, 400, 3)
			# grab the frame dimensions and convert it to a blob
			# First 2 values are the h and w of the frame. Here h = 225 and w = 400
			(h, w) = frame.shape[:2]
			# Resize each frame
			resized_image = cv2.resize(frame, (300, 300))
			# Creating the blob
			# The function:
			# blob = cv2.dnn.blobFromImage(image, scalefactor=1.0, size, mean, swapRB=True)
			# image: the input image we want to preprocess before passing it through our deep neural network for classification
			# mean:
			# scalefactor: After we perform mean subtraction we can optionally scale our images by some factor. Default = 1.0
			# scalefactor  should be 1/sigma as we're actually multiplying the input channels (after mean subtraction) by scalefactor (Here 1/127.5)
			# swapRB : OpenCV assumes images are in BGR channel order; however, the 'mean' value assumes we are using RGB order.
			# To resolve this discrepancy we can swap the R and B channels in image  by setting this value to 'True'
			# By default OpenCV performs this channel swapping for us.

			blob = cv2.dnn.blobFromImage(resized_image, (1/127.5), (300, 300), 127.5, swapRB=True)
			# print(blob.shape) # (1, 3, 300, 300)
			# pass the blob through the network and obtain the predictions and predictions
			net.setInput(blob) # net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])
			# Predictions:
			predictions = net.forward()

			confidence_threshold = self.q_receive_from_PLC.get()
			print("confidence", confidence_threshold)

			# loop over the predictions
			for i in np.arange(0, predictions.shape[2]):
				# extract the confidence (i.e., probability) associated with the prediction
				# predictions.shape[2] = 100 here
				confidence = predictions[0, 0, i, 2]
				# Filter out predictions lesser than the minimum confidence level
				# Here, we set the default confidence as 0.2. Anything lesser than 0.2 will be filtered

				if confidence > confidence_threshold:
					# extract the index of the class label from the 'predictions'
					# idx is the index of the class label
					# E.g. for person, idx = 15, for chair, idx = 9, etc.
					idx = int(predictions[0, 0, i, 1])
					# then compute the (x, y)-coordinates of the bounding box for the object
					box = predictions[0, 0, i, 3:7] * np.array([w, h, w, h])
					# Example, box = [130.9669733   76.75442174 393.03834438 224.03566539]
					# Convert them to integers: 130 76 393 224
					(startX, startY, endX, endY) = box.astype("int")

					# Get the label with the confidence score
					label = "{}: {:.2f}%".format(self.CLASSES[idx], confidence * 100)
					confidence_out = (self.CLASSES[idx], confidence * 100)

					self.q_send_to_PLC.put(confidence_out)

					# Draw a rectangle across the boundary of the object
					cv2.rectangle(frame, (startX, startY), (endX, endY),
						self.COLORS[idx], 2)
					y = startY - 15 if startY - 15 > 15 else startY + 15
					cv2.putText(frame, label, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLORS[idx], 2)

			# show the output frame
			cv2.imshow("frame", frame)

			# Now, let's code this logic (just 3 lines, lol)
			key = cv2.waitKey(1) & 0xFF

			# Press 'q' key to break the loop
			if key == ord("q"):
				break

			# update the FPS counter
			fps.update()

		# stop the timer
		fps.stop()

		# Display FPS Information: Total Elapsed time and an approximate FPS over the entire video stream
		print("[INFO] Elapsed Time: {:.2f}".format(fps.elapsed()))
		print("[INFO] Approximate FPS: {:.2f}".format(fps.fps()))

		# Destroy windows and cleanup
		cv2.destroyAllWindows()
		# Stop the video stream
		vs.stop()
