from flask import Flask, request, render_template
import plotly.graph_objs as go
from dash import Dash, dcc, html, Input, Output
import pandas as pd
import requests


class WeatherService:
    API_URL_CITY_SEARCH = 'http://dataservice.accuweather.com/locations/v1/cities/search'
    API_URL_WEATHER_1DAY = 'http://dataservice.accuweather.com/forecasts/v1/daily/1day/'
    API_URL_WEATHER_5DAY = 'http://dataservice.accuweather.com/forecasts/v1/daily/5day/'

    def __init__(self, api_key):
        self.api_key = api_key

    def get_coordinates(self, city):
        try:
            params = {'apikey': self.api_key, 'q': city}
            response = requests.get(self.API_URL_CITY_SEARCH, params=params)
            response.raise_for_status()
            return (response.json()[0]['GeoPosition']['Latitude'], response.json()[0]['GeoPosition']['Longitude'])
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка при получении координат: {e}")

    def get_city_code(self, city):
        try:
            params = {'apikey': self.api_key, 'q': city}
            response = requests.get(self.API_URL_CITY_SEARCH, params=params)
            response.raise_for_status()
            return response.json()[0]['Key']
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка при получении кода города: {e}")

    def fetch_weather(self, city_code, forecast_days):
        try:
            if forecast_days == '1day':
                return self._get_daily_weather(city_code)
            elif forecast_days in ['3day', '5day']:
                return self._get_weekly_weather(city_code, forecast_days)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка при получении погоды: {e}")

    def _get_daily_weather(self, city_code):
        params = {'apikey': self.api_key, 'details': 'true', 'metric': 'true'}
        response = requests.get(self.API_URL_WEATHER_1DAY + city_code, params=params)
        response.raise_for_status()
        weather_data = response.json()['DailyForecasts'][0]
        return {
            'date': weather_data['Date'][:10],
            'temp': weather_data['RealFeelTemperatureShade']['Minimum']['Value'],
            'humidity': weather_data['Day']['RelativeHumidity']['Average'],
            'wind_speed': weather_data['Day']['Wind']['Speed']['Value'],
            'precipitation_probability': weather_data['Day']['PrecipitationProbability']
        }

    def _get_weekly_weather(self, city_code, forecast_days):
        params = {'apikey': self.api_key, 'details': 'true', 'metric': 'true'}
        response = requests.get(self.API_URL_WEATHER_5DAY + city_code, params=params)
        response.raise_for_status()
        weather_list = []
        days_count = 5 if forecast_days == '5day' else 3

        for day in range(days_count):
            weather_data = response.json()['DailyForecasts'][day]
            weather_list.append({
                'date': weather_data['Date'][:10],
                'temp': weather_data['RealFeelTemperatureShade']['Minimum']['Value'],
                'humidity': weather_data['Day']['RelativeHumidity']['Average'],
                'wind_speed': weather_data['Day']['Wind']['Speed']['Value'],
                'precipitation_probability': weather_data['Day']['PrecipitationProbability']
            })
        return weather_list

    def assess_weather(self, temperature, humidity, wind_speed, rain_probability):
        assessment = [
            ("на улицу лучше не выходить, там слишком холодно", temperature <= -40),
            ("там реальный шторм, если весишь мало, то вероятнее всего летать будешь", wind_speed >= 75),
            ("идеальная погода, надо на улицу", 11 <= wind_speed < 30 and 15 < temperature < 25 and rain_probability < 30),
            ("выходи жарить яичницу, только сам не зажарься", temperature > 40 and rain_probability < 30),
            ("жарко, но может пойдет дождь и будет кайф", temperature > 40 and 30 <= rain_probability <= 75),
            ("убирай яичницу, сейчас лить будет", temperature > 40 and rain_probability > 75),
            ("холодновато, оденься потеплее и возьми зонт на всякий", 0 <= temperature <= 15 and wind_speed <= 20 and rain_probability > 50),
            ("холодновато, возьми еще кофту, зонт оставь дома", 0 <= temperature <= 15 and wind_speed <= 20),
            ("фу, холодно и ветрено, я бы дома ботал лучше", 0 <= temperature <= 15 and wind_speed > 20),
            ("лети на улицу, я бы остался дома", temperature < 0 and rain_probability > 70),
            ("ветер холодно, в общем, оставайся дома", temperature < 0 and wind_speed >= 40),
            ("так-то пойдет, но холодно", temperature < 0),
            ("кайфовый дождик", 15 < temperature <= 40 and rain_probability > 55 and wind_speed <= 20),
            ("ветренный не кайфовый дождик", 15 < temperature <= 40 and rain_probability > 55),
            ("кайфовый ветер", 15 < temperature <= 40 and rain_probability <= 55 and wind_speed <= 20),
            ("не кайфовый ветер", 15 < temperature <= 40 and wind_speed > 20),
            ("кхм, не уверен, что могу дать точные рекомендации на счет этой погоды", True)
        ]

        for message, condition in assessment:
            if condition:
                return message

app = Flask(__name__)
city_weather_data = {}
forecast_days = ''
dash_app = Dash(__name__, server=app, url_base_pathname='/plot/')
dash_app_map = Dash(__name__, server=app, url_base_pathname='/map/')

API_KEY = 'zP8A8KknWGrIWOi50VCiVqox3jZP23BQ'
weather_service = WeatherService(api_key=API_KEY)

dash_app.layout = html.Div([
    dcc.Dropdown(id='weather_metric',
                 options=[{'label': 'Температура', 'value': 'temp'},
                          {'label': 'Скорость ветра', 'value': 'wind_speed'},
                          {'label': 'Влажность', 'value': 'humidity'},
                          {'label': 'Вероятность осадков', 'value': 'precipitation_probability'}],
                 value='temp'),
    dcc.Graph(id='weather_graph')
])

dash_app_map.layout = html.Div([
    dcc.Graph(id='temperature_map')
])

@dash_app.callback(Output('weather_graph', 'figure'), Input('weather_metric', 'value'))
def update_graph(selected_metric):
    figure = go.Figure()
    metric_translation = {
        'temp': 'Температура',
        'wind_speed': 'Скорость ветра',
        'humidity': 'Влажность',
        'precipitation_probability': 'Вероятность осадков'
    }
    global city_weather_data, forecast_days

    for city, weather_info in city_weather_data.items():
        if forecast_days == '1day':
            figure.add_trace(go.Bar(
                x=[city],
                y=[weather_info[0][selected_metric]],
                name=f'{metric_translation[selected_metric]} в {city}'
            ))
        else:
            figure.add_trace(go.Scatter(
                x=[info['date'] for info in weather_info],
                y=[info[selected_metric] for info in weather_info],
                mode='lines+markers',
                name=f'{metric_translation[selected_metric]} в {city}'
            ))

    figure.update_layout(title="Визуализация погоды для городов",
                          xaxis_title='Дата' if forecast_days != '1day' else 'Город',
                          yaxis_title='Значение',
                          showlegend=True,
                          template='plotly_white')

    return figure

@dash_app_map.callback(Output('temperature_map', 'figure'), Input('temperature_map', 'id'))
def create_map(map_id):
    global city_weather_data, weather_service
    latitudes, longitudes, city_names, temperatures = [], [], [], []

    for city, weather_info in city_weather_data.items():
        city_names.append(city)
        temperatures.append(f'Температура в {city}: {weather_info[0]["temp"]}')
        coord = weather_service.get_coordinates(city)
        latitudes.append(coord[0])
        longitudes.append(coord[1])

    df = pd.DataFrame({'Город': city_names, 'lat': latitudes, 'lon': longitudes, 'Температура': temperatures})

    figure = go.Figure()
    figure.add_trace(go.Scattermapbox(
        lat=df['lat'],
        lon=df['lon'],
        hovertext=df['Температура'],
        marker=go.scattermapbox.Marker(size=10, color='red'),
        mode='lines+markers'
    ))
    figure.update_layout(
        mapbox=dict(
            style='open-street-map',
            zoom=3,
            center={'lat': 55.752, 'lon': 37.619}
        ),
        height=500,
    )
    return figure

@app.route('/', methods=['GET', 'POST'])
def city_weather_view():
    global city_weather_data, forecast_days
    city_weather_data = {}
    forecast_days = ''

    if request.method == 'GET':
        return render_template('form.html')
    else:
        first_city = request.form['first']
        second_city = request.form['second']
        additional_cities = request.form
        forecast_days = request.form['day']
        city_weather_data[first_city] = []
        city_weather_data[second_city] = []

        for key in additional_cities:
            if key.startswith('city'):
                city_weather_data[additional_cities[key]] = []

        try:
            for city in city_weather_data:
                city_code = weather_service.get_city_code(city)

                if forecast_days == '1day':
                    weather_info = weather_service.fetch_weather(city_code, forecast_days)
                    analysis = weather_service.assess_weather(weather_info['temp'], weather_info['humidity'],
                                                              weather_info['wind_speed'], weather_info['precipitation_probability'])
                    weather_info['weather'] = '. '.join(analysis[:-1])
                    weather_info['level'] = analysis[-1]
                    city_weather_data[city].append(weather_info)

                else:
                    weather_info = weather_service.fetch_weather(city_code, forecast_days)
                    for day_info in weather_info:
                        analysis = weather_service.assess_weather(day_info['temp'], day_info['humidity'],
                                                                  day_info['wind_speed'], day_info['precipitation_probability'])
                        day_info['weather'] = '. '.join(analysis[:-1])
                        day_info['level'] = analysis[-1]
                        city_weather_data[city].append(day_info)
            return render_template('result.html', city_weather=city_weather_data)

        except Exception as error:
            return render_template('error.html', error=str(error))


if __name__ == '__main__':
    app.run(debug=True)