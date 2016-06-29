#!/usr/bin/env python

import urllib #Библиотека для рабобты с урлами
import json #Библиотека для работы с форматом json
import os #Библиотека для работы с файловой системой

from flask import Flask #Класс фреймворка Flask для создания инстанса сервера
from flask import request #Объект чтобы делать запросы
from flask import make_response #объект чтобы отдавать ответы

# Flask app should start in global layout
#Создаем объект приложения
app = Flask(__name__)


#Создаем ф-ю которая будет вызываться когда кто-то обращается по адрессу /webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    #Смотрим что мы получили от api.ai
    req = request.get_json(silent=True, force=True)
    #выводим это
    print("Request:")
    print(json.dumps(req, indent=4))
    #Вызываем ф-ю по обработке запроса
    res = processRequest(req)
    #конвертируем в json
    res = json.dumps(res, indent=4)
    #Генерируем ответ
    r = make_response(res)
    #говорим что это json
    r.headers['Content-Type'] = 'application/json'
    #и отправляем обратно api.ai
    return r


def processRequest(req):
    #если он не хочет погоды - то возвращаем пустой ответ
    if req.get("result").get("action") != "yahooWeatherForecast":
        return {}
    #Обращаемся к API Yahoo
    baseurl = "https://query.yahooapis.com/v1/public/yql?"
    #Строим запрос
    yql_query = makeYqlQuery(req)
    #Если запрос пустой - возвращаем пустой ответ
    if yql_query is None:
        return {}
    #Генерируем итоговый URL
    yql_url = baseurl + urllib.urlencode({'q': yql_query}) + "&format=json"
    print(yql_url)

    #Делаем GET запрос по этому URL и читаем ответ
    result = urllib.urlopen(yql_url).read()
    print("yql result: ")
    print(result)

    #Конвертируем из JSON в словарь
    data = json.loads(result)
    
    #Генерируем ответ webhook'a
    res = makeWebhookResult(data)
    return res


def makeYqlQuery(req):
    result = req.get("result")
    parameters = result.get("parameters")
    city = parameters.get("geo-city")
    if city is None:
        return None

    return "select * from weather.forecast where woeid in (select woeid from geo.places(1) where text='" + city + "')"


def makeWebhookResult(data):
    query = data.get('query')
    if query is None:
        return {}

    result = query.get('results')
    if result is None:
        return {}

    channel = result.get('channel')
    if channel is None:
        return {}

    item = channel.get('item')
    location = channel.get('location')
    units = channel.get('units')
    if (location is None) or (item is None) or (units is None):
        return {}

    condition = item.get('condition')
    if condition is None:
        return {}

    # print(json.dumps(item, indent=4))

    speech = "Today in " + location.get('city') + ": " + condition.get('text') + \
             ", the temperature is " + condition.get('temp') + " " + units.get('temperature')

    print("Response:")
    print(speech)

    slack_message = {
        "text": speech,
        "attachments": [
            {
                "title": channel.get('title'),
                "title_link": channel.get('link'),
                "color": "#36a64f",

                "fields": [
                    {
                        "title": "Condition",
                        "value": "Temp " + condition.get('temp') +
                                 " " + units.get('temperature'),
                        "short": "false"
                    },
                    {
                        "title": "Wind",
                        "value": "Speed: " + channel.get('wind').get('speed') +
                                 ", direction: " + channel.get('wind').get('direction'),
                        "short": "true"
                    },
                    {
                        "title": "Atmosphere",
                        "value": "Humidity " + channel.get('atmosphere').get('humidity') +
                                 " pressure " + channel.get('atmosphere').get('pressure'),
                        "short": "true"
                    }
                ],

                "thumb_url": "http://l.yimg.com/a/i/us/we/52/" + condition.get('code') + ".gif"
            }
        ]
    }

    print(json.dumps(slack_message))

    return {
        "speech": speech,
        "displayText": speech,
        "data": {"slack": slack_message},
        # "contextOut": [],
        "source": "apiai-weather-webhook-sample"
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print "Starting app on port %d" % port

    app.run(debug=False, port=port, host='0.0.0.0')
