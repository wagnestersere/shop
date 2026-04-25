import speech_recognition as sr
import pyttsx3
import json
import random

class VoiceEngine:
    def __init__(self, config_file="config.json"):
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.awake = False
        self.is_listening = True
        self.assistant_name = self.config.get("assistant_name", "Дэвикс")
        self.greetings = self.config.get("greetings", ["Слушаю!"])
        self.init_voice()
    
    def init_voice(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', self.config.get('voice_speed', 170))
            self.engine.setProperty('volume', self.config.get('voice_volume', 0.9))
            
            # Настройка голоса (русский)
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'russian' in voice.name.lower() or 'microsoft' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
        except:
            self.engine = None
        
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
        except:
            self.recognizer = None
            self.microphone = None
    
    def speak(self, text):
        """Голосовой ответ с эмоциями"""
        if not self.config.get('voice_enabled', True):
            print(f"[💬] {text}")
            return
        
        if self.engine:
            print(f"[🗣️] {text}")
            self.engine.say(text)
            self.engine.runAndWait()
        else:
            print(f"[💬] {text}")
    
    def greet(self):
        """Приветствие при пробуждении"""
        greeting = random.choice(self.greetings)
        self.speak(greeting)
        return greeting
    
    def respond(self, text):
        """Ответ с подтверждением"""
        responses = [
            f"Хорошо, {text}",
            f"Понял, {text}",
            f"Сделано, {text}",
            f"Выполняю, {text}"
        ]
        response = random.choice(responses)
        self.speak(response)
        return response
    
    def listen(self):
        """Прослушивание микрофона"""
        if not self.recognizer:
            return None
        
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                command = self.recognizer.recognize_google(audio, language="ru-RU")
                return command.lower()
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            return None
    
    def get_wake_word(self):
        return self.config.get('wake_word', 'дэвикс')
    
    def set_awake(self, state):
        self.awake = state