# import asyncio
# from aiogram import Bot, Dispatcher
# from aiogram.filters import CommandStart, Command
# from aiogram.types import Message
# from config import TOKEN
#
#
# bot = Bot(token=TOKEN)
# dp = Dispatcher()
#
# @dp.message(Command('help'))
# async def help(message: Message):
#     await message.answer("Этот бот умеет выполнять команды:\n/start\n/help")
#
# @dp.message(CommandStart())
# async def start(message: Message):
#     await message.answer("Привет, я бот!")
#
# async def main():
#     await dp.start_polling(bot)
#
# if __name__ == "__main__":
#     asyncio.run(main())
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from config import TOKEN

# Конфигурация Open-Meteo API (не требует API ключа)
MOSCOW_LAT = 55.7558
MOSCOW_LON = 37.6173
WEATHER_URL = f"https://api.open-meteo.com/v1/forecast?latitude={MOSCOW_LAT}&longitude={MOSCOW_LON}&current_weather=true&timezone=auto&windspeed_unit=ms"

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(Command('help'))
async def help(message: Message):
    await message.answer(
        "🌤️ <b>Погодный бот для Москвы</b>\n\n"
        "Доступные команды:\n"
        "/start - приветствие\n"
        "/help - эта справка\n"
        "/weather - текущая погода\n"
        "/forecast - прогноз на 3 дня\n"
        "/detailed - подробная погода\n"
    )


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "👋 Привет! Я погодный бот для Москвы.\n\n"
        "Я показываю актуальную погоду и прогноз.\n"
        "Используй команды:\n"
        "• /weather - текущая погода\n"
        "• /forecast - прогноз на 3 дня\n"
        "• /detailed - подробная информация\n\n"
        "Для справки используй /help"
    )


@dp.message(Command('weather'))
@dp.message(Command('weather_now'))
async def weather_now(message: Message):
    """Получение текущей погоды"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WEATHER_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    weather_info = parse_current_weather(data)
                    await message.answer(weather_info, parse_mode='HTML')
                else:
                    await message.answer("❌ Не удалось получить данные о погоде. Попробуйте позже.")
    except Exception as e:
        print(f"Ошибка: {e}")
        await message.answer("⚠️ Произошла ошибка при получении погоды.")


# @dp.message(Command('detailed'))
# async def detailed_weather(message: Message):
#     """Подробная погода с дополнительными параметрами"""
#     try:
#         # Расширенный запрос с дополнительными параметрами
#         detailed_url = f"https://api.open-meteo.com/v1/forecast?latitude={MOSCOW_LAT}&longitude={MOSCOW_LON}&current_weather=true&hourly=temperature_2m,relative_humidity_2m,pressure_msl,precipitation&timezone=auto&windspeed_unit=ms"
#
#         async with aiohttp.ClientSession() as session:
#             async with session.get(detailed_url) as response:
#                 if response.status == 200:
#                     data = await response.json()
#                     weather_info = parse_detailed_weather(data)
#                     await message.answer(weather_info, parse_mode='HTML')
#                 else:
#                     await message.answer("❌ Не удалось получить подробные данные.")
#     except Exception as e:
#         print(f"Ошибка: {e}")
#         await message.answer("⚠️ Ошибка при получении подробной погоды.")

@dp.message(Command('detailed'))
async def detailed_weather_simple(message: Message):
    """Упрощенная версия подробной погоды"""
    try:
        # Более простой запрос без поиска по часам
        detailed_url = f"https://api.open-meteo.com/v1/forecast?latitude={MOSCOW_LAT}&longitude={MOSCOW_LON}&current_weather=true&hourly=temperature_2m,relative_humidity_2m&timezone=auto&windspeed_unit=ms"

        async with aiohttp.ClientSession() as session:
            async with session.get(detailed_url) as response:
                if response.status == 200:
                    data = await response.json()
                    weather_info = parse_detailed_simple(data)
                    await message.answer(weather_info, parse_mode='HTML')
                else:
                    await message.answer("❌ Не удалось получить данные.")
    except Exception as e:
        print(f"Ошибка: {e}")
        await message.answer("⚠️ Ошибка при получении данных.")

# @dp.message(Command('detailed'))
# async def detailed_weather(message: Message):
#     """Подробная погода с дополнительными параметрами"""
#     try:
#         # Используем другой эндпоинт с большим количеством данных
#         detailed_url = f"https://api.open-meteo.com/v1/forecast?latitude={MOSCOW_LAT}&longitude={MOSCOW_LON}&current_weather=true&hourly=temperature_2m,relative_humidity_2m,pressure_msl,precipitation,cloudcover&timezone=auto&windspeed_unit=ms&forecast_days=1"
#
#         async with aiohttp.ClientSession() as session:
#             async with session.get(detailed_url) as response:
#                 if response.status == 200:
#                     data = await response.json()
#                     weather_info = parse_detailed_weather(data)
#                     await message.answer(weather_info, parse_mode='HTML')
#                 else:
#                     await message.answer("❌ Не удалось получить подробные данные.")
#     except Exception as e:
#         print(f"Ошибка: {e}")
#         await message.answer("⚠️ Ошибка при получении подробной погоды.")
#
#
# def parse_detailed_weather(data):
#     """Парсинг подробной погоды - исправленная версия"""
#     try:
#         current = data['current_weather']
#         hourly = data['hourly']
#
#         temp = current['temperature']
#         wind_speed = current['windspeed']
#         wind_direction = current['winddirection']
#         weather_code = current['weathercode']
#
#         # Получаем текущее время
#         current_time = current['time']
#
#         # Ищем ближайший час в hourly данных
#         hourly_times = hourly['time']
#
#         # Преобразуем время в формат для сравнения (оставляем только час)
#         current_hour = current_time.split('T')[1][:2]
#
#         # Ищем индекс с таким же часом
#         hour_index = None
#         for i, hourly_time in enumerate(hourly_times):
#             if hourly_time.split('T')[1][:2] == current_hour:
#                 hour_index = i
#                 break
#
#         if hour_index is None:
#             # Если не нашли точное совпадение, берем первый элемент
#             hour_index = 0
#
#         # Получаем данные для найденного часа
#         humidity = hourly['relative_humidity_2m'][hour_index]
#         pressure = hourly['pressure_msl'][hour_index]
#         precipitation = hourly['precipitation'][hour_index]
#         cloudcover = hourly['cloudcover'][hour_index] if 'cloudcover' in hourly else None
#
#         weather_desc = get_weather_description(weather_code)
#         weather_emoji = get_weather_emoji(weather_code)
#         wind_dir = get_wind_direction(wind_direction)
#
#         # Конвертируем давление в мм рт.ст.
#         pressure_mmhg = round(pressure * 0.750062)
#
#         # Формируем сообщение
#         detailed_message = (
#             f"{weather_emoji} <b>Подробная погода в Москве</b>\n"
#             f"══════════════════════\n"
#             f"🌡 <b>Температура:</b> {temp:.1f}°C\n"
#             f"💧 <b>Влажность:</b> {humidity}%\n"
#             f"📊 <b>Давление:</b> {pressure_mmhg} мм рт.ст.\n"
#             f"💨 <b>Ветер:</b> {wind_speed:.1f} м/с {wind_dir}\n"
#             f"🌧 <b>Осадки:</b> {precipitation} мм\n"
#         )
#
#         if cloudcover is not None:
#             cloud_desc = get_cloud_cover_description(cloudcover)
#             detailed_message += f"☁️ <b>Облачность:</b> {cloudcover}% ({cloud_desc})\n"
#
#         detailed_message += (
#             f"📌 <b>Состояние:</b> {weather_desc}\n"
#             f"══════════════════════\n"
#             f"<i>Данные на {current_time}</i>"
#         )
#
#         return detailed_message
#
#     except Exception as e:
#         print(f"Detailed parse error: {e}")
#         import traceback
#         traceback.print_exc()
#         return "⚠️ Ошибка обработки подробных данных. Попробуйте позже."


def get_cloud_cover_description(percentage):
    """Описание облачности по проценту"""
    if percentage < 10:
        return "ясно"
    elif percentage < 30:
        return "малооблачно"
    elif percentage < 70:
        return "переменная облачность"
    elif percentage < 90:
        return "облачно"
    else:
        return "пасмурно"


# Также обновим функцию parse_forecast для правильного форматирования даты:
def parse_forecast(data):
    """Парсинг прогноза на 3 дня - исправленная версия"""
    try:
        daily = data['daily']

        forecast_message = "📅 <b>Прогноз погоды на 3 дня</b>\n══════════════════════\n"

        # Русские названия месяцев
        months_ru = ['', 'янв', 'фев', 'мар', 'апр', 'мая', 'июн',
                     'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

        for i in range(min(3, len(daily['time']))):  # Защита от выхода за границы
            date_str = daily['time'][i]
            temp_max = daily['temperature_2m_max'][i]
            temp_min = daily['temperature_2m_min'][i]
            weather_code = daily['weathercode'][i]
            precipitation = daily['precipitation_sum'][i] if 'precipitation_sum' in daily else 0
            wind_max = daily['windspeed_10m_max'][i] if 'windspeed_10m_max' in daily else 0

            weather_desc = get_weather_description(weather_code)
            weather_emoji = get_weather_emoji(weather_code)

            # Парсим дату
            year, month, day = map(int, date_str.split('-'))

            # Форматируем дату: 1 фев
            formatted_date = f"{day} {months_ru[month]}"

            # Определяем день недели
            import datetime
            date_obj = datetime.date(year, month, day)
            weekdays = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
            weekday = weekdays[date_obj.weekday()]

            forecast_message += (
                f"\n📆 <b>{formatted_date} ({weekday})</b>\n"
                f"{weather_emoji} {weather_desc}\n"
                f"⬆️  <b>Макс:</b> {temp_max:.1f}°C\n"
                f"⬇️  <b>Мин:</b> {temp_min:.1f}°C\n"
                f"💨 <b>Ветер:</b> {wind_max:.1f} м/с\n"
                f"🌧 <b>Осадки:</b> {precipitation} мм\n"
                f"────────────────\n"
            )

        forecast_message += "\n<i>Используй /weather для текущей погоды</i>"

        return forecast_message

    except Exception as e:
        print(f"Forecast parse error: {e}")
        import traceback
        traceback.print_exc()
        return "⚠️ Ошибка обработки прогноза."


def parse_detailed_simple(data):
    """Упрощенный парсинг подробной погоды"""
    try:
        current = data['current_weather']
        hourly = data['hourly']

        temp = current['temperature']
        wind_speed = current['windspeed']
        wind_direction = current['winddirection']
        weather_code = current['weathercode']

        # Берем первую запись из hourly как приблизительные данные
        humidity = hourly['relative_humidity_2m'][0] if hourly['relative_humidity_2m'] else 50

        weather_desc = get_weather_description(weather_code)
        weather_emoji = get_weather_emoji(weather_code)
        wind_dir = get_wind_direction(wind_direction)

        detailed_message = (
            f"{weather_emoji} <b>Подробная погода в Москве</b>\n"
            f"══════════════════════\n"
            f"🌡 <b>Температура:</b> {temp:.1f}°C\n"
            f"💧 <b>Влажность:</b> ~{humidity}%\n"
            f"💨 <b>Ветер:</b> {wind_speed:.1f} м/с {wind_dir}\n"
            f"📌 <b>Состояние:</b> {weather_desc}\n"
            f"══════════════════════\n"
            f"<i>Приблизительные данные</i>"
        )

        return detailed_message

    except Exception as e:
        print(f"Simple detailed error: {e}")
        return "⚠️ Ошибка обработки данных."

@dp.message(Command('forecast'))
async def weather_forecast(message: Message):
    """Прогноз погоды на 3 дня"""
    try:
        forecast_url = f"https://api.open-meteo.com/v1/forecast?latitude={MOSCOW_LAT}&longitude={MOSCOW_LON}&daily=temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum,windspeed_10m_max&timezone=auto&forecast_days=3"

        async with aiohttp.ClientSession() as session:
            async with session.get(forecast_url) as response:
                if response.status == 200:
                    data = await response.json()
                    forecast_info = parse_forecast(data)
                    await message.answer(forecast_info, parse_mode='HTML')
                else:
                    await message.answer("❌ Не удалось получить прогноз.")
    except Exception as e:
        print(f"Ошибка: {e}")
        await message.answer("⚠️ Ошибка при получении прогноза.")


def parse_current_weather(data):
    """Парсинг текущей погоды из Open-Meteo"""
    try:
        current = data['current_weather']
        temp = current['temperature']
        wind_speed = current['windspeed']
        wind_direction = current['winddirection']
        weather_code = current['weathercode']

        # Получаем описание и эмодзи
        weather_desc = get_weather_description(weather_code)
        weather_emoji = get_weather_emoji(weather_code)

        # Определяем направление ветра
        wind_dir = get_wind_direction(wind_direction)

        weather_message = (
            f"{weather_emoji} <b>Погода в Москве сейчас</b>\n"
            f"══════════════════\n"
            f"🌡 <b>Температура:</b> {temp:.1f}°C\n"
            f"💨 <b>Ветер:</b> {wind_speed:.1f} м/с {wind_dir}\n"
            f"📌 <b>Состояние:</b> {weather_desc}\n"
            f"══════════════════\n"
            f"<i>Данные обновляются каждый час</i>\n\n"
            f"<i>Используй /forecast для прогноза</i>"
        )

        return weather_message
    except Exception as e:
        print(f"Parse error: {e}")
        return "⚠️ Ошибка обработки данных погоды."


def parse_detailed_weather(data):
    """Парсинг подробной погоды"""
    try:
        current = data['current_weather']
        hourly = data['hourly']

        temp = current['temperature']
        wind_speed = current['windspeed']
        weather_code = current['weathercode']

        # Берем текущий час из hourly данных
        current_time = current['time']
        time_index = hourly['time'].index(current_time)

        humidity = hourly['relative_humidity_2m'][time_index]
        pressure = hourly['pressure_msl'][time_index]
        precipitation = hourly['precipitation'][time_index]

        weather_desc = get_weather_description(weather_code)
        weather_emoji = get_weather_emoji(weather_code)

        # Конвертируем давление в мм рт.ст.
        pressure_mmhg = round(pressure * 0.750062)

        detailed_message = (
            f"{weather_emoji} <b>Подробная погода в Москве</b>\n"
            f"══════════════════════\n"
            f"🌡 <b>Температура:</b> {temp:.1f}°C\n"
            f"💧 <b>Влажность:</b> {humidity}%\n"
            f"📊 <b>Давление:</b> {pressure_mmhg} мм рт.ст.\n"
            f"💨 <b>Скорость ветра:</b> {wind_speed:.1f} м/с\n"
            f"🌧 <b>Осадки:</b> {precipitation} мм\n"
            f"📌 <b>Состояние:</b> {weather_desc}\n"
            f"══════════════════════\n"
            f"<i>Данные на текущий час</i>"
        )

        return detailed_message
    except Exception as e:
        print(f"Detailed parse error: {e}")
        return "⚠️ Ошибка обработки подробных данных."


def parse_forecast(data):
    """Парсинг прогноза на 3 дня"""
    try:
        daily = data['daily']

        forecast_message = "📅 <b>Прогноз погоды на 3 дня</b>\n══════════════════════\n"

        for i in range(3):
            date = daily['time'][i]
            temp_max = daily['temperature_2m_max'][i]
            temp_min = daily['temperature_2m_min'][i]
            weather_code = daily['weathercode'][i]
            precipitation = daily['precipitation_sum'][i]
            wind_max = daily['windspeed_10m_max'][i]

            weather_desc = get_weather_description(weather_code)
            weather_emoji = get_weather_emoji(weather_code)

            # Форматируем дату (убираем год)
            formatted_date = date.split('-')[2] + '.' + date.split('-')[1]

            forecast_message += (
                f"\n📆 <b>{formatted_date}</b>\n"
                f"{weather_emoji} {weather_desc}\n"
                f"⬆️  <b>Макс:</b> {temp_max:.1f}°C\n"
                f"⬇️  <b>Мин:</b> {temp_min:.1f}°C\n"
                f"💨 <b>Ветер до:</b> {wind_max:.1f} м/с\n"
                f"🌧 <b>Осадки:</b> {precipitation} мм\n"
                f"────────────────\n"
            )

        forecast_message += "\n<i>Используй /weather для текущей погоды</i>"

        return forecast_message
    except Exception as e:
        print(f"Forecast parse error: {e}")
        return "⚠️ Ошибка обработки прогноза."


def get_weather_description(code):
    """Конвертация кода погоды WMO в описание на русском"""
    wmo_codes = {
        0: "Ясно",
        1: "Преимущественно ясно",
        2: "Переменная облачность",
        3: "Пасмурно",
        45: "Туман",
        48: "Изморозь",
        51: "Лекая морось",
        53: "Умеренная морось",
        55: "Сильная морось",
        56: "Ледяная морось",
        57: "Сильная ледяная морось",
        61: "Небольшой дождь",
        63: "Умеренный дождь",
        65: "Сильный дождь",
        66: "Ледяной дождь",
        67: "Сильный ледяной дождь",
        71: "Небольшой снег",
        73: "Умеренный снег",
        75: "Сильный снег",
        77: "Снежные зерна",
        80: "Небольшие ливни",
        81: "Умеренные ливни",
        82: "Сильные ливни",
        85: "Небольшой снегопад",
        86: "Сильный снегопад",
        95: "Гроза",
        96: "Гроза с небольшим градом",
        99: "Гроза с сильным градом"
    }
    return wmo_codes.get(code, "Неизвестно")


def get_weather_emoji(code):
    """Возвращает emoji в зависимости от кода погоды"""
    if code == 0:
        return "☀️"
    elif code in [1, 2]:
        return "🌤️"
    elif code == 3:
        return "☁️"
    elif code in [45, 48]:
        return "🌫️"
    elif code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
        return "🌧️"
    elif code in [71, 73, 75, 77, 85, 86]:
        return "❄️"
    elif code in [95, 96, 99]:
        return "⛈️"
    else:
        return "🌤️"


def get_wind_direction(degrees):
    """Определение направления ветра по градусам"""
    directions = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ", "С"]
    index = round(degrees / 45) % 8
    return directions[index]


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())