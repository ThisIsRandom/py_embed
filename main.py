import grovepi
import grove_rgb_lcd
import time
import math
import datetime as dt
 
pins = {
    "dhtPin": 3,
    "soundPin": 1,
    "buttonPin": 4,
    "potPin": 0
}
 
cfgs = [
    "test1",
    "test2",
    "test3"
]
 
class State:
    currentSecond = None
    currentMinute = None
    currentHour = None
    isDay = None
    cfg = None
 
class Ticker:
    def __init__(self, pubSub, state):
        self.pubSub = pubSub
        self.state = state
 
    def tick(self):
        currentHour = dt.datetime.today().hour
        currentMinute = dt.datetime.today().minute
        currentSecond = dt.datetime.today().second
 
        if currentHour != self.state.currentHour:
            self.pubSub.publish("hourChange", currentHour)
 
        if currentMinute != self.state.currentMinute:
            self.pubSub.publish("minuteChange", currentMinute)
 
        if currentSecond != self.state.currentSecond:
            self.pubSub.publish("secondChange", currentSecond)        
 
 
class PubSub:
    subscribers = {}
 
    def subscribe(self, event, fn):
        if event not in self.subscribers.keys():
            self.subscribers[event] = []
        self.subscribers[event].append(fn)
 
    def publish(self, event, data = None):
        if event not in self.subscribers.keys():
            return
 
        for fn in self.subscribers[event]:
            if data is None:
                fn()
            else:
                fn(data)
 
    def clear(self):
        tmp = []
        if "stateChange" in self.subscribers.keys():
            tmp = self.subscribers["stateChange"]
 
        self.subscribers = {
            "stateChange": tmp
        }
 
 
class ConfigState:
    selectedConfig = 0
    pinMax = 1024
 
    def __init__(self, ticker, pubSub, state):
        self.cfgs = cfgs
        self.ticker = ticker
        self.pubSub = pubSub
        self.state = state
 
        self.pubSub.clear()
        self.setup()
 
    def onSecondChange(self, _):
        print("test")
 
        reading = grovepi.analogRead(pins["potPin"]) / len(self.cfgs) / 100
 
        if reading > len(self.cfgs):
            reading = reading - 1
 
        self.pubSub.publish("config", math.floor(reading))
 
    def onConfigChange(self, index):
        print(index)
        self.state.cfg = self.cfgs[index]
        grove_rgb_lcd.setText_norefresh(self.state.cfg)
 
    def setup(self):
        self.pubSub.subscribe("secondChange", self.onSecondChange)
        self.pubSub.subscribe("config", self.onConfigChange)
        self.pubSub.subscribe("secondChange", self.readButton)
        self.pubSub.subscribe("buttonClicked", self.onButtonClick)
 
    def readButton(self, _):
        grovepi.pinMode(pins["buttonPin"], "INPUT")
        if grovepi.digitalRead(pins["buttonPin"]):
            self.pubSub.publish("buttonClicked")
 
    def onButtonClick(self):
        print("ch st")
        self.pubSub.publish("stateChange", 0)    
 
    def run(self):
        print("dadada")
        self.ticker.tick()
        time.sleep(1)
 
class StateSelector:
    def __init__(self, state, pubSub):
        self.selected = state
 
    def changeActiveState(self, newState):
        self.selected = newState
 
class LoadedState:
    def __init__(self, ticker, pubSub, state):
        self.ticker = ticker
        self.pubSub = pubSub
        self.state = state
 
        self.pubSub.clear()
        self.setup()
 
    def onHourChange(self, v):
        self.state.currentHour = v
 
    def onMinuteChange(self, v):
        self.state.currentMinute = v
 
    def onSecondChange(self, v):
        self.state.currentSecond = v
 
    def onDayOrNight(self, v):
        if v < 8 or v > 16:
            self.state.isDay = False
            grove_rgb_lcd.setRGB(255, 0, 0)
        else:
            self.state.isDay = True
            grove_rgb_lcd.setRGB(0, 255, 0)
 
    def readTempAndHumidity(self, currentMinute):
        if currentMinute % 15 != 0 or currentMinute is None:
            return
 
        [temp, hum] = grovepi.dht(pins["dhtPin"], 1)
 
    def writeScreen(self, _):
        [temp, hum] = grovepi.dht(pins["dhtPin"], 1)
        grove_rgb_lcd.setText_norefresh("Hum " + str(hum) + "temp " + str(temp))
 
    def readSound(self, _):
        s = grovepi.analogRead(pins["soundPin"])
        if s < 500:
            return
 
        if self.state.isDay:
            print("daytime")
        else:
            print("night")
 
    def readButton(self, _):
        grovepi.pinMode(pins["buttonPin"], "INPUT")
        if grovepi.digitalRead(pins["buttonPin"]):
            self.pubSub.publish("buttonClicked")
 
    def onButtonClick(self):
        self.pubSub.publish("stateChange", 1)    
 
    def setup(self):
        self.pubSub.subscribe("hourChange", self.onHourChange)
        self.pubSub.subscribe("hourChange", self.onDayOrNight)
        self.pubSub.subscribe("minuteChange", self.onMinuteChange)
        self.pubSub.subscribe("minuteChange", self.readTempAndHumidity)
        self.pubSub.subscribe("secondChange", self.onSecondChange)
        self.pubSub.subscribe("secondChange", self.readSound)
        self.pubSub.subscribe("secondChange", self.readButton)
        self.pubSub.subscribe("secondChange", self.writeScreen)
        self.pubSub.subscribe("buttonClicked", self.onButtonClick)
 
 
    def run(self):
        print("loaded")
        self.ticker.tick()
        time.sleep(1)
 
state = State()
pubSub = PubSub()
ticker = Ticker(pubSub, state)
 
stateSelector = StateSelector(ConfigState(ticker, pubSub, state), pubSub)
 
def onInit():
    while True:
        stateSelector.selected.run()
 
def onStateChange(v):
    print(v)
    if v == 0:
        stateSelector.changeActiveState(LoadedState(ticker, pubSub, state))
    else:
        stateSelector.changeActiveState(ConfigState(ticker, pubSub, state))
 
 
pubSub.subscribe("init", onInit)
pubSub.subscribe("stateChange", onStateChange)
 
pubSub.publish("init")
 