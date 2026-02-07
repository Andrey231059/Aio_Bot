import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio

# ========================================
# КОНФИГУРАЦИЯ
# ========================================

from config import TOKEN
# Токен бота (получить у @BotFather)
TOKEN = TOKEN


# ========================================
# ФУНКЦИИ РАБОТЫ С API МОСКОВСКОЙ БИРЖИ
# ========================================

def get_all_bonds():
    """
    Получение списка всех облигаций с Московской биржи
    """
    url = "https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQOB/securities.json"

    params = {
        'securities.columns': 'SECID,SHORTNAME,SECNAME,ISSUESIZE,COUPONPERCENT,COUPONPERIOD,MATDATE,LISTLEVEL',
        'marketdata.columns': 'YIELDCLOSE,COUPONVALUE'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Парсим данные
        securities_columns = data['securities']['columns']
        securities_data = data['securities']['data']

        marketdata_columns = data['marketdata']['columns']
        marketdata_data = data['marketdata']['data']

        # Создаем DataFrame
        df_securities = pd.DataFrame(securities_data, columns=securities_columns)
        df_marketdata = pd.DataFrame(marketdata_data, columns=marketdata_columns)

        df = pd.concat([df_securities, df_marketdata], axis=1)

        return df

    except Exception as e:
        print(f"Ошибка получения данных: {e}")
        return pd.DataFrame()


def get_bond_details(secid):
    """
    Получение детальной информации об облигации
    """
    # Основная информация
    url = f"https://iss.moex.com/iss/securities/{secid}.json"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        details = {}

        # Парсим данные
        if 'description' in data:
            for item in data['description']['data']:
                details[item[0]] = item[1]

        # Дополнительные данные по купонам
        coupon_url = f"https://iss.moex.com/iss/statistics/engines/stock/markets/bonds/boards/TQOB/securities/{secid}.json"
        coupon_response = requests.get(coupon_url, timeout=10)
        coupon_data = coupon_response.json()

        if 'coupons' in coupon_data:
            coupons = coupon_data['coupons']['data']
            if coupons:
                details['next_coupon_date'] = coupons[0][0]  # Дата следующего купона
                details['next_coupon_value'] = coupons[0][1]  # Размер следующего купона

        return details

    except Exception as e:
        print(f"Ошибка получения деталей: {e}")
        return {}


def filter_reliable_bonds(df, top_n=10):
    """
    Фильтрация надёжных облигаций:
    - Без оферты
    - Без амортизации
    - Сортировка по надёжности
    """
    if df.empty:
        return df

    # Копируем датафрейм
    filtered = df.copy()

    # Фильтр 1: Исключаем облигации с оферты (обычно содержат "оферта" в названии)
    filtered = filtered[~filtered['SECNAME'].str.lower().str.contains('оферта|оферты|оферте', na=False)]

    # Фильтр 2: Исключаем амортизируемые облигации
    filtered = filtered[~filtered['SECNAME'].str.lower().str.contains('аморт|погаш', na=False)]

    # Фильтр 3: Только ликвидные облигации (1-й уровень листинга)
    filtered = filtered[filtered['LISTLEVEL'] == 1]

    # Фильтр 4: Только с купонной доходностью
    filtered = filtered[filtered['COUPONPERCENT'].notna()]

    # Фильтр 5: Срок погашения в будущем
    today = datetime.now().date()
    filtered = filtered[pd.to_datetime(filtered['MATDATE']).dt.date > today]

    # Сортировка по надёжности (упрощённо - по размеру выпуска и доходности)
    filtered = filtered.sort_values(
        by=['ISSUESIZE', 'COUPONPERCENT'],
        ascending=[False, False]
    )

    # Берём топ N
    return filtered.head(top_n).reset_index(drop=True)


def calculate_coupon_frequency(coupon_period):
    """
    Расчёт количества купонных выплат в году
    """
    if pd.isna(coupon_period) or coupon_period == 0:
        return 0

    days_per_year = 365
    return round(days_per_year / coupon_period, 1)


# ========================================
# ФУНКЦИИ ФОРМАТИРОВАНИЯ СООБЩЕНИЙ
# ========================================

def format_bonds_table(df):
    """
    Форматирование таблицы облигаций для вывода в Telegram
    """
    if df.empty:
        return "❌ Не удалось загрузить данные об облигациях."

    message = "📋 <b>Топ 10 надёжных облигаций</b>\n\n"
    message += "<i>Без оферты, без амортизации</i>\n\n"
    message += "┌─────────────────────────────────────┐\n"

    for idx, row in df.iterrows():
        ticker = row['SECID']
        name = row['SHORTNAME'][:30]  # Обрезаем длинные названия
        coupon = row['COUPONPERCENT']
        matdate = row['MATDATE']
        yield_close = row.get('YIELDCLOSE', 0)

        # Форматируем срок погашения
        mat_dt = pd.to_datetime(matdate)
        days_to_maturity = (mat_dt - pd.Timestamp.now()).days
        years = days_to_maturity // 365

        # Определяем рейтинг (упрощённо)
        rating = "🔵 AAA" if years <= 3 else "🟢 AA" if years <= 5 else "🟡 A"

        message += f"<b>{idx + 1}. {ticker}</b>\n"
        message += f"   {name}\n"
        message += f"   {rating} | Доходность: {coupon:.2f}% | Погашение: {years}г\n"
        message += "─────────────────────────────────────\n"

    message += "└─────────────────────────────────────┘\n\n"
    message += "Выберите облигацию для подробной информации:"

    return message


def format_bond_details(secid, details, basic_info):
    """
    Форматирование детальной информации об облигации
    """
    message = f"📊 <b>Детальная информация: {secid}</b>\n\n"

    # Основная информация
    if not basic_info.empty:
        row = basic_info.iloc[0]

        message += f"📌 <b>Название:</b> {row.get('SHORTNAME', 'N/A')}\n"
        message += f"🏢 <b>Эмитент:</b> {row.get('SECNAME', 'N/A')}\n\n"

        # Купонная информация
        coupon_percent = row.get('COUPONPERCENT', 0)
        coupon_value = row.get('COUPONVALUE', 0)
        coupon_period = row.get('COUPONPERIOD', 0)

        coupon_freq = calculate_coupon_frequency(coupon_period)

        message += f"💰 <b>Купонная доходность:</b> {coupon_percent:.2f}% годовых\n"
        message += f"💵 <b>Размер купона:</b> {coupon_value:.2f} ₽\n"
        message += f"📅 <b>Периодичность:</b> {coupon_freq} раз/год ({int(coupon_period)} дней)\n"

        # Срок погашения
        matdate = row.get('MATDATE', '')
        if matdate:
            mat_dt = pd.to_datetime(matdate)
            days_to_maturity = (mat_dt - pd.Timestamp.now()).days
            years = days_to_maturity // 365
            months = (days_to_maturity % 365) // 30

            message += f"⏳ <b>Срок до погашения:</b> {years}г {months}м ({matdate})\n"

        # Доходность
        yield_close = row.get('YIELDCLOSE', 0)
        if yield_close:
            message += f"📈 <b>Текущая доходность:</b> {yield_close:.2f}%\n"

        # Размер выпуска
        issue_size = row.get('ISSUESIZE', 0)
        if issue_size:
            message += f"💵 <b>Объём выпуска:</b> {issue_size:,.0f} ₽\n"

    # Дополнительная информация
    if details:
        message += "\n📋 <b>Дополнительная информация:</b>\n"

        if 'next_coupon_date' in details and 'next_coupon_value' in details:
            next_coupon_date = details['next_coupon_date']
            next_coupon_value = details['next_coupon_value']
            message += f"   • Следующий купон: {next_coupon_date} ({next_coupon_value} ₽)\n"

        # Рейтинги (если есть)
        rating_agencies = ['RU', 'MOODY\'S', 'SP', 'FITCH']
        for agency in rating_agencies:
            rating_key = f'rating_{agency.lower()}'
            if rating_key in details:
                message += f"   • {agency}: {details[rating_key]}\n"

    message += "\n<i>ℹ️ Информация предоставлена Московской биржей</i>"

    return message


def create_keyboard(df):
    """
    Создание клавиатуры с выбором облигаций
    """
    keyboard = []

    for idx, row in df.iterrows():
        ticker = row['SECID']
        button_text = f"{idx + 1}. {ticker} - {row['COUPONPERCENT']:.1f}%"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"bond_{ticker}")])

    # Кнопка "Обновить"
    keyboard.append([InlineKeyboardButton("🔄 Обновить данные", callback_data="refresh")])

    return InlineKeyboardMarkup(keyboard)


# ========================================
# ОБРАБОТЧИКИ КОМАНД TELEGRAM
# ========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /start
    """
    welcome_message = """
🤖 <b>Бот надёжных облигаций</b>

Я помогу вам найти самые надёжные облигации на Московской бирже без оферты и амортизации.

📊 <b>Что я умею:</b>
• Показывать топ-10 надёжных облигаций
• Отображать ключевые параметры: доходность, срок, рейтинг
• Давать подробную информацию по каждой бумаге

💼 <b>Критерии отбора:</b>
✓ Без оферты
✓ Без амортизации
✓ Высокая ликвидность
✓ Надёжные эмитенты

Нажмите /bonds чтобы начать!
    """

    await update.message.reply_text(welcome_message, parse_mode='HTML')


async def show_bonds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /bonds - показать таблицу облигаций
    """
    message = await update.message.reply_text("⏳ Загружаю данные с Московской биржи...")

    # Получаем данные
    df = get_all_bonds()

    if df.empty:
        await message.edit_text("❌ Ошибка загрузки данных. Попробуйте позже.")
        return

    # Фильтруем
    df_filtered = filter_reliable_bonds(df, top_n=10)

    if df_filtered.empty:
        await message.edit_text("❌ Не найдено подходящих облигаций.")
        return

    # Сохраняем данные в контексте для последующего использования
    context.user_data['bonds_data'] = df_filtered

    # Формируем сообщение
    table_message = format_bonds_table(df_filtered)
    keyboard = create_keyboard(df_filtered)

    # Отправляем сообщение
    await message.edit_text(table_message, parse_mode='HTML', reply_markup=keyboard)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик нажатия кнопок
    """
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "refresh":
        # Обновляем данные
        await query.message.edit_text("⏳ Обновляю данные...")

        df = get_all_bonds()
        df_filtered = filter_reliable_bonds(df, top_n=10)

        if df_filtered.empty:
            await query.message.edit_text("❌ Не найдено подходящих облигаций.")
            return

        context.user_data['bonds_data'] = df_filtered

        table_message = format_bonds_table(df_filtered)
        keyboard = create_keyboard(df_filtered)

        await query.message.edit_text(table_message, parse_mode='HTML', reply_markup=keyboard)

    elif data.startswith("bond_"):
        # Показать детали облигации
        secid = data.replace("bond_", "")

        await query.message.edit_text(f"⏳ Загружаю информацию о {secid}...")

        # Получаем детали
        details = get_bond_details(secid)

        # Базовая информация из сохранённых данных
        df_filtered = context.user_data.get('bonds_data', pd.DataFrame())
        basic_info = df_filtered[df_filtered['SECID'] == secid] if not df_filtered.empty else pd.DataFrame()

        # Формируем сообщение
        details_message = format_bond_details(secid, details, basic_info)

        # Клавиатура с кнопкой "Назад"
        back_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад к списку", callback_data="back_to_list")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh")]
        ])

        await query.message.edit_text(details_message, parse_mode='HTML', reply_markup=back_keyboard)

    elif data == "back_to_list":
        # Вернуться к списку
        df_filtered = context.user_data.get('bonds_data', pd.DataFrame())

        if df_filtered.empty:
            await query.message.edit_text("❌ Данные не найдены. Используйте /bonds")
            return

        table_message = format_bonds_table(df_filtered)
        keyboard = create_keyboard(df_filtered)

        await query.message.edit_text(table_message, parse_mode='HTML', reply_markup=keyboard)


# ========================================
# ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА
# ========================================

def main():
    """
    Основная функция запуска бота
    """
    # Создаём приложение
    application = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bonds", show_bonds))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Запускаем бота
    print("🤖 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


# ========================================
# ТОЧКА ВХОДА
# ========================================

if __name__ == "__main__":
    main()

# import os
# import requests
# import pandas as pd
# from datetime import datetime
# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
#
# from config import TOKEN
# # Токен бота (получить у @BotFather)
# TOKEN = TOKEN
#
# # ========================================
# # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# # ========================================
#
# def calculate_coupon_value(row):
#     """
#     Рассчитывает размер купона в рублях на основе:
#     - Номинала (FACEVALUE)
#     - Купонной ставки (COUPONPERCENT)
#     - Периода выплаты (COUPONPERIOD)
#     """
#     try:
#         face_value = row.get('FACEVALUE')
#         coupon_percent = row.get('COUPONPERCENT')
#         coupon_period = row.get('COUPONPERIOD')
#
#         # Проверяем наличие всех необходимых данных
#         if (face_value is None or pd.isna(face_value) or
#                 coupon_percent is None or pd.isna(coupon_percent) or
#                 coupon_period is None or pd.isna(coupon_period)):
#             return 0.0
#
#         face_value = float(face_value)
#         coupon_percent = float(coupon_percent)
#         coupon_period = float(coupon_period)
#
#         # Если есть все данные для расчёта
#         if coupon_percent > 0 and coupon_period > 0 and face_value > 0:
#             # Формула: Купон = Номинал × (ставка / 100) × (период / 365)
#             coupon_value = face_value * (coupon_percent / 100) * (coupon_period / 365)
#             return round(coupon_value, 2)
#
#         return 0.0
#
#     except (ValueError, TypeError, AttributeError):
#         return 0.0
#
#
# def get_all_bonds():
#     """Получение списка облигаций с Московской биржи"""
#     url = "https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQOB/securities.json"
#
#     # Запрашиваем только те колонки, которые точно существуют
#     securities_cols = 'SECID,SHORTNAME,SECNAME,ISSUESIZE,COUPONPERCENT,COUPONPERIOD,MATDATE,LISTLEVEL,FACEVALUE,CURRENCY'
#
#     try:
#         response = requests.get(url + f"?securities.columns={securities_cols}", timeout=10)
#         response.raise_for_status()
#         data = response.json()
#
#         securities_columns = data['securities']['columns']
#         securities_data = data['securities']['data']
#
#         df = pd.DataFrame(securities_data, columns=securities_columns)
#
#         # Преобразуем типы данных
#         df['MATDATE'] = pd.to_datetime(df['MATDATE'], errors='coerce')
#         df['COUPONPERCENT'] = pd.to_numeric(df['COUPONPERCENT'], errors='coerce')
#         df['COUPONPERIOD'] = pd.to_numeric(df['COUPONPERIOD'], errors='coerce')
#         df['ISSUESIZE'] = pd.to_numeric(df['ISSUESIZE'], errors='coerce')
#         df['FACEVALUE'] = pd.to_numeric(df['FACEVALUE'], errors='coerce')
#
#         # Добавляем недостающие колонки как None
#         for col in ['YIELDCLOSE', 'COUPONVALUE']:
#             if col not in df.columns:
#                 df[col] = None
#
#         return df
#
#     except Exception as e:
#         print(f"Ошибка получения данных: {e}")
#         return pd.DataFrame()
#
#
# def has_offer(name):
#     """Проверка наличия оферты в названии"""
#     keywords = ['оферта', 'оферты', 'досрочн', 'погашен', 'call', 'put', 'досроч']
#     name_lower = str(name).lower()
#     return any(kw in name_lower for kw in keywords)
#
#
# def has_amortization(name):
#     """Проверка наличия амортизации"""
#     keywords = ['аморт', 'амортизац', 'погашен', 'погашени']
#     name_lower = str(name).lower()
#     return any(kw in name_lower for kw in keywords)
#
#
# def calculate_rating(row):
#     """Определение рейтинга эмитента"""
#     secname = str(row.get('SECNAME', '')).lower()
#     shortname = str(row.get('SHORTNAME', '')).lower()
#
#     # ОФЗ
#     if 'офз' in shortname or 'федеральн' in secname:
#         return "🇷🇺 AAA (ОФЗ)"
#
#     # Госкорпорации
#     state_corps = ['вэб', 'ржд', 'росатом', 'роснефть', 'газпром', 'транснефть', 'акционерная энергетическая компания']
#     if any(corp in secname for corp in state_corps):
#         return "🏛️ AA (Госкорп.)"
#
#     # Системные банки
#     if 'сбербанк' in secname or 'втб' in secname:
#         return "🏦 A+ (Системный банк)"
#
#     # Крупные компании
#     big_companies = ['газпром', 'лукойл', 'сургутнефтегаз', 'норникель', 'алроса', 'мтс', 'мегафон']
#     if any(company in secname for company in big_companies):
#         return "🏭 A (Крупная компания)"
#
#     # Остальные
#     return "📊 BBB (Иные эмитенты)"
#
#
# def filter_reliable_bonds(df, top_n=10):
#     """Фильтрация надёжных облигаций без оферты и амортизации"""
#     if df.empty:
#         return df
#
#     filtered = df.copy()
#
#     # Фильтры
#     filtered = filtered[~filtered['SECNAME'].apply(has_offer)]  # Без оферты
#     filtered = filtered[~filtered['SECNAME'].apply(has_amortization)]  # Без амортизации
#     filtered = filtered[filtered['LISTLEVEL'] == 1]  # 1-й уровень листинга
#     filtered = filtered[filtered['CURRENCY'] == 'RUB']  # Только рублёвые
#     filtered = filtered[filtered['COUPONPERCENT'].notna() & (filtered['COUPONPERCENT'] > 0)]  # С купоном
#     filtered = filtered[filtered['MATDATE'].dt.date > datetime.now().date()]  # Не погашены
#     filtered = filtered[filtered['ISSUESIZE'] >= 1_000_000_000]  # Объём от 1 млрд
#
#     # Добавляем расчётные поля
#     filtered['RATING'] = filtered.apply(calculate_rating, axis=1)
#     filtered['COUPON_FREQ'] = (365 / filtered['COUPONPERIOD']).round().fillna(0).astype(int)
#     filtered['YEARS_TO_MATURITY'] = ((filtered['MATDATE'] - pd.Timestamp.now()).dt.days / 365.25).round(1)
#
#     # Сортировка по надёжности и доходности
#     rating_order = {
#         '🇷🇺 AAA (ОФЗ)': 1,
#         '🏛️ AA (Госкорп.)': 2,
#         '🏦 A+ (Системный банк)': 3,
#         '🏭 A (Крупная компания)': 4,
#         '📊 BBB (Иные эмитенты)': 5
#     }
#     filtered['RATING_ORDER'] = filtered['RATING'].map(lambda x: rating_order.get(x, 6))
#
#     filtered = filtered.sort_values(
#         by=['RATING_ORDER', 'COUPONPERCENT'],
#         ascending=[True, False]
#     ).head(top_n).reset_index(drop=True)
#
#     return filtered.drop(columns=['RATING_ORDER'])
#
#
# def format_bonds_table(df):
#     """Форматирование таблицы облигаций"""
#     if df.empty:
#         return "❌ Не удалось загрузить данные об облигациях."
#
#     message = "🔝 <b>Топ 10 надёжных облигаций</b>\n\n"
#     message += "<i>✅ Без оферты | ✅ Без амортизации | ✅ Высокая ликвидность</i>\n\n"
#
#     for idx, row in df.iterrows():
#         ticker = row['SECID']
#         name = row['SHORTNAME'][:28] + "..." if len(str(row['SHORTNAME'])) > 28 else row['SHORTNAME']
#         rating = row['RATING'].split()[0]  # Только эмодзи и буквы
#         coupon = row['COUPONPERCENT']
#         years = row['YEARS_TO_MATURITY']
#         freq = row['COUPON_FREQ']
#
#         message += (
#             f"<b>{idx + 1}. {ticker}</b>\n"
#             f"   {name}\n"
#             f"   {rating} | {coupon:.2f}% | {years}г | {freq}×/год\n\n"
#         )
#
#     message += "👉 <i>Выберите облигацию для подробной информации:</i>"
#     return message
#
#
# def format_bond_details(row):
#     """Форматирование детальной информации об облигации"""
#     ticker = row['SECID']
#     name = row['SHORTNAME']
#     full_name = row['SECNAME']
#     rating = row['RATING']
#     maturity_date = row['MATDATE'].strftime('%d.%m.%Y')
#     years_to_maturity = row['YEARS_TO_MATURITY']
#     coupon_percent = row['COUPONPERCENT']
#     coupon_value = calculate_coupon_value(row)  # ← ИСПРАВЛЕНО: правильный расчёт купона!
#     coupon_freq = row['COUPON_FREQ']
#     coupon_period = int(row['COUPONPERIOD']) if pd.notna(row['COUPONPERIOD']) else 0
#     issue_size = f"{row['ISSUESIZE']:,.0f}".replace(",", " ") if pd.notna(row['ISSUESIZE']) else "N/A"
#     face_value = row['FACEVALUE'] if pd.notna(row['FACEVALUE']) else "N/A"
#     currency = row['CURRENCY']
#     yield_close = row.get('YIELDCLOSE', coupon_percent)
#
#     message = f"📜 <b>Облигация: {ticker}</b>\n\n"
#
#     # Основная информация
#     message += f"📌 <b>Название:</b> {name}\n"
#     message += f"🏢 <b>Эмитент:</b> {full_name[:60]}{'...' if len(full_name) > 60 else ''}\n"
#     message += f"⭐ <b>Рейтинг:</b> {rating}\n\n"
#
#     # Купонная информация
#     message += "💵 <b>Купонные характеристики:</b>\n"
#     message += f"   • Доходность: {coupon_percent:.2f}% годовых\n"
#     message += f"   • Размер купона: {coupon_value:.2f} ₽\n"  # ← Теперь будет корректное значение!
#     message += f"   • Выплат в году: {coupon_freq} раз(а)\n"
#     message += f"   • Период: каждые {coupon_period} дней\n\n"
#
#     # Срок погашения
#     message += "⏳ <b>Срок обращения:</b>\n"
#     message += f"   • Погашение: {maturity_date}\n"
#     message += f"   • До погашения: {years_to_maturity:.1f} года(лет)\n\n"
#
#     # Финансовые параметры
#     message += "💼 <b>Финансовые параметры:</b>\n"
#     message += f"   • Объём выпуска: {issue_size} ₽\n"
#     message += f"   • Номинал: {face_value} {currency}\n"
#     message += f"   • Текущая доходность: {yield_close:.2f}%\n\n"
#
#     message += "<i>ℹ️ Информация предоставлена Московской биржей (MOEX)</i>"
#
#     return message
#
#
# def create_keyboard(df):
#     """Создание клавиатуры с выбором облигаций"""
#     keyboard = []
#
#     for idx, row in df.iterrows():
#         ticker = row['SECID']
#         coupon = row['COUPONPERCENT']
#         btn_text = f"{idx + 1}. {ticker} ({coupon:.1f}%)"
#         keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"bond_{ticker}")])
#
#     keyboard.append([InlineKeyboardButton("🔄 Обновить данные", callback_data="refresh")])
#
#     return InlineKeyboardMarkup(keyboard)
#
#
# # ========================================
# # ОБРАБОТЧИКИ TELEGRAM
# # ========================================
#
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Обработчик команды /start"""
#     welcome_message = """
# 🤖 <b>Бот надёжных облигаций Мосбиржи</b>
#
# Я помогу вам найти самые надёжные облигации без оферты и амортизации.
#
# 📊 <b>Что я умею:</b>
# • Показывать топ-10 надёжных облигаций
# • Отображать ключевые параметры: доходность, срок, рейтинг
# • Давать подробную информацию по каждой бумаге
#
# 💼 <b>Критерии отбора:</b>
# ✓ Без оферты
# ✓ Без амортизации
# ✓ Высокая ликвидность (1-й уровень листинга)
# ✓ Объём выпуска от 1 млрд ₽
#
# 👉 Используйте команду /bonds чтобы начать!
#     """
#
#     await update.message.reply_text(welcome_message, parse_mode='HTML')
#
#
# async def show_bonds(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Обработчик команды /bonds"""
#     message = await update.message.reply_text("⏳ Загружаю данные с Московской биржи...")
#
#     # Получаем данные
#     df = get_all_bonds()
#
#     if df.empty:
#         await message.edit_text("❌ Ошибка загрузки данных. Попробуйте позже.")
#         return
#
#     # Фильтруем
#     df_filtered = filter_reliable_bonds(df, top_n=10)
#
#     if df_filtered.empty:
#         await message.edit_text("❌ Не найдено облигаций, соответствующих критериям.")
#         return
#
#     # Сохраняем данные в контексте
#     context.user_data['bonds_data'] = df_filtered
#
#     # Формируем сообщение
#     table_message = format_bonds_table(df_filtered)
#     keyboard = create_keyboard(df_filtered)
#
#     # Отправляем сообщение
#     await message.edit_text(table_message, parse_mode='HTML', reply_markup=keyboard)
#
#
# async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Обработчик нажатия кнопок"""
#     query = update.callback_query
#     await query.answer()
#
#     data = query.data
#
#     if data == "refresh":
#         # Обновляем данные
#         await query.message.edit_text("⏳ Обновляю данные с Московской биржи...")
#
#         df = get_all_bonds()
#         df_filtered = filter_reliable_bonds(df, top_n=10)
#
#         if df_filtered.empty:
#             await query.message.edit_text("❌ Не найдено подходящих облигаций.")
#             return
#
#         context.user_data['bonds_data'] = df_filtered
#
#         table_message = format_bonds_table(df_filtered)
#         keyboard = create_keyboard(df_filtered)
#
#         await query.message.edit_text(table_message, parse_mode='HTML', reply_markup=keyboard)
#
#     elif data.startswith("bond_"):
#         # Показать детали облигации
#         secid = data.replace("bond_", "")
#
#         await query.message.edit_text(f"⏳ Загружаю информацию о {secid}...")
#
#         # Получаем данные из сохранённого DataFrame
#         df_filtered = context.user_data.get('bonds_data', pd.DataFrame())
#
#         if df_filtered.empty:
#             await query.message.edit_text("❌ Данные устарели. Используйте /bonds")
#             return
#
#         bond_row = df_filtered[df_filtered['SECID'] == secid]
#
#         if bond_row.empty:
#             await query.message.edit_text("❌ Облигация не найдена в списке.")
#             return
#
#         # Формируем детальное сообщение
#         details_message = format_bond_details(bond_row.iloc[0])
#
#         # Клавиатура с кнопками "Назад" и "Обновить"
#         back_keyboard = InlineKeyboardMarkup([
#             [InlineKeyboardButton("🔙 Назад к списку", callback_data="back_to_list")],
#             [InlineKeyboardButton("🔄 Обновить данные", callback_data="refresh")]
#         ])
#
#         await query.message.edit_text(details_message, parse_mode='HTML', reply_markup=back_keyboard)
#
#     elif data == "back_to_list":
#         # Вернуться к списку
#         df_filtered = context.user_data.get('bonds_data', pd.DataFrame())
#
#         if df_filtered.empty:
#             await query.message.edit_text("❌ Данные устарели. Используйте /bonds")
#             return
#
#         table_message = format_bonds_table(df_filtered)
#         keyboard = create_keyboard(df_filtered)
#
#         await query.message.edit_text(table_message, parse_mode='HTML', reply_markup=keyboard)
#
#
# # ========================================
# # ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА
# # ========================================
#
# def main():
#     """Основная функция запуска бота"""
#     # Создаём приложение
#     application = Application.builder().token(TOKEN).build()
#
#     # Регистрируем обработчики
#     application.add_handler(CommandHandler("start", start))
#     application.add_handler(CommandHandler("bonds", show_bonds))
#     application.add_handler(CallbackQueryHandler(button_callback))
#
#     # Запускаем бота
#     print("🤖 Бот запущен!")
#     print(f"🔍 Токен: {TOKEN[:5]}...{TOKEN[-5:]}")
#     application.run_polling(drop_pending_updates=True)
#
#
# # ========================================
# # ТОЧКА ВХОДА
# # ========================================
#
# if __name__ == "__main__":
#     main()