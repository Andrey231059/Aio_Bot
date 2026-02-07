import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile, CallbackQuery
import random

from gtts import gTTS
import os

from config import TOKEN
import keyboards as kb

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
   await message.answer('Этот бот умеет выполнять команды: \n /start \n /link \n /dynamic', reply_markup=kb.main)

@dp.message(F.text == "Привет")
async def aitext(message: Message):
   await message.answer(f'Привет, {message.from_user.first_name}')

@dp.message(F.text == "Пока")
async def aitext(message: Message):
   await message.answer(f'До свидания, {message.from_user.first_name}')

@dp.message(Command('link'))
async def link(message: Message):
   await message.answer(f'Что желаете, {message.from_user.first_name}', reply_markup=kb.inline_keyboard_test)

# @dp.callback_query(Command('dynamic'))
# async def dynamic(callback: CallbackQuery):
#    await callback.answer("Показать больше", show_alert=True)
#    await callback.message.edit_text('Показать больше', reply_markup=await kb.test_keyboard())

# 👇 Обработка команды /dynamic — отправляем первую кнопку
@dp.message(Command('dynamic'))
async def dynamic(message: Message):
    await message.answer("Нажмите кнопку ниже:", reply_markup=kb.get_show_more_keyboard())

# 👇 Обработка нажатия на "Показать больше"
@dp.callback_query(F.data == "show_more")
async def show_more(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите опцию:",
        reply_markup=kb.get_options_keyboard()
    )
    await callback.answer()  # подтверждаем нажатие (убираем часики)

# 👇 Обработка выбора опций
@dp.callback_query(F.data.in_({"option_1", "option_2"}))
async def handle_option(callback: CallbackQuery):
    option_text = "Опция 1" if callback.data == "option_1" else "Опция 2"
    await callback.message.answer(f"Вы выбрали: {option_text}")
    await callback.answer()  # убираем индикатор загрузки

async def main():
   await dp.start_polling(bot)

if __name__ == '__main__':
   asyncio.run(main())
