import time
from serial import Serial

#class ReadThread(threading.Thread):
#    print('initialize read thread..")

def connect():
	#Initiate a connection
	print("initializing..")
	arduino = Serial('/dev/ttyACM0', 115200)
	#Read confirmation from Arduino
	print("Done initializing...")
	arduino.flushInput()
	arduino.flushOutput()
	arduino.flush()
	count = 0
	try:
		while True:
			if count == 0:
				print('about to write..')
				arduino.write("H".encode('utf-8'))
				print('wrote..')
				count = count + 1
			if arduino.inWaiting() > 0:
				
				#read the message from the Arduino
				print('about to read.')
				time.sleep(0.2)
				raw_message = str(arduino.read(1))
				print('reading..')
				
				#remove EOL characters from string
				message = raw_message.rstrip()
				print(message)
				count = count + 1
				if count >= 100:
					count = 0
				print ("count " + str(count))
	except: 
		arduino.flushInput()
		arduino.flushOutput()
		arduino.flush()
		arduino.close()
		print('closed')

if __name__ == "__main__":
    connect()
