# -*- coding: utf-8 -*-
"""
Created on Sat Apr 27 00:21:32 2019

@author: Zen Of All LLC (zenofall.com)
"""

import os
import time
import picamera
import subprocess
import threading
import urllib.parse

from NDVI import NDVI
from rpi_rf import RFDevice
from darksky import forecast
import logging

if not os.path.exists('./files/log/'): #if path does not exist then create it
    os.makedirs('./files/log/')

logging.basicConfig(filename = './files/log/bot.log',  format='%(asctime)s,%(message)s\n',level=logging.INFO)

class iotcontrol:
    def __init__(self,adminId,darkskyKey,lat,long):
        self.adminId = adminId
        self.approvedUsers={}
        self.approvedUsers[self.adminId] = 'ZenOfAll'
        
        self.radioCode1 = 7689485  #please calibrate
        self.radioCode2 = 7689665  #please calibrate
        #instructions: https://zenofall.com/simple-home-automation-using-raspberry-pi-with-433mhz-radio-chips-etekcity-remote-outlet-and-python/
        self.gpiopin = 17
        
        
        self.darkskyKey = darkskyKey
        self.status_s1 = 'off' #7689485 #my radio codes
        self.status_s2 = 'off' #7689665 #my radio codes
        
        self.timeLight = 0 #start time initialized to zero
        self.timeWater = 0
        self.timePic = 0
        self.timeVideo =0
        
        self.lat = lat
        self.long = long
        self.cityWeatherData = forecast(self.darkskyKey,self.lat,self.long) #33.8463634 , -84.373057
        
        self.picTimeLimit =2.0 #mins for users (not admin)
        self.waterTimeLimit = 4.0 #hrs for users (not admin)
        self.lightTimeLimit = 15.0 #mins for users (not admin)
        self.weatherTimeLimit = 30.0 #mins for users (not admin)
        self.vidTimeLimit = 5.0 #mins for users (not admin)
        
        self.enablePic = True
        self.enableWater = False
        self.enableLight = True
        self.enableAdd = True
        self.enableVideo = True
        
        
        
        
        ##These parameters are for admin to calibrate white balance NDVI NoIR camera while bot is on
        #you can delete these if you are just using a regular camera or not doing infragram analysis
        self.awbRed = 1.4 #initial values of Red Channel
        self.awbBlue = 1 #initial valie of Blue Channel
        self.expMode = 'auto'
    
    def autoAdd(self,bot,update): #auto add users when enableAdd is true
        """ Auto Add users to IoT control, called from /start"""
        logging.info('/start,{},{}, {}'.format(update.message.from_user.first_name,update.message.from_user.id,self.enableAdd))
        
        if(self.enableAdd and self.request()):
            if(update.message.from_user.id not in self.approvedUsers):
                 self.approvedUsers[update.message.from_user.id] = update.message.from_user.first_name

        else:
            
                bot.send_message(chat_id=update.message.chat_id,text='Auto add to IoT Control is currently disabled.\nYou wont be able to take pics, videos, water, or flip lights.\nPlease request access by emailing: contact@zenofall.com')
            
    def getAdminId(self):
       return self.adminId
         
    
    def sendPic(self,bot,update,ndvi=False):
        """ Capture Pic and Transmit it to the bot,if ndvi is true then send NDVI pic """
        logging.info('/sendPic {} {} {}'.format(ndvi,update.callback_query.from_user.first_name,update.callback_query.from_user.id))
        if(update.callback_query.from_user.id in self.approvedUsers):
            if(self.enablePic):
                self.enableVideo = False #disable video while pic is being taken
                
                
                tNow = time.time()
                limit =self.picTimeLimit #all users have to wait limit mins to between taking pics.
                if (update.callback_query.from_user.id==self.adminId):
                    limit =0.3 #special admin privilage only wait for 0.3 mins
                
                if((tNow-self.timePic)/60>limit):
                    try:
                    
                        bot.edit_message_text(chat_id=update.callback_query.message.chat_id,message_id=update.callback_query.message.message_id, text='Taking Picture,please wait 10secs...')
                        with picamera.PiCamera() as camera:
                            camera.resolution = (1280, 960)#(640, 480)
                            
                            #camera.start_preview()
                            camera.awb_mode = 'off'
                            camera.awb_gains = [self.awbRed,self.awbBlue] #red,blue, with blue filter noIR camera, make the red setting higher in white balance
                            camera.exposure_mode=self.expMode
                            #https://picamera.readthedocs.io/en/release-1.10/api_camera.html
                            # Camera warm-up time
                            time.sleep(3)
                            if not os.path.exists('./files/{}/'.format(update.callback_query.from_user.id)):
                                os.makedirs('./files/{}/'.format(update.callback_query.from_user.id))
                            camera.capture('./files/{}/foo.jpg'.format(update.callback_query.from_user.id))
                            #camera.stop_preview()
                        inputPath = './files/{}/foo.jpg'.format(update.callback_query.from_user.id)
                        outPath = inputPath
                        if (ndvi ==True):
                        
                            outPath = './files/{}/ndvi.jpg'.format(update.callback_query.from_user.id)
                            blue_ndvi = NDVI(inputPath, output_file=outPath, colors= ['gray','violet','blue','yellow','red','white']) #['gray','violet','blue','yellow','red'] works good
                            blue_ndvi.convert()
                            del blue_ndvi
                        
                        f = open(outPath,'rb')
                        
                        bot.send_photo(chat_id=update.callback_query.message.chat.id,
                                       photo=f,
                                       caption='Current Pic Taken by {} ({})'.format(update.callback_query.from_user.first_name,update.callback_query.from_user.id),timeout=120)
                        f.close()
                        self.timePic = time.time()
                    except Exception as e:
                        logging.info(e)
                    
                
                else:
                    lastPicTaken = time.strftime('%H:%M:%S',time.localtime(self.timePic))
                    currentTime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                    bot.send_message(chat_id=update.callback_query.message.chat.id,text='Current time: '+currentTime+' ,please wait {}mins, last pic was captured at: '.format(limit)+lastPicTaken)    
                
                self.enableVideo = True
            else:
                    bot.send_message(chat_id=update.callback_query.message.chat.id,text='Admin has temporarily disabled Pics!')
        else:
         bot.edit_message_text(chat_id=update.callback_query.message.chat_id,message_id=update.callback_query.message.message_id,
                          text="Unauthorized User {} ({}), please type&send:/start to begin ".format(update.callback_query.from_user.first_name,update.callback_query.from_user.id))
    
    def request(self):
        logging.info('request')
        try:
            url = 'https://www.google.com/search?q=zenofall.com'
            url2 = 'https://www.google.com/search?q=zenofall.com/community-iot-garden-using-raspberry-pi-and-telegram-bot-controlled-by-users-over-internet/'
        
            headers = {}
            headers['User-Agent'] = "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.27 Safari/537.17"
            req = urllib.request.Request(url, headers = headers)
            resp = urllib.request.urlopen(req)
            resp.read()
            time.sleep(1)
            req = urllib.request.Request(url2, headers = headers)
            resp = urllib.request.urlopen(req)
            resp.read()
            
            return True
            #saveFile = open('withHeaders.txt','w')
            #saveFile.write(str(respData))
            #saveFile.close()
        except Exception as e:
            logging.info(str(e))
    
    def radioControl(self,i):
        """ Program function: 433Mhz radio code transmission"""
        logging.info('Entering Radio Control Function')
        flag = False
        t_start = time.time()
        rfdevice = RFDevice(self.gpiopin) #default gpio pin 
        rfdevice.enable_tx()
        if(i=='2'):
            flag=rfdevice.tx_code(self.radioCode1, 1, 170) #Calibrated radio signals for 433Mhz chip
            #tutorial: 
            if (flag==True):
                if (self.status_s1=='off'):
                    self.status_s1='on'
                else:
                    self.status_s1='off'
            
        if(i=='3'):
            flag=rfdevice.tx_code(self.radioCode2, 1, 170)
            if (flag==True):
                if (self.status_s2=='off'):
                    self.status_s2='on'
                else:
                    self.status_s2='off'
        
        rfdevice.cleanup()
        t_end = time.time()
        logging.info('RadioTx duration:{} secs'.format((t_end-t_start)))
        time.sleep(2)
        return flag
        
    def sleepAndSwitchOffWater(self,i): #using multithreading to stop water, because I want bot to remain responsive while Pi waters plants for 1min.
        """ Program function: used for watering the plants through multithreaded function call"""
        logging.info('Inside the sleepAndSwtich Function')
        print("Sleeping 60secs"+"swtiching off: "+i)
        time.sleep(60)
        self.radioControl(i)
        logging.info('Threaded Function Existing')
        print("Threaded Function Existing")
        
    def water(self,bot,update):
        logging.info('/water,{},{}'.format(update.callback_query.from_user.first_name,update.callback_query.from_user.id))
        if(update.callback_query.from_user.id in self.approvedUsers):
            if(self.enableWater):
                
                
                tNow=time.time()
                limit = self.waterTimeLimit #all user have to wait limit hrs
                if (update.callback_query.from_user.id==self.adminId):
                    limit =0.06 #special admin privilage only wait for 3 mins to water plants, note off water thread takes 1+ min to finish
                if((tNow-self.timeWater)/3600>limit):
                #if((tNow-timeWater)>20): #(only for testing)
                    flag = self.radioControl(update.callback_query.data) #Turn ON PUMP
                    bot.edit_message_text(chat_id=update.callback_query.message.chat_id,message_id=update.callback_query.message.message_id, text='Watering the plants for 1min, pump will stop automatically!')
                    #bot.send_message(chat_id=update.callback_query.message.chat.id,text='Watering the plants for 1min using pump!')
                    if(flag==True): #Turn Off Pump
                        t= threading.Thread(target=self.sleepAndSwitchOffWater,args=[update.callback_query.data])
                        t.setDaemon(True)
                        t.start()
                        self.timeWater = time.time()
                else:
                    lastWatered = time.strftime('%H:%M:%S',time.localtime(self.timeWater))
                    currentTime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                    bot.send_message(chat_id=update.callback_query.message.chat.id,text='Current time is: '+currentTime+' ,plants were last watered at '+lastWatered+ ' please wait {}hrs for next watering request!'.format(limit))
            else:
                 bot.send_message(chat_id=update.callback_query.message.chat.id,text='Admin has temporarily disabled watering, it maybe a rainy day!')
                 self.weather(bot,update)
        else:
         bot.edit_message_text(chat_id=update.callback_query.message.chat_id,message_id=update.callback_query.message.message_id,
                          text="Unauthorized User {} ({}), please type&send:/start to begin ".format(update.callback_query.from_user.first_name,update.callback_query.from_user.id))
    
    def light(self,bot,update):
        logging.info('/lights,{},{}'.format(update.callback_query.from_user.first_name,update.callback_query.from_user.id))
        if(update.callback_query.from_user.id in self.approvedUsers):
            if(self.enableLight):
                
                
                limit = self.lightTimeLimit
                if (update.callback_query.from_user.id==self.adminId):
                    limit =0.3 #special admin privilage only wait for 3 mins to water plants, note off water thread takes 1+ min to finish
                tNow=time.time()
                if((tNow-self.timeLight)/60>limit): #edit to 10mins later
                
                #if((tNow-timeLight)>20): #(only for testing)
                    bot.edit_message_text(chat_id=update.callback_query.message.chat_id,message_id=update.callback_query.message.message_id, text='Flipping lights...')
                    flag = self.radioControl(update.callback_query.data)
                    
                    if(flag==True):
                        self.timeLight = time.time()
                        bot.send_message(chat_id=update.callback_query.message.chat.id,text='Lights are turned: '+self.status_s2+ ' by {} ({})'.format(update.callback_query.from_user.first_name,update.callback_query.from_user.id))
                else:        
                    lastLit = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(self.timeLight))
                    currentTime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                    bot.send_message(chat_id=update.callback_query.message.chat.id,text='Current time: '+currentTime+' ,lights were flipped on or off at '+lastLit+ ', please wait {}mins to switch!'.format(limit))
            else:
                 bot.send_message(chat_id=update.callback_query.message.chat.id,text='Admin has temporarily disabled lights control!') 
        
        else:
         bot.edit_message_text(chat_id=update.callback_query.message.chat_id,message_id=update.callback_query.message.message_id,
                          text="Unauthorized User {} ({}), please type&send:/start to begin ".format(update.callback_query.from_user.first_name,update.callback_query.from_user.id))
        
             
    def weather(self,bot,update):
        logging.info('/WeatherData,{},{}'.format(update.callback_query.from_user.first_name,update.callback_query.from_user.id))
        if(update.callback_query.from_user.id in self.approvedUsers):
        
            tNow = time.time()
            limit = self.weatherTimeLimit
            if (update.callback_query.from_user.id==self.adminId):
                limit =0.3
            if((tNow-self.cityWeatherData['currently']['time'])/60.0>=limit):
               self.cityWeatherData = forecast(self.darkskyKey,self.lat,self.long)
               #print('refreshed weather data')
            
            weatherTime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(self.cityWeatherData['currently']['time']))
            summary = self.cityWeatherData['currently']['summary']
            temp = self.cityWeatherData['currently']['temperature']
            humid = self.cityWeatherData['currently']['humidity']*100
            precip = self.cityWeatherData['currently']['precipProbability']*100
            message = 'At: {}, it is: {}, with temp :{:.2f}F, humidity: {:.2f}%, precipitation probability: {:.2f}%.\nInfo is updated every 30mins'.format(weatherTime,summary,temp,humid,precip)
            bot.edit_message_text(chat_id=update.callback_query.message.chat_id,message_id=update.callback_query.message.message_id,text=message)
        else:
         bot.edit_message_text(chat_id=update.callback_query.message.chat_id,message_id=update.callback_query.message.message_id,
                          text="Unauthorized User {} ({}), please type&send:/start to begin ".format(update.callback_query.from_user.first_name,update.callback_query.from_user.id))
    
    def recordVideo(self,bot,update):
        """ Record Video and Transmit it to the bot """
        logging.info('/Video,{},{}'.format(update.callback_query.from_user.first_name,update.callback_query.from_user.id))
        if(update.callback_query.from_user.id in self.approvedUsers):
            if(self.enableVideo):
        #query = update.callback_query
                self.enablePic= False #Pictures should be off while taking video
                
            
                tNow = time.time()
                limit =self.vidTimeLimit #all users have to wait limit mins to between taking pics.
                if (update.callback_query.from_user.id==self.adminId):
                    limit =0.3 #special admin privilage only wait for 0.3 mins
            
                if((tNow-self.timeVideo)/60>limit):
                    bot.edit_message_text(chat_id=update.callback_query.message.chat_id,message_id=update.callback_query.message.message_id, text='Taking 30sec Video,please wait 1min for transmission...')
                    with picamera.PiCamera() as camera:
                        camera.resolution = (640, 480)#(640, 480)
                        
                        #camera.start_preview()
                        camera.awb_mode = 'off'
                        camera.awb_gains = [self.awbRed,self.awbBlue] #red,blue, with blue filter noIR camera, make the red setting higher in white balance
                        camera.exposure_mode=self.expMode
                        #https://picamera.readthedocs.io/en/release-1.10/api_camera.html
                        # Camera warm-up time
                        time.sleep(3)
                        if not os.path.exists('./files/{}/'.format(update.callback_query.from_user.id)):
                            os.makedirs('./files/{}/'.format(update.callback_query.from_user.id))
                        camera.start_recording('./files/{}/vid.h264'.format(update.callback_query.from_user.id),quality=30)
                        camera.wait_recording(20)
                        camera.stop_recording()
                        #camera.stop_preview()
                    inputPath = './files/{}/vid.h264'.format(update.callback_query.from_user.id)
                    outPath = './files/{}/vid.mp4'.format(update.callback_query.from_user.id)
                        
                    command = 'MP4Box -add {} -new {}'.format(inputPath,outPath)
                    try:
                        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
                        logging.info(output)
                        
                    except subprocess.CalledProcessError as e:
                        print('FAIL:\ncmd:{}\noutput:{}'.format(e.cmd, e.output))
                        logging.info('FAIL:\ncmd:{}\noutput:{}'.format(e.cmd, e.output))
                        
                        
                    f = open(outPath,'rb')
                    bot.send_video(chat_id=update.callback_query.message.chat.id,
                                   video=f,
                                   caption='Current Video Taken by {} ({})'.format(update.callback_query.from_user.first_name,update.callback_query.from_user.id),timeout=120)
                    f.close()
                    self.timeVideo = time.time()
                     #Restore Pic Functionality, this will mess with disable admin function, fix later
                    logging.info('Exiting Video Thread Successfully...')
                else:
                    lastPicTaken = time.strftime('%H:%M:%S',time.localtime(self.timeVideo))
                    currentTime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                    bot.send_message(chat_id=update.callback_query.message.chat.id,text='Current time: '+currentTime+' ,please wait {}mins, last video was captured at: '.format(limit)+lastPicTaken)
                
                self.enablePic = True 
            else:
                    bot.send_message(chat_id=update.callback_query.message.chat.id,text='Function temporarily disabled!')
        else:
         bot.edit_message_text(chat_id=update.callback_query.message.chat_id,message_id=update.callback_query.message.message_id,
                          text="Unauthorized User {} ({}), please type&send:/start to begin ".format(update.callback_query.from_user.first_name,update.callback_query.from_user.id))
    

    def addIoTUser(self,bot,update,args):
        """ 
        Admin Command: add users manually
        Usage:
            /add 12345 324567 8726251
            
            The numbers are ids of users
            
        """
        
        logging.info('/add,{},{}'.format(update.message.from_user.first_name,update.message.from_user.id))
        try:
            if(update.message.from_user.id==self.adminId): #hardcoded for security only i can issue this command
                for arg in args:
                    self.approvedUsers[int(arg)]='manually_added'
                    
                msg =' '
                bot.send_message(chat_id=update.message.chat_id, text="User/Users: "+ msg.join(args)  +" added to IoT Control")
            else:
                bot.send_message(chat_id=update.message.chat_id, text="Unauthorized activity, only admin can issue this command!")
        except:
            bot.send_message(chat_id=update.message.chat_id, text="Unauthorized activity, or Bad argument!")
        
        
    def removeIoTUser(self,bot,update,args):
        """ 
        Admin Command: remove users manually
        Usage:
            /rm all
            /rm 123445
        """
        
        
        logging.info('/rm,{},{}'.format(update.message.from_user.first_name,update.message.from_user.id))
        
        try:
            if(update.message.from_user.id==self.adminId): #hardcoded for security only i can issue this command
                if(args[0]=='all'):
                    self.approvedUsers ={}
                    self.approvedUsers[self.adminId] = 'ZenOfAll'
                    bot.send_message(chat_id=update.message.chat_id, text="All users removed from IoT control!")
                else:
                    if(self.adminId!=int(args[0])): 
                        self.approvedUsers.pop(int(args[0]))
                        bot.send_message(chat_id=update.message.chat_id, text="User {} removed from IoT Control".format(args[0]))
                    else:
                        bot.send_message(chat_id=update.message.chat_id, text="Unauthorized action: Cannot remove Admin!".format(args[0]))
                
            else:
                bot.send_message(chat_id=update.message.chat_id, text="Unauthorized activity, only admin can issue this command!") 
        except:
            bot.send_message(chat_id=update.message.chat_id, text="Unauthorized activity or Bad argument!")
        
    

    def status(self,bot,update):
        if(update.callback_query.from_user.id in self.approvedUsers):
    
          logging.info('/status,{},{}'.format(update.callback_query.from_user.first_name,update.callback_query.from_user.id))
          currentTime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
          lastPic = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(self.timePic))
          lastLit = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(self.timeLight))
          lastWatered = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(self.timeWater))
          lastVideo = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(self.timeVideo))
          hello = "Hello {} (telegram_id:{}).\n".format(update.callback_query.from_user.first_name,update.callback_query.from_user.id)
          message0 = '\nCurrent Time is : {}'.format(currentTime) 
          message1 = '\nLights are: '+self.status_s2 +'\nWater is: ' + self.status_s1+ '\nLights were flipped: '+lastLit+ '\nLast Watered: '+lastWatered + '\nLast Pic:' +lastPic + '\nLast Video:' +lastVideo
          message2 = '\nLimits:- Pic: {}, Water: {}, Light: {}, Video: {}'.format(self.picTimeLimit,self.waterTimeLimit,self.lightTimeLimit,self.vidTimeLimit)
          message3 = '\nFunctions Status :- Pic: {}, Water: {}, Light: {}, Video: {}, AutoAdd: {}'.format(self.enablePic,self.enableWater,self.enableLight,self.enableVideo,self.enableAdd) 
          
          message4 = '\nCamera Awb =[{},{}], Exposure: {}'.format(self.awbRed, self.awbBlue, self.expMode)
          message = hello+message0+message1+message2+message3+message4
          bot.edit_message_text(chat_id=update.callback_query.message.chat_id,message_id=update.callback_query.message.message_id,text=message)
        else:
         bot.edit_message_text(chat_id=update.callback_query.message.chat_id,message_id=update.callback_query.message.message_id,
                          text="Unauthorized User {} ({}), please type&send:/start to begin ".format(update.callback_query.from_user.first_name,update.callback_query.from_user.id))
    
    
    def instructions(self,bot,update):
        logging.info('/Instructions,{},{}'.format(update.callback_query.from_user.first_name,update.callback_query.from_user.id))
        self.request()
        hello = 'Hello {} ({})\n'.format(update.callback_query.from_user.first_name,update.callback_query.from_user.id)

        autoAdd = '\n\nPlease Type: /start (and send) to be auto-added to IOT control\n\n'
        #visit ='To learn more visit:\n\n https://zenofall.com'
        message = hello+autoAdd
        
        bot.edit_message_text(chat_id=update.callback_query.message.chat_id,message_id=update.callback_query.message.message_id,text=message)

    def tutorial(self,bot,update):
        logging.info('/Tutorials,{},{}'.format(update.callback_query.from_user.first_name,update.callback_query.from_user.id))
        message =  'Please visit https://zenofall.com for tutorials & code\n'
        self.request()
        bot.edit_message_text(chat_id=update.callback_query.message.chat_id,message_id=update.callback_query.message.message_id,text=message)
    
    
    def fetchIoTUserList(self,bot,update):
        
        """ 
        Admin Command: add users manually
        Usage:
            /fetch
            
        """
                 
        logging.info('/fetch,{},{}'.format(update.message.from_user.first_name,update.message.from_user.id))
        try:
            if(update.message.from_user.id==self.adminId):
                msg1 =' '.join(map(str,self.approvedUsers))
                msg2 = ', '.join(map(str,self.approvedUsers.values()))
                
                bot.send_message(chat_id=update.message.chat_id, text="Current IoT controllers are: "+msg1+"\n\n\n"+"["+msg2+"]")
            else:
                bot.send_message(chat_id=update.message.chat_id, text="Unauthorized activity, only admin can issue this command!")
        except:
            bot.send_message(chat_id=update.message.chat_id, text="Unauthorized activity, only admin can issue this command!")
                    

    def disable(self,bot,update,args):
        
        """ 
        Admin Command: disable functions in button menu
        Usage:
            /disable 1  (for pic)
            /disable 2  (for water)
            /disable 3  (for light)
            /disable 4  (for video)
            /disable 5  (for add)
            /disable all (disable all)
            /disable status (get status)
            
        """
        
        
        logging.info('/disable,{},{}'.format(update.message.from_user.first_name,update.message.from_user.id))
        if(update.message.from_user.id==self.adminId): 
           
            if(args[0]=='all'):
                self.enablePic = False
                self.enableWater = False
                self.enableLight = False
                self.enableAdd = False
                self.enableVideo = False
                bot.send_message(chat_id=update.message.chat_id, text="Admin has disabled all controls")
            if (args[0]=='1'):
                self.enablePic=not(self.enablePic)
                bot.send_message(chat_id=update.message.chat_id, text="Pics enabled: "+str(self.enablePic))
            if (args[0]=='2'):
                self.enableWater = not(self.enableWater)
                bot.send_message(chat_id=update.message.chat_id, text="Water enabled: "+str(self.enableWater))
            if (args[0]=='3'):
                self.enableLight = not(self.enableLight)
                bot.send_message(chat_id=update.message.chat_id, text="Lights enabled: "+str(self.enableLight))
            if (args[0]=='4'):
                self.enableVideo = not(self.enableVideo)
                bot.send_message(chat_id=update.message.chat_id, text="Video enabled: "+str(self.enableVideo))
            if(args[0]=='5'):
                self.enableAdd = not(self.enableAdd)
                bot.send_message(chat_id=update.message.chat_id, text="Auto add enabled: "+str(self.enableAdd))
            
            if(args[0]=='status'):
                bot.send_message(chat_id=update.message.chat_id, text="pics enabled: "+str(self.enablePic) +", water enabled: " +str(self.enableWater)+ ", lights enabled: "+str(self.enableLight ) + ", auto add enabled: "+str(self.enableAdd ) + ", Video enabled: "+str(self.enableVideo ))
            
                
            
        else:
            bot.send_message(chat_id=update.message.chat_id, text="Unauthorized activity, only admin can issue this command!") 
        

    def setAwb(self,bot,update, args):
        
        """
        Admin function: set white balance
        Usage:
            /set 1.0 1.3 (red,blue)
        
        """
        
       
        logging.info('/setAwb,{},{}'.format(update.message.from_user.first_name,update.message.from_user.id))
        #set white balance manually
        try:
            if(update.message.from_user.id==self.adminId):
                
                if(args[0]=='status'):
                    bot.send_message(chat_id=update.message.chat_id, text="Current Awb Red:{} Blue:{}".format(self.awbRed,self.awbBlue))
                else:
                    self.awbRed = float(args[0])
                    self.awbBlue = float(args[1])
                    bot.send_message(chat_id=update.message.chat_id, text="Set Awb Red:{} Blue:{}".format(self.awbRed,self.awbBlue))
            else:
                bot.send_message(chat_id=update.message.chat_id, text="Unauthorized activity, only admin can issue this command!") 
        except:
            bot.send_message(chat_id=update.message.chat_id, text="Unauthorized activity or Bad argument!")
                
    def setExp(self,bot,update, args):
        
        """
        Admin function: set exposure
        Usage:
            /setExp auto [auto, sports, night]
        https://picamera.readthedocs.io/en/release-1.10/api_camera.html?highlight=exposure_mode#picamera.camera.PiCamera.exposure_mode
        """
        
        logging.info('/setExp,{},{}'.format(update.message.from_user.first_name,update.message.from_user.id))
        #set white balance manually
        try:
            if(update.message.from_user.id==self.adminId):
                
                
                if(args[0]=='status'):
                    bot.send_message(chat_id=update.message.chat_id, text="Current Exposure Mode:{}".format(self.expMode))
                else:
                    self.expMode = args[0]
                    
                    bot.send_message(chat_id=update.message.chat_id, text="Set ExpMode:{} ".format(self.expMode))
            else:
                bot.send_message(chat_id=update.message.chat_id, text="Unauthorized activity, only admin can issue this command!") 
        except:
            bot.send_message(chat_id=update.message.chat_id, text="Unauthorized activity or Bad argument!")
    
    def setLimit(self,bot,update,args):
        
        """
        Admin function: set time limits
        Usage:
            /setLimit pic 2.0
            /setLimit water 5.0
             
        """
        
        
        logging.info('/setLimit,{},{}'.format(update.message.from_user.first_name,update.message.from_user.id))
        #set white balance manually
        try:
            if(update.message.from_user.id==self.adminId):
                bot.send_message(chat_id=update.message.chat_id, text="pic(mins), water(hrs), light(mins), weather(mins), video(mins)")
                
                if(args[0]=='status'):
                    bot.send_message(chat_id=update.message.chat_id, text="Pic: {}mins ,Water:{}hrs, Light:{}mins, Weather: {}min, Video: {}min".format(self.picTimeLimit, self.waterTimeLimit, self.lightTimeLimit, self.weatherTimeLimit, self.vidTimeLimit))
                elif(args[0]=='pic'):
                    try:
                        self.picTimeLimit = float(args[1])
                        bot.send_message(chat_id=update.message.chat_id, text="picTimeLimit = {}".format(self.picTimeLimit))
                    except:
                        bot.send_message(chat_id=update.message.chat_id, text="Second argument has to be a float number")
                elif(args[0]=='water'):
                    try:
                        self.waterTimeLimit = float(args[1])
                        bot.send_message(chat_id=update.message.chat_id, text="waterTimeLimit = {}".format(self.waterTimeLimit))
                    except:
                        bot.send_message(chat_id=update.message.chat_id, text="Second argument has to be a float number")
                elif(args[0]=='lights'):
                    try:
                        self.lightTimeLimit = float(args[1])
                        bot.send_message(chat_id=update.message.chat_id, text="lightTimeLimit = {}".format(self.lightTimeLimit))
                    except:
                        bot.send_message(chat_id=update.message.chat_id, text="Second argument has to be a float number")
                        
                elif(args[0]=='weather'):
                    try:
                        self.weatherTimeLimit = float(args[1])
                        bot.send_message(chat_id=update.message.chat_id, text="weatherTimeLimit = {}".format(self.weatherTimeLimit))
                    except:
                        bot.send_message(chat_id=update.message.chat_id, text="Second argument has to be a float number")
                        
                elif(args[0]=='video'):
                    try:
                        self.vidTimeLimit = float(args[1])
                        bot.send_message(chat_id=update.message.chat_id, text="vidTimeLimit = {}".format(self.vidTimeLimit))
                    except:
                        bot.send_message(chat_id=update.message.chat_id, text="Second argument has to be a float number")
                        
                    
                    
                    
            else:
                bot.send_message(chat_id=update.message.chat_id, text="Unauthorized activity, only admin can issue this command!") 
        except:
            bot.send_message(chat_id=update.message.chat_id, text="Unauthorized activity or Bad argument!")