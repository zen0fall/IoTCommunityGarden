# -*- coding: utf-8 -*-
"""
Created on Sat Apr  7 13:26:28 2018

@author: Zen Of All LLC (zenofall.com)
"""


import threading
import os



from iotcontrol import iotcontrol
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from telegram.ext import Updater
from telegram.ext import CommandHandler , CallbackQueryHandler
from telegram.ext import MessageHandler, Filters
import logging
##############################################################################################
darkskyKey = '<Enter dark sky token>'
updater = Updater(token='<TELEGRAM TOKEN>') #Insert bot token
#required by bot to execute functions see example: https://python-telegram-bot.org/
control = iotcontrol(1234567,darkskyKey,33.8463634,-84.373057) 
# 1234567 is example admin id : find yours by going to web-api of telegram: https://api.telegram.org/bot<TOKEN>/getUpdates
#<TOKEN> is telegram token during bot creation
#read: https://zenofall.com/raspberry-pi-telegram-home-automation/
#replace: 33.8463634,-84.373057 by latitude longitude of your location from google maps
#we use adminId for special privileges on the bot

dispatcher = updater.dispatcher 
#bot examples: https://github.com/python-telegram-bot/python-telegram-bot/tree/master/examples

#logging is always good

#define logging format and file location



####################Bot User Functions ##############################

def start(bot,update): #display menu
    """ BotFunction: First function using which users are supposed to interact with this bot"""
   

    
    control.autoAdd(bot,update)
    
    
    keyboard = [[InlineKeyboardButton("Instructions", callback_data='5')], 
                 [InlineKeyboardButton("Take Pic", callback_data='1')],
                 [InlineKeyboardButton("NDVI Pic", callback_data='8')],
                 [InlineKeyboardButton("Video", callback_data='9')],
                 [InlineKeyboardButton("Local Weather", callback_data='7')],
                 [InlineKeyboardButton("Water Plants", callback_data='2')],
                [InlineKeyboardButton("Ligts on/off", callback_data='3')],
                [InlineKeyboardButton("Status", callback_data='4')],
                [InlineKeyboardButton("Tutorial & Code", callback_data='6')]
                ]
    
    message="Hello {} (telegram_id:{}).\nPlease read: Instructions first.\nType& send:/start again to pull up menu at any time.\n*Disclaimer: Bot logs all user commands. \nPlease Choose: \n".format(update.message.from_user.first_name,update.message.from_user.id)
    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_message(chat_id=update.message.chat_id,text=message, reply_markup=reply_markup)
            

def button(bot,update):
    """ BotFunction: Function that implements the button callbacks"""
    query = update.callback_query
    bot.answer_callback_query(callback_query_id=query.id, text="Choice registered,processing request..")
    
        
    if(query.data=='1'):
         
        
        #control.sendPic(bot,update,False)
        t=threading.Thread(target=control.sendPic,args=(bot,update,False))
        t.setDaemon(True)
        t.start()

    if(query.data=='8'):
        #global enablePic
        
        t=threading.Thread(target=control.sendPic,args=(bot,update,True))
        t.setDaemon(True)
        t.start()

    if(query.data=='9'):
        #global enablePic
      
        t=threading.Thread(target=control.recordVideo,args=(bot,update))
        t.setDaemon(True)
        t.start()

    if(query.data=='2'):
        
        control.water(bot,update)
    
    if(query.data=='3'):
        
        control.light(bot,update)
         
    if(query.data=='7'):
        
        control.weather(bot,update)

    if(query.data=='4'):
    
     control.status(bot,update)

    if(query.data=='5'):
        control.instructions(bot,update)

    
    if(query.data=='6'):
        control.tutorial(bot,update)

############# Admin only program functions####################
            

def unknown(bot, update):
    """ Unkwown command handler"""
    logging.info('/unknown,{},{}'.format(update.message.from_user.first_name,update.message.from_user.id))
    bot.send_message(chat_id=update.message.chat_id, text="Sorry Command Not Recognized! Type: /start for all user actions.")            

def shutdown():
    
    updater.stop()
    updater.is_idle=False

def stop(bot, update): #hardcoded for security only i can issue this command
    """ 
    Admin Command: stop the bot
    Usage:
        /stop
        
    """
    #global adminId
    logging.info('/stop,{},{}'.format(update.message.from_user.first_name,update.message.from_user.id))
    if(update.message.from_user.id==control.getAdminId()):
        bot.send_message(chat_id=update.message.chat_id, text="Stopping Server!")    
        threading.Thread(target=shutdown).start()
    else:
        bot.send_message(chat_id=update.message.chat_id, text="ERROR: Unauthorized User!")

def addIoTUser(bot,update,args):
    """ 
    Admin Command: add users manually
    Usage:
        /add 12345 324567 8726251
        
        The numbers are ids of users
        
    """
    control.addIoTUser(bot,update,args)

        
        
def removeIoTUser(bot,update,args):
    """ 
    Admin Command: remove users manually
    Usage:
        /rm all
        /rm 123445
    """
    control.removeIoTUser(bot,update,args)

        

def fetchIoTUserList(bot,update):
    
    """ 
    Admin Command: add users manually
    Usage:
        /fetch
        
    """
    control.fetchIoTUserList(bot,update)

                    

def disable(bot,update,args):
    
    """ 
    Admin Command: disable functions in button menu
    Usage:
        /disable 1  (for pic)
        /disable 2  (for water)
        /disable 3  (for light)
        /disable 4  (for video)
        /disable all (disable all)
        
    """
    control.disable(bot,update,args)

    

def setAwb(bot,update, args):
    
    """
    Admin function: set white balance
    Usage:
        /set 1.0 1.3 (red,blue)
    
    """
    control.setAwb(bot,update,args)

            
def setExp(bot,update, args):
    
    """
    Admin function: set white balance
    Usage:
        /setExp auto [auto, sports, night]
    https://picamera.readthedocs.io/en/release-1.10/api_camera.html?highlight=exposure_mode#picamera.camera.PiCamera.exposure_mode
    """
    control.setExp(bot,update,args)


def setLimit(bot,update,args):
    
    """
    Admin function: set time limits
    Usage:
        /setLimit pic 2.0
        /setLimit water 5.0
         
    """
    control.setLimit(bot,update,args)
   
                     
        
#def clear(bot,update,chat_data):
#    chat_data.clear()

    
       
    
####____global variables____#########
 


#Kill ServoBlaster - interferes with GPIO #something specific to me
###comment this out if you dont have servo blaster
try:
    os.system("sudo killall servod")      
except Exception as e:
    print(e)
    pass
############ #comment ends
    
#####____HANDLERS_____#######
#bot examples: https://github.com/python-telegram-bot/python-telegram-bot/tree/master/examples
start_handler = CommandHandler('start', start)
stop_handler = CommandHandler('stop', stop)
#menu_handler = CommandHandler('menu', menu)
addHandler = CommandHandler('add',addIoTUser, pass_args=True)
removeHandler = CommandHandler('rm',removeIoTUser,pass_args=True)
fetchHandler = CommandHandler('fetch',fetchIoTUserList)
disable_Handler = CommandHandler('disable',disable,pass_args=True)
awbHandler = CommandHandler('setawb',setAwb,pass_args=True)
expModeHandler = CommandHandler('setexp',setExp,pass_args=True)
setLimitHandler = CommandHandler('setLimit',setLimit,pass_args=True)
#clearHandler = CommandHandler('clear',clear,pass_chat_data=True)
unknown_handler= MessageHandler(Filters.command, unknown)

#####____DISPATCHERS_____#######
dispatcher.add_handler(start_handler)
dispatcher.add_handler(stop_handler)
#dispatcher.add_handler(menu_handler)
dispatcher.add_handler(addHandler)
dispatcher.add_handler(removeHandler)
dispatcher.add_handler(fetchHandler)
dispatcher.add_handler(disable_Handler)
dispatcher.add_handler(awbHandler)
dispatcher.add_handler(expModeHandler)
dispatcher.add_handler(setLimitHandler)
dispatcher.add_handler(CallbackQueryHandler(button))

#dispatcher.add_handler(clearHandler)
dispatcher.add_handler(unknown_handler) #Always keep unkown handler last else commands not recognized
#start the bot client - poll for server messages
updater.start_polling()
updater.idle()

