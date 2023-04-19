from aiogram import Bot, types
from aiogram.utils import executor
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import logging
import os
from dotenv import load_dotenv
from keyboard import InlineButtonsBuilder, GlobalButtonsBuilder
import texthandler
from texthandler import StatisticsState
from posthandler import MailHandler
from dbhandler import FromMailDBHandler, IntoTelegramDBHandler

load_dotenv()
ADMINS = tuple(int(admin) for admin in os.getenv('ADMINS').split(', '))
POST = os.getenv('POST')
POST_PASS = os.getenv('POST_PASS')
POST_DOMAIN = os.getenv('POST_DOMAIN')
db = FromMailDBHandler()   # for creation of all tables in db with first starting of this bot
db.close_connection()
storage = MemoryStorage()
bot = Bot(token=os.getenv('BOT_KEY'), parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(format='%(filename)s [LINE:%(lineno)d] #%(levelname)-8s [%(asctime)s] %(message)s',
                    level=logging.INFO)


@dp.message_handler(Command('start'))
async def welcome(message) -> None:
    if message.chat.id in ADMINS:
        await bot.send_message(message.chat.id,
                               f'Здравствуйте, {message.from_user.first_name}!\n'
                               f'Это бот для обработки и вывода статистики.\n'
                               f'Для обновления статистики используйте кнопку "Обновить статистику" или '
                               f'напишите "Обновить статистику" в чат.\n'                                   
                               f'Для вывода статистики используйте кнопку "Статистика" или '
                               f'напишите "Статистика" в чат.\n',
                               reply_markup=GlobalButtonsBuilder().get_start(),
                               parse_mode='Markdown')
    else:
        await bot.send_message(message.chat.id,
                               f'Здравствуйте, {message.from_user.first_name}!\n'
                               f'Это приватный бот, извините!',
                               parse_mode='Markdown')


@dp.message_handler(content_types=['text'])
async def get_message(message) -> None:
    if message.chat.id in ADMINS:
        if message.text == 'Статистика':
            products_list = await IntoTelegramDBHandler().get_products_list()
            await bot.send_message(message.chat.id, text='Выберите категории!',
                                   reply_markup=InlineButtonsBuilder().products_buttons_builder(products_list),
                                   parse_mode='Markdown')
            await StatisticsState.selected_product.set()
        if message.text == 'Обновить статистику':
            await bot.send_message(message.chat.id, 'Начинаю обработку писем!')
            mail_handler = MailHandler(POST, POST_PASS, POST_DOMAIN)
            mail_handler.handle_new_messages()
            await bot.send_message(message.chat.id, 'Сделано!')
        if message.text == 'Информация':
            await welcome(message)


@dp.message_handler(state=StatisticsState.entered_period)
async def entered_period(message, state: FSMContext) -> None:
    if message.chat.id in ADMINS:
        chat_id = message.chat.id
        answer = message.text
        await handle_selected_data(answer, state, chat_id)


async def handle_selected_data(answer: str, state: FSMContext, chat_id: int) -> None:
    if chat_id in ADMINS:
        await state.update_data(period=answer)
        data = await state.get_data()
        selected_period = data.get('period')
        selected_product = data.get('products')
        await state.finish()
        products_list = await IntoTelegramDBHandler().get_products_list()
        selected = texthandler.handle_entered(selected_period, selected_product, products_list)
        for product_id in selected[1]:
            msg_text = await IntoTelegramDBHandler().get_statistics(selected[0], product_id)
            await bot.send_message(chat_id, msg_text, parse_mode='HTML')


@dp.callback_query_handler(state=StatisticsState.selected_period, text_contains='period_')
async def period(call: types.CallbackQuery, state: FSMContext) -> None:
    if call.message.chat.id in ADMINS:
        answer = call.data
        await bot.edit_message_text(chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text='Ок')
        if answer == 'period_user':
            await call.message.answer('Введите период в формате:\n'
                                      '"дд.мм.гггг-дд.мм.гггг"')
            await StatisticsState.entered_period.set()
        else:
            chat_id = call.message.chat.id
            answer = call.data
            await handle_selected_data(answer, state, chat_id)


@dp.callback_query_handler(state=StatisticsState.selected_product, text_contains='product_')
async def product(call: types.CallbackQuery, state: FSMContext) -> None:
    if call.message.chat.id in ADMINS:
        answer = call.data
        await state.update_data(products=answer)
        await bot.edit_message_text(chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text='За какой период?',
                                    reply_markup=InlineButtonsBuilder().period_buttons_builder())
        await StatisticsState.selected_period.set()


if __name__ == '__main__':
    print('Запущен Бот!')
    executor.start_polling(dp)
