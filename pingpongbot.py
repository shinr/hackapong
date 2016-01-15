"""Usage: pongbot.py teamname host port """

import json
import logging
import socket
import sys
import webbrowser
import random

'''def slope(x1, x2, y1, y2):
    return (y2-y1)/(x2-x1)'''
   
#used to calculate y position where ball hits   
def futurePosition(x1, x2, y1, y2, left=True):
    slope = (y2-y1) / (x2-x1)
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

class Point(object):
    x = 0.0
    y = 0.0
    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y

    def __eq__(self, other):
        print "eq", self.x, self.y, other.x, other.y
        if self.x == other.x and self.y == other.y:
            return True
        return False

class PingPongBot(object):
    missile_ready = False
    bot_side = None
    bot_name = None
    ball_old_pos = None
    ball_position = None
    ball_predicted_pos = None
    x = 0
    y = 0
    nowindow = True
    slowdownmode = False
    timer = 0
    def __init__(self, connection, log):
        self._connection = connection
        self._log = log

    def run(self, teamname, duel=None, nowindow=None):
        if nowindow:
            self.nowindow = False
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
                'missileLaunched': self._missile_launched,
                'error': self._error
                }
        while True:
            response = self._connection.receive()
            msg_type, data = response['msgType'], response['data']
            try:
                response_handlers[msg_type](data)
            except KeyError:
                self._log.error('Unkown response: %s' % msg_type)
            except:
                print "Unexpected error:", sys.exc_info()[0]
                raise

    def _error(self, data):
        pass # whatevs

    def _game_joined(self, data):
        self._log.info('Game visualization url: %s' % data)
        if not self.nowindow:
            webbrowser.open_new_tab(data)

    def _game_started(self, data):
        self._log.info('Game started: %s vs. %s' % (data[0], data[1]))
        if data[0] == self.bot_name:
            self.bot_side = "left"
        else:
            self.bot_side = "right"

    def close_enough(self, y, target_y):
        if y < target_y + 2 and y > target_y - 2:
            return True
        return False

    def _make_move(self, data):
        self.timer += 1
        if self.timer > 100:
            print "switching modes"
            if self.slowdownmode:
                self.slowdownmode = False
                self.timer = 0
            else:
                self.slowdownmode = True
                self.timer = 0
        offset = -30 + random.randint(1, 10)
        self.y = data["left"]['y']
        self.ball_position = Point(data['ball']['pos']['x'], data['ball']['pos']['y'])
        if self.ball_old_pos and self.ball_position:
            # tulossa kohti
            if self.ball_old_pos.x - self.ball_position.x > 0:
                if self.ball_position.x - self.ball_old_pos.x != 0.0:
                    slope = (self.ball_position.y - self.ball_old_pos.y) / (self.ball_position.x - self.ball_old_pos.x)
                else:
                    slope = (self.ball_position.y - self.ball_old_pos.y) / (self.ball_position.x - self.ball_old_pos.x +.01)
                self.ball_predicted_pos = Point(0.0, ((self.ball_position.x) * slope - self.ball_position.y)*-1.0) 
                #print self.ball_predicted_pos.y,
                if self.ball_predicted_pos.y > 480:
                    self.ball_predicted_pos.y = 480 - (self.ball_predicted_pos.y - 480)
                elif self.ball_predicted_pos.y < 0:
                    self.ball_predicted_pos.y *= -1.0
                linear_interpolation = self.ball_predicted_pos.y - (self.y - offset)
                linear_interpolation /= 8.0
                lerp_speed = max(-1.0, min(linear_interpolation, 1.0))
                #print lerp_speed, 
                opponent_y = data['right']['y']
                if self.slowdownmode:
                    offset = -25
                else:
                    if slope > 0.0:
                        offset = -6
                    else:
                        offset = -44
                if abs(slope) >= 1.0:
                    print "trying to smash"
                    
                #print speed
                #print offset
                #print self.y, offset, self.ball_predicted_pos.y
                if self.y - offset < self.ball_predicted_pos.y:
                    self._connection.send({'msgType':'changeDir', 'data':1.0})
                else:
                    self._connection.send({'msgType':'changeDir', 'data':-1.0})
            else:
                if self.ball_position.x - self.ball_old_pos.x != 0.0:
                    slope = (self.ball_position.y - self.ball_old_pos.y) / (self.ball_position.x - self.ball_old_pos.x)
                else: # vitun hack :D
                    slope = (self.ball_position.y - self.ball_old_pos.y) / (self.ball_position.x - self.ball_old_pos.x +.01)
               # print '\nslope*: ', slope, '\n'
                prediction = -1.0 *(slope * (self.ball_position.x) - self.ball_position.y)
                if prediction > 480:
                    prediction = 480 - (prediction - 480)
                elif prediction < 0:
                    prediction *= -1.0
                if prediction < 240:
                    prediction *= 1.3
                else:
                    prediction *= .7
                if slope > 0.0:
                    prediction += prediction * slope
                else:
                    prediction += prediction * slope
                if abs(slope) < .25:
                    print "adjusting small angles",
                    prediction = 240
                    if slope < 0.0:
                        prediction = prediction - 220 * slope 
                    elif slope > 0.0:
                        prediction = prediction + 220 * slope
                if self.y > 320:
                    print "adjusting wall", slope
                    if slope < 0.0:
                        prediction = prediction - 240 * slope
                    else:
                        prediction = prediction + 120 * slope
                elif self.y < 160:
                    print "adjusting wall", slope
                    if slope > 0.0:
                        prediction = prediction + 240 * slope
                    else:
                        prediction = prediction - 120 * slope
                print prediction
                if prediction < self.y:
                    self._connection.send({'msgType': 'changeDir', 'data': -1.0})
                else:
                    self._connection.send({'msgType': 'changeDir', 'data': 1.0})
                """
                if slope < 0.15 and slope > -0.15:
                    if data['left']['y'] < data['ball']['pos']['y']:
                        self._connection.send({'msgType': 'changeDir', 'data': 1.0})
                    elif data['left']['y'] > data['ball']['pos']['y']:
                        self._connection.send({'msgType': 'changeDir', 'data': -1.0})
                
                elif slope < 0.3 and slope > -0.3:
                    if data['left']['y'] < 80:
                        self._connection.send({'msgType': 'changeDir', 'data': 1.0})
                        
                    elif data['left']['y'] > 400:
                        self._connection.send({'msgType': 'changeDir', 'data': -1.0})
                        
                    elif slope < 0:
                        self._connection.send({'msgType': 'changeDir', 'data': -1.0})
                        
                    else:
                        self._connection.send({'msgType': 'changeDir', 'data': 1.0})
                        
                elif slope > 0.60 or slope < -0.60:
                    if data['left']['y'] < 200:
                        self._connection.send({'msgType': 'changeDir', 'data': 1.0})
                        
                    elif data['left']['y'] > 280:
                        self._connection.send({'msgType': 'changeDir', 'data': -1.0})
                        
                    elif slope < 0:
                        self._connection.send({'msgType': 'changeDir', 'data': -1.0})
                        
                    else:
                        self._connection.send({'msgType': 'changeDir', 'data': 1.0})
                        
                else:
                    if data['left']['y'] < 150:
                        self._connection.send({'msgType': 'changeDir', 'data': 1.0})
                        
                    elif data['left']['y'] > 350:
                        self._connection.send({'msgType': 'changeDir', 'data': -1.0})
                        
                    elif slope < 0:
                        self._connection.send({'msgType': 'changeDir', 'data': -1.0})
                        
                    else:
                        self._connection.send({'msgType': 'changeDir', 'data': 1.0})
                """        
                        
                
                
        self.ball_old_pos = self.ball_position

    def _game_over(self, data):
        self._log.info('Game ended. Winner: %s' % data)

    def _missile_ready(self, data):
        print "Missile ready!"
        self.missile_ready = True
        self._connection.send({'msgType':'launchMissile'})

    def _missile_launched(self, data):
        pass

if __name__ == '__main__':
    duel = None
    nowindow = None
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                        level=logging.INFO)
    log = logging.getLogger(__name__)
    try:
        if len(sys.argv) == 4:
            teamname, hostname, port = sys.argv[1:4]
        elif len(sys.argv) == 5:
            teamname, hostname, port, duel = sys.argv[1:5]
        elif len(sys.argv) == 6:
            teamname, hostname, port, duel, nowindow = sys.argv[1:]
        
        PingPongBot(JsonOverTcp(hostname, port), log).run(teamname, duel, nowindow)

    except TypeError:
        sys.exit(__doc__)
