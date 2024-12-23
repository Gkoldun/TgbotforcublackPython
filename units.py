import matplotlib.pyplot as plt
from aiogram import Bot
import pandas as pd
import requests
import uuid


def generate_1_day_plot(temperatures, cities):
    plt.figure(figsize=(10, 5))
    plt.bar(cities, temperatures, color='skyblue')
    plt.xlabel('Города')
    plt.ylabel('Температура (°C)')
    plt.title('Сравнение температур на 1 день')
    plt.xticks(rotation=45)

    file_name = f'1_day_plot_{uuid.uuid4()}.jpg'
    plt.savefig(file_name)
    plt.close()
    return file_name


def generate_3_day_plot(city_temperatures):
    weather_data = []
    for city, temperatures in city_temperatures.items():
        for date, temp in temperatures[:3]:
            weather_data.append({'Город': city, 'Дата': date, 'Температура': temp})

    df = pd.DataFrame(weather_data)

    plt.figure(figsize=(10, 6))
    for city in df['Город'].unique():
        df_city = df[df['Город'] == city]
        plt.plot(df_city['Дата'], df_city['Температура'], marker='o', label=city)

    plt.title('Температура за 3 дня')
    plt.xlabel('Дата')
    plt.ylabel('Температура (°C)')
    plt.xticks(rotation=45)
    plt.grid()
    plt.legend()

    file_name = f'3_day_plot_{uuid.uuid4()}.jpg'
    plt.savefig(file_name)
    plt.close()
    return file_name


def generate_5_day_plot(city_temperatures):
    weather_data = []
    for city, temperatures in city_temperatures.items():
        for date, temp in temperatures:
            weather_data.append({'Город': city, 'Дата': date, 'Температура': temp})

    df = pd.DataFrame(weather_data)

    plt.figure(figsize=(10, 6))
    for city in df['Город'].unique():
        df_city = df[df['Город'] == city]
        plt.plot(df_city['Дата'], df_city['Температура'], marker='o', label=city)

    plt.title('Температура за 5 дней')
    plt.xlabel('День')
    plt.ylabel('Температура (°C)')
    plt.xticks(rotation=45)
    plt.grid()
    plt.legend()

    file_name = f'5_day_plot_{uuid.uuid4()}.jpg'
    plt.savefig(file_name)
    plt.close()
    return file_name


async def handle_error_message(chat_id, bot: Bot, error: Exception):
    print()
    error_message = 'Произошла ошибка'
    if isinstance(error, requests.exceptions.ConnectionError):
        error_message = "Ошибка подключения: не удалось установить связь с сервером."
    elif isinstance(error, requests.exceptions.HTTPError):
        error_message = f"Ошибка API: {error.response.status_code}"
    elif isinstance(error, ValueError):
        error_message = "Некорректные данные, попробуйте снова позже."
    elif isinstance(error, PermissionError):
        error_message = "Ошибка доступа: доступ к API запрещен."
    else:
        error_message = f"Неизвестная ошибка, повторите попытку позже. Подробности: {str(error)}"
    await bot.send_message(chat_id, error_message)