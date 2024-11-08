from datetime import datetime, UTC

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from config import config

client = AsyncIOMotorClient(config.MONGO_URI)
db = client[config.MONGO_DB_NAME]


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
    await db.tickets.insert_one(ticket)


async def updateTicketStatus(ticketID, status):
    await db.tickets.update_one(
        {"_id": ObjectId(ticketID)},
        {"$set": {"TicketStatus": status}}
    )


async def getTicketByID(ticketID):
    ticket = await db.tickets.find_one(
        {"_id": ObjectId(ticketID)}
    )
    return ticket


async def setTicketRating(ticketID, rating):
    await db.tickets.update_one(
        {"_id": ObjectId(ticketID)},
        {"$set": {"TicketRating": rating}}
    )
