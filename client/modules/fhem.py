# -*- coding: utf-8-*-

import re
import urllib2
import json
import dateutil.parser as dparser

WORDS = ["musik","licht","wecker","heizung","zug"]
PRIORITY = 10

def isValid(intent):
        return intent in WORDS

def handle(outcome, mic, profile):
    def send_request(url):
        print url
        request = urllib2.Request(url)
        response = urllib2.urlopen(request)
        return response.read()

    def get_json_obj(fhemobject, param):
        url = 'http://localhost:8083/fhem/?cmd=jsonlist2+'+fhemobject+'&XHR=1'
        obj = json.loads(send_request(url))
        if 'Results' in obj:
            if param:
                return obj['Results'][0]['Readings'][param]
            else:
                return obj['Results'][0]['Readings']

    def get_sonos_room(room):
        if 'Wohnzimmer' == room:
            sonos_room = 'Sonos_Wohnzimmer'
        elif 'kueche' == room:
            sonos_room = 'Sonos_Kueche'
        elif 'bad' == room:
            sonos_room = 'Sonos_Bad'
        elif 'badezimmer' == room:
            sonos_room = 'Sonos_Bad'
        elif 'schlafzimmer' == room:
            sonos_room = 'Sonos_Schlafzimmer'
        else:
            sonos = eval(get_json_obj('Sonos', 'MasterPlayerPlaying')['Value'])
            if len(sonos) > 0:
                sonos_room = sonos[0]
            else:
                sonos_room = 'Sonos_Wohnzimmer'
        return sonos_room

    def get_heating_room(room):
        if 'Wohnzimmer' == room:
            heating_room = 'wz_heizung_Clima'
        elif 'Kueche' == room:
            heating_room = 'HM_36B8EC_Clima'
        elif 'Bad' == room:
            heating_room = 'HM_36BB9C_Clima'
        elif 'Badezimmer' == room:
            heating_room = 'HM_36BB9C_Clima'
        else:
            heating_room = ''

        return heating_room

    def handle_sonos(entities):
        if 'room' in entities:
            room = get_sonos_room(entities['room'][0]['value'])
        else:
            room = 'Sonos_Wohnzimmer'

        if 'control' in entities:
            action = entities['control'][0]['value']

            if action in ['play']:
                send_request('http://localhost:8083/fhem/?cmd.'+room+'=set%20'+room+'%20Play')
                return 'Gern'
            if action in ['stop','halt']:
                send_request('http://localhost:8083/fhem/?cmd.'+room+'=set%20'+room+'%20Pause')
                return 'Gern'
            elif action == 'next':
                send_request('http://localhost:8083/fhem/?cmd.'+room+'=set%20'+room+'%20Next')
                return 'Gern'
            elif action == 'previous':
                send_request('http://localhost:8083/fhem/?cmd.'+room+'=set%20'+room+'%20Previous')
                return 'Gern'

            return 'Das Kommando kann ich nicht ausführen'

    def handle_lights(entities):
        if 'on_off' in entities:
            action = entities['on_off'][0]['value']
            if action in ['on','ein']:
                send_request('http://localhost:8083/fhem/?cmd.wz_licht=set%20wz_licht%20on')
                return ''
            elif action in ['off','aus']:
                send_request('http://localhost:8083/fhem/?cmd.wz_licht=set%20wz_licht%20off')
                return ''

            return 'Das Kommando kann ich nicht ausführen'

    def handle_alarm(entities):
        if 'time' in entities:
            time2 = entities['time'][0]['value']
            datetime = dparser.parse(time2,fuzzy=True)
            time = str(datetime.hour)+':'+str(datetime.minute)
            cmd = 'set Sonos_Schlafzimmer Alarm Update 1 { StartTime => \'' + time + ':00\'}'
            send_request('http://localhost:8083/fhem/?XHR=1&amp;cmd.Sonos_Schlafzimmer=' + urllib2.quote(cmd))
            return 'Setze den Alarm auf ' + time
                    
        return 'Das Kommando kann ich nicht ausführen'

    def handle_heating(entities):
        if 'room' in entities:
            room = get_heating_room(entities['room'][0]['value'])

            if 'on_off' in entities:
                action = entities['on_off'][0]['value']
                if action in ['on','ein','an']:
                    send_request('http://localhost:8083/fhem/?cmd.'+room+'=set%20'+room+'%20desired-temp%2021.0')
                    return 'Gern'
                elif action in ['off','aus','ab']:
                    send_request('http://localhost:8083/fhem/?cmd.'+room+'=set%20'+room+'%20desired-temp%20off')
                    return 'Gern'

        return 'Das Kommando kann ich nicht ausführen'

    def handle_train(entities):
        dbinfo = get_json_obj('db_han_bs', None);

        text = u'Der nächste Zug fährt um ' + dbinfo['plan_departure_1']['Value']
        if dbinfo['plan_departure_delay_1']['Value'] == '+0':
            text += u' und ist pünktlich. '
        elif dbinfo['plan_departure_delay_1']['Value'].startswith('ca.'):
            text += u' mit einer Verspätung von ' + re.findall(r'\d+', dbinfo['plan_departure_delay_1']['Value'])[0] + ' Minuten. ';
        elif dbinfo['plan_departure_delay_1']['Value'] == u'fällt aus':
            text += u' aber fällt aus. '
        else:
            text += '. '

        text += u'Der Zug danach fährt um ' + dbinfo['plan_departure_2']['Value']
        if dbinfo['plan_departure_delay_2']['Value'] == '+0':
            text += u' und ist pünktlich. '
        elif dbinfo['plan_departure_delay_2']['Value'].startswith('ca.'):
            text += u' mit einer Verspätung von ' + re.findall(r'\d+', dbinfo['plan_departure_delay_2']['Value'])[0] + ' Minuten. ';
        elif dbinfo['plan_departure_delay_2']['Value'] == u'fällt aus':
            text += u' aber fällt aus. '
        else:
            text += '. '

        return text.encode('utf-8', 'ignore')

    intent = outcome['intent']
    entities = outcome['entities']

    if intent == 'musik':
        response = handle_sonos(entities)
    elif intent == 'licht':
        response = handle_lights(entities)
    elif intent == 'wecker':
        response = handle_alarm(entities)
    elif intent == 'heizung':
        response = handle_heating(entities)
    elif intent == 'zug':
        response = handle_train(entities)
    else:
        response = 'Huch'

    if response:
        mic.say(response)
