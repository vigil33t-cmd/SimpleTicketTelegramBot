import logging
from datetime import datetime

import bson
from aiogram import Bot, Dispatcher, types
from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from config import config
from database import createTicket, updateTicketStatus, setTicketRating, getTicketByID, getUser, initUser, closeTicket

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

class TicketForm(StatesGroup):
    cabinetName = State()
    description = State()

@dp.message(Command('stats'))
async def getStats(message: types.Message):
    user = await getUser(message.from_user.id)
    # [ticket['TicketText'] for ticket in [await getTicketByID(tickets) for tickets in user['ClosedTickets']]]

    await message.answer('''
    <b>bold</b>, <strong>bold</strong>
<i>italic</i>, <em>italic</em>
<u>underline</u>, <ins>underline</ins>
<s>strikethrough</s>, <strike>strikethrough</strike>, <del>strikethrough</del>
<span class="tg-spoiler">spoiler</span>, <tg-spoiler>spoiler</tg-spoiler>
<b>bold <i>italic bold <s>italic bold strikethrough <span class="tg-spoiler">italic bold strikethrough spoiler</span></s> <u>underline italic bold</u></i> bold</b>
<a href="http://www.example.com/">inline URL</a>
<a href="tg://user?id=259134928">inline mention of a user</a>
<tg-emoji emoji-id="5368324170671202286">👍</tg-emoji>
<code>inline fixed-width code</code>
<pre>pre-formatted fixed-width code block</pre>
<pre><code class="language-python">pre-formatted fixed-width code block written in the Python programming language</code></pre>
<blockquote>Block quotation started\nBlock quotation continued\nThe last line of the block quotation</blockquote>
<blockquote expandable>Expandable block quotation started\nExpandable block quotation continued\nExpandable block quotation continued\nHidden by default part of the block quotation started\nExpandable block quotation continued\nThe last line of the block quotation</blockquote>
    ''', parse_mode="HTML")


@dp.message(Command("start"))
async def startCommand(message: types.Message):
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="Оставить заявку")
    await message.answer(text="Выберите действие:",
                         reply_markup=keyboard.as_markup(resize_keyboard=True))


@dp.message(F.text == "Оставить заявку")
async def openTicket(message: types.Message, state: FSMContext):
    # user = await getUser(message.from_user.id)
    # if user is not None:
    #     await message.answer("Вы не можете создавать сами себе заявки.\n")
    #     return

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
    await message.answer(f"✅ Заявка с номером {str(ticketID)[-4:]} принята.")
    userData = await state.get_data()
    ticketText = f"Кабинет: {userData['cabinet_name']}\nОписание: {message.text}"

    inlineKeyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Закрыть заявку", callback_data=f"close_ticket:{ticketID}")]
    ])
    sentMessage = await bot.send_message(chat_id=config.GROUP_CHAT_ID,
                                         text="Поступила новая заявка!\n\n"
                                              f"Номер заявки: {str(ticketID)[-4:]}\n"
                                              f"Кабинет\n"
                                              f"\t\t\t{userData['cabinet_name']}\n"
                                              f"Описание заявки\n"
                                              f"\t\t\t{message.text}",
                                         reply_markup=inlineKeyboard)

    await bot.pin_chat_message(chat_id=config.GROUP_CHAT_ID,
                                                message_id=sentMessage.message_id)

    await bot.delete_message(chat_id=config.GROUP_CHAT_ID, message_id=int(sentMessage.message_id) + 1)

    await createTicket(ticketText=ticketText,
                       userID=message.from_user.id,
                       ticketID=ticketID,
                       ticketMessageID=sentMessage.message_id)

    await state.clear()


@dp.callback_query(F.data.startswith("close_ticket"))
async def closeTicketCallback(callBackQuery: types.CallbackQuery):
    ticketID = callBackQuery.data.split(":")[1]
    ticket = await getTicketByID(ticketID)
    messageID = ticket["TicketMessageID"]

    user = await getUser(callBackQuery.from_user.id)
    if user is None:
        await initUser(callBackQuery.from_user.id)

    await closeTicket(callBackQuery.from_user.id, ticketID)

    await updateTicketStatus(ticketID, status=0)
    await bot.unpin_chat_message(chat_id=config.GROUP_CHAT_ID,
                                 message_id=messageID)

    await callBackQuery.answer("Заявка закрыта.")

    ratingKeyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ " + str(i),
                              callback_data=f"rate:{i}:{ticketID}") for i in range(1, 6)],

        [InlineKeyboardButton(text="❌ Отказаться от оценки ",
                              callback_data="rate:skip")]
    ])

    await bot.send_message(chat_id=ticket['TelegramUserID'],
                           text=f"Ваша заявка c номером <code>{ticketID[-4:]}</code> "
                                f"от {datetime.strftime(ticket['Date'], '%d.%m.%Y %H:%M')}\n"
                                f"\n"
                                f"{ticket["TicketText"]}\n\n"
                                f"❌ <b>Закрыта</b>",
                           parse_mode="HTML")

    await bot.delete_message(chat_id=config.GROUP_CHAT_ID,
                             message_id=messageID)

    await bot.send_message(chat_id=ticket['TelegramUserID'],
                           text="Оцените качество работы от 1⭐️ до 5⭐️",
                           reply_markup=ratingKeyboard)


@dp.callback_query(F.data.startswith("rate"))
async def rateTicket(callback_query: types.CallbackQuery):
    callback = callback_query.data.split(":")
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text=f"Вы поставили оценку <b>{callback[1]}</b>⭐️.",
                                parse_mode='HTML')
    if callback[1] != 'skip':
        await setTicketRating(callback[2], int(callback[1]))
        await callback_query.answer(f"Вы поставили оценку <b>{callback[1]}</b>⭐️.")

        await bot.send_message(chat_id=config.GROUP_CHAT_ID,
                               text=f"Пользователь поставил оценку {callback[1]}⭐️"
                                    f" в заявке <code>{callback[2][-4:]}</code>.",
                               parse_mode='HTML')
    else:
        await bot.send_message(chat_id=config.GROUP_CHAT_ID,
                               text=f"Пользователь отказался от оценки {callback[1]}⭐️"
                                    f" в заявке <code>{callback[2][-4:]}</code>.",
                               parse_mode='HTML')
        await callback_query.answer("Вы отказались от оценки.")


if __name__ == "__main__":
    dp.run_polling(bot)
