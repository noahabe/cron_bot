"""
main code for the cron_bot
"""

import logging
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import InlineQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler
import configparser as cfg

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

#the scheduler
sched = None 

#a dictionary from groupid's to all of their crontab expressions
ALLJOBS = dict()

def get_parser()->cfg.ConfigParser:
	config_file = "config.cfg"
	parser = cfg.ConfigParser()
	parser.read(config_file)
	return parser

def read_token(parser:cfg.ConfigParser, key:str):
	return parser.get('creds',key)

def private_talk(update,context):
	update.message.reply_text("this bot doesn't make sense in private"
		" communication")	
	return None

class Job:
	def __init__(self,groupid:int,message:str,context):
		'''groupid is the id that telegram servers gives you
		'''
		self.groupid = groupid
		self.message = message
		self.context = context

	def __call__(self):
		self.context.bot.send_message(self.groupid,self.message)	
	
	def printJob(self):
		'''this function is for debugging purposes only.'''
		print(f"GROUPID: {self.groupid}  MESSAGE: {self.message}")
		return 0

class CrontabExpression:
	def __init__(self,m,h,dom,mon,dow):
		self.m = m 	# minute (0-59)
		self.h = h	# hour   (0-23) 
		self.dom = dom	# day of month (1-31)
		self.mon = mon	# month (1-12)
		self.dow = dow	# day of the week (0-6)

		if self.m.isdigit():
			self.m = int(self.m)
		if self.h.isdigit():
			self.h = int(self.h)
		if self.dom.isdigit():
			self.dom = int(self.dom)
		if self.mon.isdigit():
			self.mon = int(self.mon)
		if self.dow.isdigit():
			self.dow = int(self.dow)

	def check(self):
		'''raise ValueError if the above values are not in the range'''
		#note the short-circuit evaluation here.
		if not (self.m == '*' or (self.m >= 0 and self.m <= 59)):
			raise ValueError("minute must be in the range 0 to 59") 
		if not (self.h == '*' or (self.h >= 0 and self.h <= 23)):
			raise ValueError("hour must be in the range from 0 to 23") 
		if not (self.dom == '*' or (self.dom >= 1 and self.dom <= 31)):
			raise ValueError("day of month must be in the range from 1 to 31")
		if not (self.mon == '*' or (self.mon >= 1 and self.mon <= 12)):
			raise ValueError("month must be in the range from 1 to 12")
		if not (self.dow == '*' or (self.dow >= 0 and self.dow <= 6)):
			raise ValueError("day of the week must be in the range from 0 to 6")	
	def get(self):
		return {"minute":self.m,
			"hour":self.h,
			"day":self.dom,
			"month":self.mon,
			"day_of_week":self.dow,
			"year":'*',
			"week":'*',
			"second":1,
			}
	
def add_a_job(update,context):
	global sched,ALLJOBS

	option = context.args
	if len(option) < 6:
		update.message.reply_text("not enough parameters passed, tap on /help")
		return
	expr = CrontabExpression(*option[0:5])	

	try:
		expr.check()
	except ValueError as e:
		update.message.reply_text( "syntax error: {}".format(str(e)) )
		return
	except:
		update.message.reply_text("serious bug inside code!! notify the dev @data53."
			"A screenshot would be appreciated...")
		return
		
	text = ' '.join(option[5:])
#	print(expr.get(),text) #for debugging purposes.
	j = Job(update.effective_chat.id,text,context)
	s = sched.add_job(j,'cron',**expr.get()) #the sched's job instance 	

	if not j.groupid in ALLJOBS:  
		ALLJOBS[j.groupid] = []
	
	ALLJOBS[j.groupid].append([j,s])
#	j.printJob() #for debugging purposes.

def list_all_jobs(update,context):
	msg = ""
	counter = 1 
	if (not update.effective_chat.id in ALLJOBS) or (len(ALLJOBS[update.effective_chat.id]) == 0):
		update.message.reply_text("Empty jobs. Use the add command to add one")
		return
	for x in ALLJOBS[update.effective_chat.id]:
		msg += str(counter) + ") " + x[0].message + "\n"
		counter += 1 
	update.message.reply_text(msg)
	return

def remove_a_job(update,context):
	job_tag = int(context.args[0]) - 1 
	if (not update.effective_chat.id in ALLJOBS) or (len(ALLJOBS[update.effective_chat.id]) == 0):
		update.message.reply_text("Empty jobs. Use the add command to add one")
		return
	ALLJOBS[update.effective_chat.id][job_tag][1].remove()
	del ALLJOBS[update.effective_chat.id][job_tag]
	return 
	
def group_help(update,context):
	msg = ""
	msg += "/add [cron tab expression] text-message\n"
	msg += "/list - to list all of the jobs that are scheduled\n"
	msg += "/remove [id] - to remove a job that is already scheduled\n"
	msg += "\n"
	update.message.reply_text(msg)

def main():
	#set up the scheduler
	global sched 
	sched = BackgroundScheduler(daemon=True)
	sched.start()

	parser = get_parser()
	botname = read_token(parser,"botname")	
	updater = Updater(read_token(parser,"token"),use_context=True)

	dispatcher = updater.dispatcher
	
	#communication in a private message
	unknown_handler = MessageHandler(Filters.chat_type.private, private_talk) 
	
	#communication in a group			
	add_handler = CommandHandler("add",add_a_job)
	list_handler = CommandHandler("list",list_all_jobs)
	remove_handler = CommandHandler("remove",remove_a_job)
	help_handler = CommandHandler("help",group_help)

	#dispatching all of the handlers.
	
	dispatcher.add_handler(unknown_handler)	
	dispatcher.add_handler(add_handler)	
	dispatcher.add_handler(list_handler)
	dispatcher.add_handler(remove_handler)
	dispatcher.add_handler(help_handler)

	updater.start_polling()
	updater.idle()

if __name__ == '__main__':
	main()

