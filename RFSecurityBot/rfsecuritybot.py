#!usr/bin/python

##
### RF Security bot start script
###
### Written by @KaiserHaz
##

##
### Imports
##
import telegram     as tg
import telegram.ext as tgExt
import RPi.GPIO     as gpio
import time
from datetime import datetime as dt
from uuid import uuid4

##
### Common variables
##
NULLSENSOR = 0
PRESSENSOR = 1
MAGSENSOR  = 2

sensDict = {NULLSENSOR:"No sensor",
            PRESSENSOR:"Pressure sensor",
            MAGSENSOR:"Magnetic sensor"}

cmdString = ["/help","/start","/stop","/log","/list","/test"]

# Event class
class ev(object):

        timestamp = 0
        sType     = NULLSENSOR
        
        def __init__(self, ts=0, st=NULLSENSOR):
                self.timestamp = ts
                self.sType     = st


        def __repr__(self):
                return "Event class"

        def __str__(self):
                if(self.sType == PRESSENSOR):
                        return str("-> @"+self.timestamp.strftime('%c')+
                                   ": Pressure sensor triggered\n")
                elif(self.sType == MAGSENSOR):
                        return str("-> @"+self.timestamp.strftime('%c')+
                                   ": Magnetic sensor triggered\n")
                else:
                        return ""


# Report log
llog   = []   # Data log
lmutex = True # Log mutex for writing

# Trigger counters
trigCntGlobal = 0                       # Global count since start of bot
trigCntPress  = 0
trigCntMag    = 0

# RF Security Bot variables
rfSecuBotIsStarted     = 0

##
### Hardware configuration
##

# Set GPIO mode
gpio.setmode(gpio.BCM)                  # Use BCM chip GPIO mode

# GPIO 23 and 24 as input
# Set to pull-down since we are expecting a rising edge  
gpio.setup(23, gpio.IN, pull_up_down=gpio.PUD_DOWN)
gpio.setup(24, gpio.IN, pull_up_down=gpio.PUD_DOWN)

# GPIO callbacks
def pressureCallback(channel):
        global llog
        global lmutex
        global trigCntGlobal
        global trigCntPress

        ep = ev(ts=dt.now(), st=PRESSENSOR)
        
        print("---> Pressure sensor triggered at "+
              ep.timestamp.strftime("%c")+"\n")

        rfSecuBot.sendMessage('@fyprfsecuritychannel', "Pressure sensor "+
                        "triggered.")

        while(not lmutex):
                pass

        lmutex = False
        
        llog.insert(0, ep)
        trigCntGlobal = trigCntGlobal + 1
        trigCntPress = trigCntPress + 1

        lmutex = True


def magneticCallback(channel):
        global llog
        global lmutex
        global trigCntGlobal
        global trigCntMag

        em = ev(ts=dt.now(), st=MAGSENSOR)
        
        print("---> Magnetic sensor triggered at "+
              em.timestamp.strftime("%c")+"\n")

        rfSecuBot.sendMessage('@fyprfsecuritychannel', "Magnetic sensor "+
                        "triggered.")

        while(not lmutex):
                pass

        lmutex = False
        
        llog.insert(0, em)
        trigCntGlobal = trigCntGlobal + 1
        trigCntMag = trigCntMag + 1
        
        lmutex = True

# Register event detection
def startEventLogging():
        gpio.add_event_detect(23, gpio.RISING, callback=pressureCallback,
                              bouncetime=1000)
        gpio.add_event_detect(24, gpio.RISING, callback=magneticCallback,
                              bouncetime=1000)


# Remove event detection in case of stop
def stopEventLogging():
        gpio.remove_event_detect(23)
        gpio.remove_event_detect(24)


##
### Logging functions
##

# Periodic logging function
def logUpdate():
        global llog
        global lmutex

        updTime = dt.now()
        
        while(not lmutex):
                pass
        
        lmutex = False
        
        # Check log timestamps
        for i in llog:
                if((updTime - i.timestamp).total_seconds() > 300):
                        llog.remove(i)
                
        lmutex = True


# Formatting function
def logFormat():
        global llog
        global lmutex
        
        logUpdate() # Asynchronous call to logUpdate to make sure
                    #  that the log has been updated at the time
                    #  of formatting

        while(not lmutex):
                pass
        
        lmutex = False
        
        flog = []
        cnt = 0
        
        for i in reversed(llog):
                if(cnt < 10):
                        flog.append(i.__str__())
                        cnt = cnt + 1
                else:
                        break
        
        lmutex = True

        return flog


def listFormat():
        global llog
        global lmutex
        global sensDict
        
        logUpdate() # Asynchronous call to logUpdate to make sure
                    #  that the log has been updated at the time
                    #  of formatting

        while(not lmutex):
                pass

        lmutex = False
        
        flog = []
        flog.append("===== Sensors =====\n\n")

        for k,v in sensDict.items():
                if(k == NULLSENSOR):
                        pass
                else:
                        trigCnt = 0
                        
                        for i in llog:
                                if(i.sType == k):
                                        trigCnt = trigCnt + 1
			
			flog.append("-> "+v+"\n")

                        if(trigCnt < 1):
                                flog.append("    No trips in the last"+
					    " 5 minutes.\n")
                        else:
                                flog.append("    No. of times tripped: "+
                                            str(trigCnt)+"\n")
        
        if(len(flog) ==0):
                flog.append(sensDict[NULLSENSOR])

        lmutex = True
        
        return flog


##
### Software configuration
##

print("--> Starting bot setups")

# Token file open
fd = open('/home/pi/tg/rfsecuritybot.token')

# Get token
rfSecuBotToken = fd.readline()

# Start bot using token
rfSecuBot = tg.Bot(rfSecuBotToken)
print(rfSecuBot.getMe()) ## TODO: Make a prettier print!!!

# Command callbacks

def bhelp(bot, update):
        print("--> Help command received\n")
        helpString="Hello, my name is RF Security Bot.\nI "             +\
              "monitor the security triggers for\nthe security system." +\
              "\n"                                                      +\
              "Command list:\n"                                         +\
              "/help : Prints out this message\n"                       +\
              "/start: Start the security monitoring\n"                 +\
              "/stop : Stop the security monitoring\n"                  +\
              "/log  : Prints out the last 10 events since powerup\n"   +\
              "/list : Lists the sensors that have triggered within"    +\
              "the last 5 minutes\n"                                    +\
              "/test : Dummy test command for bot communication debug\n"
        print("> "+helpString)
	bot.sendMessage('@fyprfsecuritychannel', helpString)


def bstart(bot, update):
        print("--> Start command received\n")
        global llog
        global rfSecuBotIsStarted
        global trigCntGlobal
        global trigCntPress
        global trigCntMag

        print("> Starting system...\n")
        
        if(rfSecuBotIsStarted==0):
                rfSecuBotIsStarted = 1
                trigCntPress = 0
                trigCntMag = 0

                llog = []
                
                startEventLogging()
                
                print("> Start success!\n")
                bot.sendMessage('@fyprfsecuritychannel',
                                "The monitoring system has been started")
        else:
                print("> System already started!\n")
                bot.sendMessage('@fyprfsecuritychannel',
                                "The system has already been started!")
        
        
def bstop(bot, update):
        print("--> Stop command received\n")
        global rfSecuBotIsStarted

        print("> Stopping system...\n")

        stopEventLogging()

        rfSecuBotIsStarted = 0

        bot.sendMessage('@fyprfsecuritychannel',
                                "The monitoring system has been stopped")
        

def blog(bot, update):
        print("--> Log command received\n")
        
        logString = "Log of last 10 occurrences:\n"
        logString = logString+''.join(logFormat())

        print("> "+logString)
	bot.sendMessage('@fyprfsecuritychannel', logString)


def blist(bot, update):
        print("--> List command received\n")

        listString = ""
        listString = listString+''.join(listFormat())

        print("> "+listString)
	bot.sendMessage('@fyprfsecuritychannel', listString)


def btest(bot, update):
        print("--> Test command received\n")
        print("> Test command.\n")
	bot.sendMessage('@fyprfsecuritychannel', "Test command.")


# Inline query handler so that the bot can be evoked right from the channel
def chInQuery(bot, update):
        print("--> Inline query received\n")
        query = update.inline_query.query
        fEx = 0
        results = list()

        if("/" in query):
                results.append(tg.InlineQueryResultArticle(
                        id=uuid4(),
                        title="help",
                        input_message_content=tg.InputTextMessageContent("/help"),
                        description="Prints out help message"))
        
                results.append(tg.InlineQueryResultArticle(
                        id=uuid4(),
                        title="start",
                        input_message_content=tg.InputTextMessageContent("/start"),
                        description="Start the security monitoring"))
        
                results.append(tg.InlineQueryResultArticle(
                        id=uuid4(),
                        title="stop",
                        input_message_content=tg.InputTextMessageContent("/stop"),
                        description="Stop the security monitoring"))
        
                results.append(tg.InlineQueryResultArticle(
                        id=uuid4(),
                        title="log",
                        input_message_content=tg.InputTextMessageContent("/log"),
                        description="Print out last 10 events"))
        
                results.append(tg.InlineQueryResultArticle(
                        id=uuid4(),
                        title="list",
                        input_message_content=tg.InputTextMessageContent("/list"),
                        description="List triggered sensors within 5 mins"))
        
                results.append(tg.InlineQueryResultArticle(
                        id=uuid4(),
                        title="test",
                        input_message_content=tg.InputTextMessageContent("/test"),
                        description="Dummy command for comm debug"))
                
                if(query in cmdString):
                        fEx = 1
        else:
                results.append(tg.InlineQueryResultArticle(
                        id=uuid4(),
                        title="ERROR!",
                        input_message_content=tg.InputTextMessageContent(query),
                        description="Command unknown"))
                fEx = 0

        if(fEx == 1):
                globals()['b'+query.replace('/','')](bot, update)
        else:
                pass

        bot.answerInlineQuery(update.inline_query.id, results=results)


# Command handlers for each callbacks
rfSecuBotHelpHdlr = tgExt.CommandHandler ('help'  , bhelp)
rfSecuBotStartHdlr = tgExt.CommandHandler('start' , bstart)
rfSecuBotStopHdlr = tgExt.CommandHandler ('stop'  , bstop)
rfSecuBotLogHdlr = tgExt.CommandHandler  ('log'   , blog)
rfSecuBotListHdlr = tgExt.CommandHandler ('list'  , blist)
rfSecuBotTestHdlr = tgExt.CommandHandler ('test'  , btest)
rfSecuBotInlineHdlr = tgExt.InlineQueryHandler(chInQuery)

# Bot updater
rfSecuBotUpd = tgExt.Updater(rfSecuBotToken)
rfSecuBotDisp = rfSecuBotUpd.dispatcher

# Add handler to dispatcher
rfSecuBotDisp.addHandler(rfSecuBotHelpHdlr)
rfSecuBotDisp.addHandler(rfSecuBotStartHdlr)
rfSecuBotDisp.addHandler(rfSecuBotStopHdlr)
rfSecuBotDisp.addHandler(rfSecuBotLogHdlr)
rfSecuBotDisp.addHandler(rfSecuBotListHdlr)
rfSecuBotDisp.addHandler(rfSecuBotTestHdlr)
rfSecuBotDisp.addHandler(rfSecuBotInlineHdlr)

rfSecuBotUpd.start_polling(poll_interval=1.0,clean=True)
rfSecuBotUpd.idle()

while True:
	pass

# Just in case...
print("--> Bot exiting\n")
gpio.cleanup()
rfSecuBotUpd.stop()
rfsecuBot = 0
print("\n\n\t *** EOF[] *** \t\n\n")
quit()

# EOF []
