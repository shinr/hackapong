"""Usage: pongbot.py teamname host port """

import json
import logging
import socket
import sys
import webbrowser


'''def slope(x1, x2, y1, y2):
    return (y2-y1)/(x2-x1)'''
   
#used to calculate y position where ball hits   
def futurePosition(x1, x2, y1, y2, left=True):
    slope = (y2-y1)/(x2-x1)
    #x2 = 5
    if left:
        #slope = (y2 -y1)/(5 - x1)
        slope = slope*(5-x1)
        return slope -(y1)
        
    #x2 = 635
    else:
        slope = slope*(635-x1)
        return slope -(y1)
        

class JsonOverTcp(object):
    """Send and receive newline delimited JSON messages over TCP."""
    def __init__(self, host, port):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((host, int(port)))

    def send(self, data):
        self._socket.sendall(json.dumps(data) + '\n')

    def receive(self):
        data = ''
        while '\n' not in data:
            data += self._socket.recv(1)
        return json.loads(data)


class PingPongBot(object):
    missile_ready = False
    bot_side = None
    bot_name = None
    def __init__(self, connection, log):
        self._connection = connection
        self._log = log

    def run(self, teamname, duel=None):
        self.bot_name = teamname
        if duel:
            self._connection.send({'msgType': 'requestDuel', 'data': [teamname, duel]})
        else:
            self._connection.send({'msgType': 'join', 'data': teamname})
        self._response_loop()

    def _response_loop(self):
        response_handlers = {
                'joined': self._game_joined,
                'gameStarted': self._game_started,
                'gameIsOn': self._make_move,
                'gameIsOver': self._game_over,
                'missileReady': self._missile_ready,
                }
        while True:
            response = self._connection.receive()
            msg_type, data = response['msgType'], response['data']
            try:
                response_handlers[msg_type](data)
            except KeyError:
                self._log.error('Unkown response: %s' % msg_type)

    def _game_joined(self, data):
        self._log.info('Game visualization url: %s' % data)
        webbrowser.open_new_tab(data)

    def _game_started(self, data):
        self._log.info('Game started: %s vs. %s' % (data[0], data[1]))
        if data[0] == self.bot_name:
            self.bot_side = "left"
        else:
            self.bot_side = "right"
        print self.bot_side

    def _make_move(self, data):
        if data['left']['y'] < data['ball']['pos']['y']:
            print data
            self._connection.send({'msgType': 'changeDir', 'data': 1.0})
        elif data['left']['y'] > data['ball']['pos']['y']:
            self._connection.send({'msgType': 'changeDir', 'data': -1.0})

    def _game_over(self, data):
        self._log.info('Game ended. Winner: %s' % data)

    def _missile_ready(self):
        self.missile_ready = True


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                        level=logging.INFO)
    log = logging.getLogger(__name__)
    try:
        teamname, hostname, port = sys.argv[1:4]
        duel = sys.argv[-1]
        if not duel == "9090":
            PingPongBot(JsonOverTcp(hostname, port), log).run(teamname, duel)
        else:
            PingPongBot(JsonOverTcp(hostname, port), log).run(teamname)

    except TypeError:
        sys.exit(__doc__)
