import os
import subprocess
import webbrowser
import pyautogui
import psutil
from datetime import datetime
from app_finder import AppFinder
from weather_api import WeatherAPI

class CommandManager:
    def __init__(self, voice_engine):
        self.voice = voice_engine
        self.app_finder = AppFinder()
        self.weather = WeatherAPI()
        
        # Словарь с ответами на вопросы
        self.responses = {
            "как дела": ["У меня всё отлично! А у вас?", "Лучше всех! Спасибо что спросили", "Отлично, готов работать!"],
            "кто ты": ["Я Дэвикс - ваш голосовой помощник", "Я Дравикс ассистент, приятно познакомиться!", "Ваш персональный помощник на ПК"],
            "как тебя зовут": ["Меня зовут Дэвикс", "Я Дэвикс, ваш помощник", "Дэвикс! Рад служить"],
            "что ты умеешь": ["Я умею открывать программы, искать в интернете, показывать погоду, делать скриншоты и многое другое!", 
                              "Могу открыть любую программу, найти информацию в Google, рассказать погоду и управлять вашим ПК"],
            "спасибо": ["Пожалуйста! Всегда рад помочь", "Обращайтесь!", "Без проблем"],
            "привет": ["Здравствуйте!", "Привет! Чем могу помочь?", "Добрый день!"]
        }
    
    def get_answer(self, question):
        """Поиск ответа на вопрос из словаря"""
        question = question.lower()
        for key, answers in self.responses.items():
            if key in question:
                import random
                return random.choice(answers)
        return None
    
    def search_google(self, query):
        """Поиск в Google и возврат результата"""
        webbrowser.open(f"https://www.google.com/search?q={query}")
        return f"Ищу в Google: {query}"
    
    def get_weather(self, city=None):
        """Получение погоды"""
        return self.weather.get_weather(city)
    
    def get_system_info(self):
        """Информация о системе"""
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('C:')
        return f"Процессор загружен на {cpu}%, оперативной памяти использовано {memory.percent}%, на диске C свободно {disk.free // (1024**3)} гигабайт"
    
    def take_screenshot(self):
        """Скриншот"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        pyautogui.screenshot(filename)
        return f"Скриншот сохранен в файл {filename}"
    
    def open_app(self, app_name):
        """Открытие приложения с поиском"""
        path = self.app_finder.find_app(app_name)
        if path:
            subprocess.Popen(path)
            return f"Открываю {app_name}"
        else:
            # Поиск в Google если не найдено
            webbrowser.open(f"https://www.google.com/search?q={app_name}")
            return f"Не нашел программу {app_name}, но нашел в Google"
    
    def open_website(self, site_name):
        """Открытие сайта"""
        sites = {
            "ютуб": "https://youtube.com",
            "youtube": "https://youtube.com",
            "гугл": "https://google.com",
            "google": "https://google.com",
            "яндекс": "https://yandex.ru",
            "вк": "https://vk.com",
            "телеграм": "https://web.telegram.org",
            "дискорд": "https://discord.com",
            "гитхаб": "https://github.com"
        }
        
        for name, url in sites.items():
            if name in site_name.lower():
                webbrowser.open(url)
                return f"Открываю {name}"
        
        webbrowser.open(f"https://www.google.com/search?q={site_name}")
        return f"Ищу {site_name} в Google"
    
    def control_volume(self, command):
        """Громкость"""
        if "громче" in command:
            pyautogui.press('volumeup')
            return "Увеличил громкость"
        elif "тише" in command:
            pyautogui.press('volumedown')
            return "Уменьшил громкость"
        elif "мут" in command:
            pyautogui.press('volumemute')
            return "Выключил звук"
        return None
    
    def execute_system_command(self, command):
        """Системные команды"""
        system = self.voice.config.get("system_commands", {})
        for name, cmd in system.items():
            if name.lower() in command.lower():
                os.system(cmd)
                return f"Выполняю: {name}"
        return None
    
    def process(self, command):
        """Основная обработка команды"""
        if not command:
            return None
        
        # Вопросы из словаря
        answer = self.get_answer(command)
        if answer:
            return answer
        
        # Погода
        if "погода" in command:
            city = None
            if "в " in command and len(command.split("в ")) > 1:
                city = command.split("в ")[-1].strip()
            return self.get_weather(city)
        
        # Открытие приложений
        if "открой" in command:
            app = command.replace("открой", "").replace("запусти", "").strip()
            return self.open_app(app)
        
        # Поиск в Google
        if "найди" in command or "загугли" in command:
            query = command.replace("найди", "").replace("загугли", "").strip()
            return self.search_google(query)
        
        # Открытие сайта
        if "открой сайт" in command:
            site = command.replace("открой сайт", "").strip()
            return self.open_website(site)
        
        # Скриншот
        if "скриншот" in command or "снимок" in command:
            return self.take_screenshot()
        
        # Информация о системе
        if "состояние" in command or "информация" in command or "характеристики" in command:
            return self.get_system_info()
        
        # Громкость
        if any(x in command for x in ["громче", "тише", "мут"]):
            result = self.control_volume(command)
            if result:
                return result
        
        # Системные команды
        result = self.execute_system_command(command)
        if result:
            return result
        
        # Запуск браузера по умолчанию
        if "браузер" in command:
            webbrowser.open("https://google.com")
            return "Открываю браузер"
        
        # Если ничего не подошло - поиск в Google
        return self.search_google(command)