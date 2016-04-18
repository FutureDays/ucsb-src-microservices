#makebroadcast
#this script takes a single input file and makes a file suitable for broadcast/ delivery to patrons
#for audio this means 44.1kHz, 16bit, mono wav with ID3s (like a CD)
#for video this means a 6kbps H.264 .mp4
#you can also add fades or switch it to stereo
#"python makebroadcast.py -h" for help

import os
import subprocess
import sys
import glob
import re
import argparse
from distutils import spawn

class cd:
    #Context manager for changing the current working directory
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

def dependencies():
	depends = ['ffmpeg','ffprobe']
	for d in depends:
		if spawn.find_executable(d) is None:
			print "Buddy, you gotta install " + d
			sys.exit()
	return

def makeVideo(startObj):
#print ffprobe output to txt file, we'll grep it later to see if we need to transcode for j2k/mxf
	ffdata = open(startObj + ".ffdata.txt","w")
	subprocess.call(['ffprobe','-show_streams','-of','flat','-sexagesimal','-i',startObj], stdout=ffdata)
	ffdata.close()

	#find which stream is the video stream
	ffdata = open(startObj + ".ffdata.txt","r")
	for line in ffdata:
		#find the line for video stream
		if re.search('.codec_type=\"video\"', line):
			#separate that line by periods, the formatting provided by ffprobe
			foolist = re.split(r'\.', line)
			#3rd part of that list is the video stream
			whichStreamVid = foolist[2]
		#find the line for audio stream
		if re.search('.codec_type=\"audio\"', line):
			#separate that line by periods, the formatting provided by ffprobe
			foolist = re.split(r'\.', line)
			#3rd part of that list is the video stream
			whichStreamAud = foolist[2]
			print whichStreamAud
	ffdata.close()
	return

def makeAudio(args, startObj, startDir, assetName, EuseChar):
	with cd(startDir):
		#set some defaults
		ac = '1'
		ar = '44100'
		sfmt = 's16'
		fadestring = ''
		id3string = ''
		if not EuseChar == '': #sorts out the jukebox stuff which doesn't get this treatment
			id3string = makeid3(startDir, assetName)
		#get the right channel config
		if args['stereo'] is not False:
			ac = '2'
		#lets make fades!
		if args['fades'] is not False:
			tmptxt = open(startObj + '.ffdata.txt','w')
			#pipe ffprobe data for only duration thru stdout to txt file
			subprocess.call(['ffprobe','-i',startObj,'-show_entries','format=duration','-v','quiet'], stdout = tmptxt)
			tmptxt.close()
			#read from that text file we just made
			ffdata = open(startObj + ".ffdata.txt","r")
			for line in ffdata:
				#import duration from ffprobe output
				if re.search('duration=', line):
					#split the line at the = sign, as output by ffprobe
					foolist = re.split(r'=', line)
					dur = foolist[1] #grab the text element that is the duration
					fadestart = float(dur) - 2.0 #subract 2 from that to get the fade out start time
					fadestart = str(fadestart)
					fadestring = "-af afade=t=in:ss=0:d=2,afade=t=out:st=" + fadestart + ":d=2 " #generate the fade string using the fade out start time
			ffdata.close() #housekeeping
			os.remove(startObj + '.ffdata.txt') #housekeeping
		
		#subprocess.call(['ffmpeg','-i',startObj,'-ar',ar,'-sample_fmt',sfmt,'-ac',ac,'-id3v2_version','3','-write_id3v1','1','-y',assetName + EuseChar + '.wav'])
		ffmpegstring = 'ffmpeg -i ' + startObj + " " + id3string + ' -ar ' + ar + ' -sample_fmt ' + sfmt + ' -ac ' + ac + ' ' + fadestring + '-id3v2_version 3 -write_id3v1 1 -y ' + assetName + EuseChar + '.wav'

		subprocess.call(ffmpegstring)
	return

#makes an id3 ;ffmetadata1 file that we can use to load tags into the broadcast master	
def makeid3(startDir, assetName):
	id3Obj = os.path.join(startDir, assetName + "-mtd.txt")
	print "id3Obj " + id3Obj
	id3String = ""
	if not os.path.exists(id3Obj):
		usrInput = ''
		while usrInput not in ['y','n']: #gotta answer yes or no to this q
			usrInput = raw_input("There is currently no associated ID3 metadata for this object, would you like to make some so that it'll play nice with iTunes? (y/n) ")
			usrInput = usrInput.lower()
		if usrInput == 'y':
			print "Great, thank you! Here's how"
			print "1)Open a new text file and save it in the same folder as the thing you're trying to broadcast"
			print "2)Copy and paste the following into the empty text file, keep the new lines and punctuation"
			print ";FFMETADATA1"
			print "title= "
			print "artist= "
			print "album- "
			print "date= "
			print "publisher=UCSB Special Research Collections"
			print "3)Ok, don't copy-paste this part. Now, the best you can, fill out those fields in the text file"
			print "4)Lastly, save it as " + assetName + "-mtd.txt"
			donezo = raw_input("Press 'Enter' when you've finished the above process")
			id3String = "-i " + id3Obj + " -map_metadata 1"
		if usrInput == 'n':
			print "Ok, not great but ok"
	else:
		id3String = "-i " + id3Obj + " -map_metadata 1"
	return id3String

#parses input and makes the appropriate calls	
def handling():
	#initialize a buncha crap
	parser = argparse.ArgumentParser(description="Makes a broadcast-ready file from a single input file")
	parser.add_argument('startObj',nargs ='?',help='the file to be transcoded',)
	parser.add_argument('-ff','--fades',action='store_true',help='adds 2s heads and tails fades to black/ silence')
	parser.add_argument('-s','--stereo',action='store_true',help='outputs to stereo (mono is default)')
	args = vars(parser.parse_args()) #create a dictionary instead of leaving args in NAMESPACE land
	startObj = args['startObj'].replace("\\",'/') #for the windows peeps
	vexts = ['.mxf','.mp4','.mkv']
	aexts = ['.wav']
	fnamext = os.path.basename(os.path.abspath(startObj))
	fname, ext = os.path.splitext(fnamext)
	SuseChar = fname[-1:]
	startDir = os.path.abspath(os.path.join(startObj, os.pardir))
	#start testing
	if not os.path.isfile(startObj):
		print "Buddy, that's not a file"
	if not ext in vexts and not ext in aexts:
		print "Buddy, that's not really a file that we can make a broadcast master out of"
	else:
		if ext in vexts:
			print "itsa vid"
			#makevideo(startObj, )
		if ext in aexts:
			print "itsa sound"
			if SuseChar == 'a':
				print "archival master"
				assetName = fname[:-1]
				EuseChar = "b"
			elif SuseChar == 'm':
				print "archival master"
				assetName = fname[:-1]
				EuseChar = ""
			elif SuseChar == 'b':
				print "broadcast master"
				assetName = fname[:-1]
				EuseChar = "c"
			elif SuseChar == 'c':
				assetName = fname[:-1]
				EuseChar = "c"
			else:
				assetName = fname
				EuseChar = "b"
			makeAudio(args, startObj, startDir, assetName, EuseChar)
	return 


dependencies()
handling()

#adds for later
#seeing if id3 metadata is already in the file
#replacing print to txt with regex
#video