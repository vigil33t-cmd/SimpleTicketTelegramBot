import logging

import bson
from aiogram import Bot, Dispatcher, types
from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from config import config
from database import createTicket, updateTicketStatus, setTicketRating, getTicketByID

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)


class TicketForm(StatesGroup):
    cabinetName = State()
    description = State()


@dp.message(Command("start"))
async def startCommand(message: types.Message):
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="Оставить заявку")
    await message.answer("Выберите действие:",
                         reply_markup=keyboard.as_markup(resize_keyboard=True))


@dp.message(F.text == "Оставить заявку")
async def openTicket(message: types.Message, state: FSMContext):
    await message.answer("Введите номер или название кабинета")
    await state.set_state(TicketForm.cabinetName)


@dp.message(TicketForm.cabinetName)
async def cabinetName(message: types.Message, state: FSMContext):
    await state.update_data(cabinet_name=message.text)
    await message.answer("Опишите проблему")
    await state.set_state(TicketForm.description)


@dp.message(TicketForm.description)
async def generateTicket(message: types.Message, state: FSMContext):
    ticketID = bson.ObjectId()
    userData = await state.get_data()
    ticketText = f"Кабинет: {userData['cabinet_name']}\nОписание: {message.text}"

    inlineKeyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Закрыть заявку", callback_data=f"close_ticket:{ticketID}")]
    ])
    sentMessage = await bot.send_message(chat_id=config.GROUP_CHAT_ID,
                                         text=ticketText,
                                         reply_markup=inlineKeyboard)

    await bot.pin_chat_message(chat_id=config.GROUP_CHAT_ID,
                               message_id=sentMessage.message_id)

    await createTicket(ticketText=ticketText,
                       userID=message.from_user.id,
                       ticketID=ticketID,
                       ticketMessageID=sentMessage.message_id)

    await state.clear()


@dp.callback_query(F.data.startswith("close_ticket"))
async def closeTicket(callBackQuery: types.CallbackQuery):
    ticketID = callBackQuery.data.split(":")[1]
    await updateTicketStatus(ticketID, status=0)
    ticket = await getTicketByID(ticketID)
    messageID = ticket["TicketMessageID"]
    await bot.unpin_chat_message(chat_id=config.GROUP_CHAT_ID,
                                 message_id=messageID)
    await callBackQuery.answer("Заявка закрыта.")

    ratingKeyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(i),
                              callback_data=f"rate:{i}:{ticketID}") for i in range(1, 6)],
        [InlineKeyboardButton(text="Отказаться от оценки", callback_data="rate:skip")]
    ])
    await bot.send_message(chat_id=ticket['TelegramUserID'],
                           text="Оцените качество работы от 1 до 5:",
                           reply_markup=ratingKeyboard)


@dp.callback_query(F.data.startswith("rate"))
async def rateTicket(callback_query: types.CallbackQuery):
    callback = callback_query.data.split(":")
    if callback[1] != 'skip':
        await setTicketRating(callback[2], int(callback[1]))
        await callback_query.answer(f"Вы поставили оценку {callback[1]}.")
    else:
        await callback_query.answer("Вы отказались от оценки.")


if __name__ == "__main__":
    dp.run_polling(bot)
