import os
from webbrowser import get

import telebot
from telebot.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from telebot import types
import certifi
import time
from datetime import datetime, timedelta
import operator
import pymongo
from pymongo import MongoClient
import certifi
import copy

# Database setup
cluster = MongoClient("mongodb+srv://bryan:bryan@cluster0.fmdfb.mongodb.net/splitease?retryWrites=true&w=majority",
tlsCAFile=certifi.where())
db = cluster["splitease"]
collection_trips = db["trips"]
receipts = db["receipts"]
users = db["users"]

# Telegram Bot setup
API_KEY = '5802653714:AAGRvJoocdJ0K9Vb0ouaKU6YVZNMW5BgnkI'
bot = telebot.TeleBot(API_KEY)

bot.set_my_commands([
    BotCommand('start', 'Starts the bot'),
    BotCommand('newtrip', 'Creates a new trip'),
    BotCommand('delete', 'Deletes a trip'),
    BotCommand('edit', 'Edits a trip'),
    BotCommand('trips', 'View all trips'),
    BotCommand('overview', 'Shows the overview of the trip')
])


#Commands
@bot.message_handler(commands=['start'])
def start(message):
    """
    Command that welcomes the user 
    """

    chat_id = message.chat.id

    message_text = """ Hi @
                \nWelcome to SplitEase, where I will help you split your overseas bills with ease! 
                \nTo add a new trip, use the /newtrip command followed by the trip name.
                \nFor more details, check out /help!"""
    bot.send_message(chat_id, message_text, parse_mode= 'HTML')

list_of_names = []

# Handle the '/newtrip' command
@bot.message_handler(commands=['newtrip'])
def newtrip(message):
    chat_id = message.chat.id

    words = message.text.split()

    if len(words) < 2:
        bot.send_message(message.chat.id, "Please provide a country name after the command e.g.'/newtrip <country>'.")
        return
    # Get the country argument
    country = words[1]
    # Check if the country name is valid
    if not country.isalpha():
        bot.send_message(message.chat.id, "Invalid country name. Please provide a valid country name.")
        return
    
    #Add to Database
    if collection_trips.find_one({"tripname" : country, "chatid": chat_id}) == None:
        result = {"tripname" : country, "chatid": chat_id}
        collection_trips.insert_one(result)
        print(collection_trips.find_one())
    else:
        bot.send_message(chat_id, f"Trip to {country} already exists.")
        return

    # Create the inline keyboard with the buttons
    keyboard = InlineKeyboardMarkup()
    button1 = InlineKeyboardButton("Add me to the trip", callback_data="add_to_trip" + country)
    button2 = InlineKeyboardButton("Show the list", callback_data="show_list")
    keyboard.add(button1, button2)
    # Send the message with the inline keyboard
    bot.send_message(chat_id, f"Click the button to add your name for your {country} trip", reply_markup=keyboard)

# Handle callback queries
@bot.callback_query_handler(func=lambda call: call.data.startswith("add_to_trip"))
def add_to_trip(call):
    # Get the user's name
    username = call.from_user.username
    country = call.data.replace("add_to_trip", "")
    # Add the user's username to the list
    if list_of_names.__contains__(username): 
        bot.answer_callback_query(call.id, f"Your username {username} has already been added to the trip!")  
        return  
    list_of_names.append(username)
    chat_id = call.message.chat.id

    #Add user to database if user is not already present in database
    if users.find_one({"username": username, "chatid": chat_id, "tripname": country}) == None:
        users.insert_one({"chatid": chat_id, "amount_spent": 0, "amount_paid": 0 ,"username": username, "tripname": country})
        
    bot.answer_callback_query(call.id, f"Your username {username} has been added to the trip!")
    
@bot.callback_query_handler(func=lambda call: call.data == "show_list")
def show_list(call):
    chat_id = call.message.chat.id
    if list_of_names:
        message_text = "The list of names: \n" + "\n".join(list_of_names)
    else:
        message_text = "The list is empty"
    bot.send_message(chat_id, message_text)

@bot.message_handler(commands=['delete'])
def delete(message):
    """
    Command that deletes a trip
    """
    tripname = message.text.split()[1]
    chat_id = message.chat.id
    query = {"tripname" : tripname, 
            "chatid": chat_id}
    collection_trips.delete_one(query)
    print(collection_trips.deleted_count, " documents deleted")

    message_text = """ Deleted the trip {}
                    """.format(tripname)
    bot.send_message(chat_id, message_text, parse_mode= 'HTML')

@bot.message_handler(commands=['edit'])
def edit(message):
    """
    Edits the name of the trip 
    """

    chat_id = message.chat.id
    original_tripname = message.text.split()[1]
    new_tripname = message.text.split()[2]
    
    query = {"tripname" : original_tripname, 
            "chatid": chat_id}
    new_values = {"$set": {"tripname" : new_tripname}}
    collection_trips.update_one(query, new_values)

    message_text = """ Trip name has been updated to {}""".format(new_tripname)
    bot.send_message(chat_id, message_text, parse_mode= 'HTML')
    
@bot.message_handler(commands=['trips'])
def trips(message):
    """
    Command that shows all trips belonging to the group
    """

    chat_id = message.chat.id
    results = collection_trips.find({"chatid": chat_id})
    response = ""
    counter = 1
    
    for result in results :
        response += str(counter) + ". " + result["tripname"] + "\n"
        counter = counter + 1

    bot.send_message(chat_id, response, parse_mode= 'HTML')

@bot.message_handler(commands=['overview'])
def overview(message):
    """
    Command that shows overview of payments for the trip
    """

    chat_id = message.chat.id
    country = message.text.split()[1]
    results = list(users.find({"chatid": chat_id, "tripname": country}))        
    response = ""
    counter = 1
    
    
    owes = {}
    result_count = len(results)
    print("Number of results:", result_count)

    results_copy = copy.deepcopy(results)

    for result in results_copy:
        paid = result["amount_paid"]
        spent = result["amount_spent"]
        balance = paid - spent
        # If the person has a positive balance, they need to get paid
        if balance > 0:
            # Iterate over the people dictionary again to find the person to whom they owe money
            for x in results_copy:
                if x["username"] != result["username"]:
                    balance2 = x["amount_paid"] - x["amount_spent"]
                    if balance2 < 0:
                        # If the other person has a negative balance, they need to pay others
                        amount = min(abs(balance), abs(balance2))
                        # Add the transaction to the owes dictionary
                        if result["username"] not in owes:
                            owes[result["username"]] = {}
                        if x["username"] not in owes[result["username"]]:
                            owes[result["username"]][x["username"]] = amount
                        else:
                            owes[result["username"]][x["username"]] += amount
                        balance -= amount
                        x["amount_paid"] += amount
                        if (balance == 0):
                            break

    for result in results:
        response = response + str(counter) + ". " + result["username"] + "\n"
        response = response + "Amount Spent: <b>" + str(result["amount_spent"]) + "</b>\n"
        response = response + "Amount Paid: <b>" + str(result["amount_paid"]) + "</b>\n"
        response = response + "Amount Owed: <b>" + str(result["amount_paid"] - result["amount_spent"]) + "</b>\n\n"
        if result["username"] in owes:
            for key, value in owes[result["username"]].items():
                response = response + "Owes: " + str(key) + ": <b>" + str(value) + "</b>\n"
        response += "\n"
        counter = counter + 1

    if response:
        bot.send_message(chat_id, response, parse_mode='HTML')
    else:
        bot.send_message(chat_id, "Error: response text is empty")


# Running the bot
while True:
    try:
        bot.polling()
    except Exception:
        time.sleep(15)