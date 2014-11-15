#!usr/bin/python

#imports
from Tkinter import *
from tkMessageBox import *
from tkFileDialog import *
from tkColorChooser import *
from tkSimpleDialog import *
import time
import sys
import requests
import json
import shelve
import os.path
import smtplib

#program
class Person(object):
	def __init__(self, first='?', last='?', phone='?', address='?', mail='?'):
		self.first = first
		self.last = last
		self.phone = phone
		self.address = address
		self.mail = mail

	def set(self,option,value):
		if option == 0:
			self.first = value
		elif option == 1:
			self.last = value
		elif option == 2:
			self.phone = value
		elif option == 3:
			self.address = value
		else:
			self.mail = value

	def get(self,option):
		if option == 0:
			return self.first
		elif option == 1:
			return self.last
		elif option == 2:
			return self.phone
		elif option == 3:
			return self.address
		else:
			return self.mail

class AddressBook(Frame):
	''' simple address book script.
		Features:
			Check distance from contact
			send contact an Email

		takes command line arguments:
		gmail username
		gmail password
	'''

	def __init__(self,filename, parent = None, **kwargs):
		# call parent constructor
		#pack and configure the frame
		Frame.__init__(self,parent, **kwargs)
		self.pack()
		self.master.resizable(width=False, height = False)
		self.config(width = 640, height = 480, pady='10',padx = '10')

		#MAIL variables
		#gmail username and gmail password as command line arguments
		#create a variable objects for the subject and the message
		#so that we can retrieve the strings from the entry boxes
		self.gmail_user = sys.argv[1]
		self.gmail_password = sys.argv[2]
		self.gmail_subject = StringVar()
		self.gmail_message = StringVar()

		#Maps Variables
		#create var objects for the current position and the mode (driving,walking,cycling...)
		# Current should be in the format Street ,City, Country
		self.current = StringVar()
		self.mode = StringVar()

		#CONTACTS
		#contact dict to store the Person objects with their current position in the listbox as keys
		self.contacts = {}
		self.options = ['First name','Second name','Phone number','Address','Email']

		#LABEL
		Label(self,text = 'Address Book').pack(side='top')

		#LIST FRAME
		self.listFrame = Frame(self)
		self.listFrame.pack(side='left')
		self.list = Listbox(self.listFrame)
		self.list.pack()

		#Start the database
		self.filename = filename
		self.startData()

		#Buttons
		self.buttonFrame = Frame(self)
		self.buttonFrame.pack(side = 'right',anchor = 'n')
		Button(self.buttonFrame,text = 'Add',width = 5,command = self.add).pack()
		Button(self.buttonFrame,text = 'Delete',width = 5,command = self.delete).pack()
		Button(self.buttonFrame,text = 'Details',width = 5,command = self.details).pack()
		Button(self.buttonFrame,text='Map It',width=5,command=self.mapit_mode).pack()
		Button(self.buttonFrame,text='Current',width = 5,command = self.setCurrent).pack()
		Button(self.buttonFrame,text='Mail',width=5,command=self.mail_window).pack()
		Button(self.buttonFrame,text = 'Quit',width = 5,command = self.quitProgram).pack()

	def add(self):
		''' creates the add form 

			toplevel - The window on which to display the form
			self.vars - list of variables for the entries , used to get the info in the entries
		'''
		toplevel = Toplevel()
		self.vars = []
		for i in xrange(len(self.options)):
			Label(toplevel, text = self.options[i]).grid(row = i, column = 0)
			var = StringVar()
			Entry(toplevel,textvariable = var).grid(row=i,column=1)
			self.vars.append(var)
		Button(toplevel,text='Cancel',command = toplevel.destroy).grid(row=len(self.options),column = 0)
		Button(toplevel,text='Save',command = lambda : self.save(toplevel)).grid(row=len(self.options),column = 1)

	def save(self,toplevel):
		''' Save the contact information in the contacts dictionary and in the listbox object '''
		person = Person()
		for i in xrange(len(self.vars)):
			person.set(i, self.vars[i].get())
		self.list.insert('end',(person.first, person.last))
		self.contacts[len(self.contacts)] = person
		toplevel.destroy()


	def details(self):
		''' get the current selected item , create a window on which to display the info and then create the labels on the window'''
		person = self.list.curselection()[0]
		toplevel = Toplevel()
		for i in xrange(len(self.options)):
			Label(toplevel,text = self.options[i]+': ',padx = 5,pady = 5).grid(row = i, column = 0)
			Label(toplevel, text = self.contacts[person].get(i),padx =5,pady=5).grid(row=i,column=1)

	def delete(self):
		''' gets the current selected item in the list , deletes it from the list and the dictionary and adjusts the key in the dictionary to match the 
			position in the listbox'''
		to_delete = self.list.curselection()[0]
		del self.contacts[to_delete]
		self.list.delete(to_delete)
		for key in self.contacts.keys():
			if key > to_delete:
				self.contacts[key-1] = self.contacts[key]
				del self.contacts[key]

	def setCurrent(self):
		''' sets the current location'''
		toplevel = Toplevel()
		toplevel.title('Current Location')
		Entry(toplevel,textvariable=self.current).pack(side='left')
		Button(toplevel,text='Save',command = toplevel.destroy).pack(side='right')

	def mapit_mode(self):
		''' creates a window on which to display the info
			asks for mode'''
		toplevel = Toplevel()
		modes = ['driving','walking','bicycling','transit']
		for i in xrange(0,len(modes),2):
			Radiobutton(toplevel,text=modes[i],variable = self.mode,value = modes[i],width = 10).grid(row=i,column=0)
			Radiobutton(toplevel,text=modes[i+1],variable = self.mode,value = modes[i+1],width = 10).grid(row=i,column=1)
		self.mode.set('walking')
		Button(toplevel,text='Cancel',command = toplevel.destroy,width = 10).grid(row = len(modes),column = 0)
		Button(toplevel,text='Search',command=lambda :self.mapit(toplevel),width = 10).grid(row = len(modes),column = 1)
		

	def mapit(self,toplevel):
		''' destroys the mode window,
			gets the address of the current seleced item in the list,
			builds a dictionary of parameters and sends a request to google maps api,
			finally creates Labels with the relevant info from the response (which is converted from json object to python object)'''
		toplevel.destroy()
		current = self.current.get()
		end = self.contacts[self.list.curselection()[0]].address
		params = {}
		params['origin'] = self.prepare_destination(current)
		params['destination'] = self.prepare_destination(end)
		params['mode'] = self.mode.get()
		google_response = requests.get('https://maps.googleapis.com/maps/api/directions/json',params = params)
		results = google_response.json()
		new_window = Toplevel()
		Label(new_window,text = 'Starting Point:').grid(row=0,column=0)
		Label(new_window,text = results['routes'][0]['legs'][0]['start_address']).grid(row=0,column = 1)
		Label(new_window,text = 'End Point:').grid(row=1,column=0)
		Label(new_window,text = results['routes'][0]['legs'][0]['end_address']).grid(row=1,column = 1)
		Label(new_window,text = 'Distance:').grid(row=2,column=0)
		Label(new_window,text = results['routes'][0]['legs'][0]['distance']['text']).grid(row=2,column = 1)
		Label(new_window,text = 'Duration:').grid(row=3,column=0)
		Label(new_window,text = results['routes'][0]['legs'][0]['duration']['text']).grid(row=3,column = 1)
		Label(new_window,text = 'Mode:').grid(row=4,column=0)
		Label(new_window,text = self.mode.get()).grid(row=4,column = 1)


	def prepare_destination(self,string):
		''' strips all the spaces and unwanted symobls from the address'''
		raw_results = string.split(',')
		results = []
		for string in raw_results:
			if ' ' in string.strip():
				results.append(string.strip().replace(' ','+'))
			else:
				results.append(string.strip())
		return ','.join(results)

	def mail_window(self):
		''' creates a window with subject and message entry fields and send button '''
		toplevel = Toplevel()
		send_from = self.gmail_user
		send_to = [self.contacts[self.list.curselection()[0]].mail]
		Label(toplevel,text = 'Subject').grid(row=0,column=0)
		Entry(toplevel,textvariable = self.gmail_subject).grid(row=0,column=1)
		Label(toplevel,text = 'Message').grid(row=1,column=0)
		Entry(toplevel,textvariable=self.gmail_message).grid(row=1,column=1)
		Button(toplevel,text='Send',command =lambda: self.send_mail(send_from,send_to,toplevel)).grid(row=2,column=1)

	def send_mail(self,send_from,send_to,toplevel):
		''' creates an instance of SMTP object, connects to google and sends the email to the currently selected contact'''
		server = smtplib.SMTP()
		server.connect('smtp.gmail.com',587)
		server.ehlo()
		server.starttls()
		server.login(self.gmail_user,self.gmail_password)
		message = 'From: %s\nTo: %s\nSubject: %s\n\n%s' % (send_from,send_to,self.gmail_subject.get(),self.gmail_message.get())
		server.sendmail(send_from,send_to,message)
		server.close()
		toplevel.destroy()



	def startData(self):
		''' converts the shelve object to a python dictionary'''
		database = shelve.open(self.filename)
		if database:
			self.contacts = database['contacts']
			for key in sorted(self.contacts.keys()):
				self.list.insert(str(key), (self.contacts[key].first, self.contacts[key].last))
		database.close()

	def quitProgram(self):
		''' saves the dictionary onto the shelve objects and quits'''
		database = shelve.open(self.filename)
		database['contacts'] = self.contacts
		database.close()
		self.quit()

if __name__=='__main__':
	AddressBook('database').mainloop()
