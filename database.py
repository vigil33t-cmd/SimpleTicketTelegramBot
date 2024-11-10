from datetime import datetime, UTC

import bson
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from config import config

client = AsyncIOMotorClient(config.MONGO_URI)
ticketDB = client[config.MONGO_DB_NAME]


async def createTicket(userID, ticketText, ticketID, ticketMessageID):
    ticket = {
        "_id": ticketID,
        "TicketStatus": 1,
        "Date": datetime.now(UTC),
        "TicketText": ticketText,
        "TicketRating": None,
        "TicketMessageID": ticketMessageID,
        "TelegramUserID": userID
    }
    await ticketDB.tickets.insert_one(ticket)


async def updateTicketStatus(ticketID, status):
    await ticketDB.tickets.update_one(
        {"_id": ObjectId(ticketID)},
        {"$set": {"TicketStatus": status}}
    )


async def getTicketByID(ticketID):
    ticket = await ticketDB.tickets.find_one(
        {"_id": ObjectId(ticketID)}
    )
    return ticket


async def setTicketRating(ticketID, rating):
    await ticketDB.tickets.update_one(
        {"_id": ObjectId(ticketID)},
        {"$set": {"TicketRating": rating}}
    )

async def initUser(userID):
    userInfo = {
        "TelegramUserID": userID,
        "ClosedTickets": [],
    }
    await ticketDB.user.insert_one(userInfo)

async def getUser(userID):
    user = await ticketDB.user.find_one(
        {"TelegramUserID": userID}
    )
    return user

async def closeTicket(userID, ticketID):
    user = await getUser(userID)
    tickets = user['ClosedTickets']
    tickets.append(bson.ObjectId(ticketID))
    await ticketDB.user.update_one(
        {"TelegramUserID": userID},
        {"$set":{"ClosedTickets": tickets}}
    )