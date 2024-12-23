from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from app import WeatherService
from units import generate_1_day_plot, generate_3_day_plot, generate_5_day_plot
import asyncio
import os
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

class WeatherForm(StatesGroup):
    start_city = State()
    destination_city = State()
    stopovers_city = State()

api_token = ''
# @BlackProject_weather_bot мой бот
weather_api_key = ''

weather_bot = Bot(token=api_token)
dispatcher = Dispatcher()

user_sessions = {}
temperature_data = {}

weather_service_instance = WeatherService(api_key=weather_api_key)

async def report_error(chat_id, bot_instance, error_message):
    await bot_instance.send_message(chat_id, f'Ошибка: {error_message}')

@dispatcher.message(F.text == '/start')
async def initiate_chat(message: types.Message):
    await message.answer(
        'Здравствуйте! Я бот для прогноза погоды. С помощью меня вы можете узнать погоду в вашем городе и в других местах, включая промежуточные остановки. Выберите /weather или отправьте команду /help для помощи.'
    )

@dispatcher.message(F.text == '/help')
async def show_help(message: types.Message):
    await message.answer('Команда /start - начальное сообщение и информация о боте\n'
                         'Команда /weather - узнать погоду в интересующих вас городах')

@dispatcher.message(F.text == '/weather')
async def request_start_city(message: types.Message, state: FSMContext):
    try:
        user_sessions[message.from_user.id] = []
        await state.set_state(WeatherForm.start_city)
        await message.answer('Введите город отправления:')
    except Exception as e:
        await report_error(message.chat.id, weather_bot, e)

@dispatcher.message((F.text | F.location), WeatherForm.start_city)
async def request_destination_city(message: types.Message, state: FSMContext):
    try:
        user_sessions[message.from_user.id].append(message.text.strip())
        await message.answer('Введите город назначения:')
        await state.set_state(WeatherForm.destination_city)
    except Exception as e:
        await report_error(message.chat.id, weather_bot, e)

@dispatcher.message((F.text | F.location), WeatherForm.destination_city)
async def inquire_stopovers(message: types.Message, state: FSMContext):
    try:
        user_sessions[message.from_user.id].append(message.text.strip())
        yes_button = InlineKeyboardButton(text='Да', callback_data='yes')
        no_button = InlineKeyboardButton(text='Нет', callback_data='no')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[yes_button, no_button]])
        await state.clear()
        await message.answer('Планируете ли вы промежуточные остановки?', reply_markup=keyboard)
    except Exception as e:
        await report_error(message.chat.id, weather_bot, e)

@dispatcher.callback_query(F.data == 'yes')
async def handle_stopovers_yes(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await state.set_state(WeatherForm.stopovers_city)
        await callback.message.answer('Введите город для промежуточной остановки:')
    except Exception as e:
        await report_error(callback.message.chat.id, weather_bot, e)

@dispatcher.message(F.text, WeatherForm.stopovers_city)
async def inquire_more_stopovers(message: types.Message, state: FSMContext):
    try:
        user_sessions[message.from_user.id].append(message.text.strip())
        yes_button = InlineKeyboardButton(text='Да', callback_data='yes')
        no_button = InlineKeyboardButton(text='Нет', callback_data='no')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[yes_button, no_button]])
        await message.answer('Есть ли еще города, которые вас интересуют?', reply_markup=keyboard)
    except Exception as e:
        await report_error(message.chat.id, weather_bot, e)

@dispatcher.callback_query(F.data == 'no')
async def provide_weather_info(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        one_day_button = InlineKeyboardButton(text='1 день', callback_data='1_day')
        three_days_button = InlineKeyboardButton(text='3 дня', callback_data='3_day')
        five_days_button = InlineKeyboardButton(text='5 дней', callback_data='5_day')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[one_day_button, three_days_button, five_days_button]])
        await callback.message.answer('Выберите период для прогноза погоды:', reply_markup=keyboard)
        await state.clear()
    except Exception as e:
        await report_error(callback.message.chat.id, weather_bot, e)

@dispatcher.callback_query(F.data == '1_day')
async def weather_forecast_one_day(callback: types.CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        forecast_report = ''
        weather_instance = weather_service_instance
        temperature_data[user_id] = {}
        for city in user_sessions.get(user_id, []):
            city_code = weather_instance.get_city_code(city)
            weather_info = weather_instance.fetch_weather(city_code, '1day')
            weather_analysis = weather_instance.assess_weather(weather_info['temp'], weather_info['humidity'],
                                                       weather_info['wind_speed'], weather_info['precipitation_probability'])
            summary = weather_analysis if isinstance(weather_analysis, str) else '. '.join(weather_analysis[:-1])
            rating = weather_analysis if isinstance(weather_analysis, str) else weather_analysis[-1]
            temperature_data[user_id][city] = weather_info['temp']
            forecast_report += (f'Прогноз погоды для {city} на {weather_info["date"]}:\n'
                                f'Температура: {weather_info["temp"]}°C\n'
                                f'Влажность: {weather_info["humidity"]}%\n'
                                f'Скорость ветра: {weather_info["wind_speed"]} км/ч\n'
                                f'Вероятность дождя: {weather_info["precipitation_probability"]}%\n'
                                f'Анализ: {summary}\n'
                                f'Уровень: {rating}\n\n')
        await callback.message.answer(forecast_report)
        user_sessions[user_id] = []
        graph_yes_button = InlineKeyboardButton(text='Да', callback_data='yes_graph_1_day')
        graph_no_button = InlineKeyboardButton(text='Нет', callback_data='no_graph')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[graph_yes_button, graph_no_button]])
        await callback.message.answer('Хочется увидеть график температуры?', reply_markup=keyboard)
    except Exception as e:
        await report_error(callback.message.chat.id, weather_bot, e)

@dispatcher.callback_query(F.data == '3_day')
async def weather_forecast_three_days(callback: types.CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        forecast_report = ''
        weather_instance = weather_service_instance
        temperature_data[user_id] = {}
        for city in user_sessions.get(user_id, []):
            city_code = weather_instance.get_city_code(city)
            weather_info = weather_instance.fetch_weather(city_code, '3day')
            temperature_data[user_id][city] = []
            for day in weather_info:
                weather_analysis = weather_instance.assess_weather(day['temp'], day['humidity'],
                                                        day['wind_speed'], day['precipitation_probability'])
                summary = weather_analysis if isinstance(weather_analysis, str) else '. '.join(weather_analysis[:-1])
                rating = weather_analysis if isinstance(weather_analysis, str) else weather_analysis[-1]
                temperature_data[user_id][city].append((day['date'], day['temp']))
                forecast_report += (f'Прогноз погоды для {city} на {day["date"]}:\n'
                                    f'Температура: {day["temp"]}°C\n'
                                    f'Влажность: {day["humidity"]}%\n'
                                    f'Скорость ветра: {day["wind_speed"]} км/ч\n'
                                    f'Вероятность дождя: {day["precipitation_probability"]}%\n'
                                    f'Анализ: {summary}\n'
                                    f'Уровень: {rating}\n\n')
        await callback.message.answer(forecast_report)
        user_sessions[user_id] = []
        graph_yes_button = InlineKeyboardButton(text='Да', callback_data='graph_3')
        graph_no_button = InlineKeyboardButton(text='Нет', callback_data='no_graph')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[graph_yes_button, graph_no_button]])
        await callback.message.answer('Хочется увидеть график температуры?', reply_markup=keyboard)
    except Exception as e:
        await report_error(callback.message.chat.id, weather_bot, e)

@dispatcher.callback_query(F.data == '5_day')
async def weather_forecast_five_days(callback: types.CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        forecast_report = ''
        weather_instance = weather_service_instance
        temperature_data[user_id] = {}
        for city in user_sessions.get(user_id, []):
            city_code = weather_instance.get_city_code(city)
            weather_info = weather_instance.fetch_weather(city_code, '5day')
            temperature_data[user_id][city] = []
            for day in weather_info:
                weather_analysis = weather_instance.assess_weather(day['temp'], day['humidity'],
                                                            day['wind_speed'], day['precipitation_probability'])
                summary = weather_analysis if isinstance(weather_analysis, str) else '. '.join(weather_analysis[:-1])
                rating = weather_analysis if isinstance(weather_analysis, str) else weather_analysis[-1]
                temperature_data[user_id][city].append((day['date'], day['temp']))
                forecast_report += (f'Прогноз погоды для {city} на {day["date"]}:\n'
                                    f'Температура: {day["temp"]}°C\n'
                                    f'Влажность: {day["humidity"]}%\n'
                                    f'Скорость ветра: {day["wind_speed"]} км/ч\n'
                                    f'Вероятность дождя: {day["precipitation_probability"]}%\n'
                                    f'Анализ: {summary}\n'
                                    f'Уровень: {rating}\n\n')
        await callback.message.answer(forecast_report)
        user_sessions[user_id] = []
        graph_yes_button = InlineKeyboardButton(text='Да', callback_data='graph_5')
        graph_no_button = InlineKeyboardButton(text='Нет', callback_data='no_graph')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[graph_yes_button, graph_no_button]])
        await callback.message.answer('Хочется увидеть график температуры?', reply_markup=keyboard)
    except Exception as e:
        await report_error(callback.message.chat.id, weather_bot, e)

@dispatcher.callback_query(F.data == 'no_graph')
async def farewell_user(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        user_sessions[user_id] = []
        temperature_data[user_id] = {}
        await callback.answer()
        await callback.message.answer('Хороших вам поездок! Если захотите узнать погоду снова, пишите /weather')
    except Exception as e:
        await report_error(callback.message.chat.id, weather_bot, e)

@dispatcher.callback_query(F.data == 'graph_3')
async def generate_temperature_plot_3_days(callback: types.CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        temp_info = temperature_data.get(user_id, {})
        if not temp_info:
            raise Exception("Недостаточно данных для генерации графика.")
        plot_file = generate_3_day_plot(temp_info)
        image_file = FSInputFile(path=plot_file)
        await weather_bot.send_photo(chat_id=callback.message.chat.id, photo=image_file)
        os.remove(plot_file)
    except Exception as e:
        await report_error(callback.message.chat.id, weather_bot, e)

@dispatcher.callback_query(F.data == 'graph_5')
async def generate_temperature_plot_5_days(callback: types.CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        temp_info = temperature_data.get(user_id, {})
        if not temp_info:
            raise Exception("Недостаточно данных для генерации графика.")
        plot_file = generate_5_day_plot(temp_info)
        image_file = FSInputFile(path=plot_file)
        await weather_bot.send_photo(chat_id=callback.message.chat.id, photo=image_file)
        os.remove(plot_file)
    except Exception as e:
        await report_error(callback.message.chat.id, weather_bot, e)

@dispatcher.callback_query(F.data == 'yes_graph_1_day')
async def generate_temperature_plot_1_day(callback: types.CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        temp_info = temperature_data.get(user_id, {})
        if not temp_info:
            raise Exception("Недостаточно данных для генерации графика.")
        plot_file = generate_1_day_plot(list(temp_info.values()), list(temp_info.keys()))
        image_file = FSInputFile(path=plot_file)
        await weather_bot.send_photo(chat_id=callback.message.chat.id, photo=image_file)
        os.remove(plot_file)
    except Exception as e:
        await report_error(callback.message.chat.id, weather_bot, e)

@dispatcher.message()
async def handle_unrecognized_input(message: types.Message):
    await message.answer('Я не понимаю эту команду. Попробуйте /help для получения списка команд.')

if __name__ == '__main__':
    async def run_bot():
        await dispatcher.start_polling(weather_bot)

    asyncio.run(run_bot())