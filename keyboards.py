from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

main = ReplyKeyboardMarkup(keyboard=[
   [KeyboardButton(text="Привет")], [KeyboardButton(text="Пока")]
], resize_keyboard=True)

inline_keyboard_test = InlineKeyboardMarkup(inline_keyboard=[
   [InlineKeyboardButton(text="Новости", url='https://ria.ru/')],
   [InlineKeyboardButton(text="Музыка", url='https://music.yandex.ru/promo/lt-pay-promo/?get-plus=4&utm_source=direct_search&utm_medium=paid_performance&utm_campaign=705690007%7CMSCAMP-4_%5BMU-P%5D_%7BWM%3AS%7D_RU-225_goal-UPS_TGO-Generic-LP%2F%2Fpromo&utm_term=музыка%20онлайн&utm_content=cid%7C705690007%7Cgid%7C5690189184%7Caid%7C17482503203%7Cdvc%7Cdesktop&etext=2202.TaFyBnPbNu0Kj-DQufmxBHrrm-UgC089-kaX0Sl9cQBndXBqbHNkZGVxdGJuY2Js.cb4142896eeeec33dc9bad4438f2eff7383be3fd&yclid=18143452280886919167')],
   [InlineKeyboardButton(text="Видео", url='https://www.1tv.ru/news?=')]
   #  [InlineKeyboardButton(text="Новости", callback_data='news')],
   #  [InlineKeyboardButton(text="Музыка", callback_data='music')],
   #  [InlineKeyboardButton(text="Видео", callback_data='video')]
])

test = ["Опция 1", "Опция 2"]

async def test_keyboard():
   keyboard = InlineKeyboardBuilder()
   for key in test:
       keyboard.add(InlineKeyboardButton(text=key))
   return keyboard.adjust(1).as_markup()

# Кнопка "Показать больше"
def get_show_more_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Показать больше", callback_data="show_more")]
    ])

# Кнопки "Опция 1" и "Опция 2"
def get_options_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Опция 1", callback_data="option_1")],
        [InlineKeyboardButton(text="Опция 2", callback_data="option_2")]
    ])

