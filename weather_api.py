import requests
import json

class WeatherAPI:
    def __init__(self, config_file="config.json"):
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.city = self.config.get("city", "Москва")
    
    def get_weather(self, city=None):
        if city:
            self.city = city
        
        try:
            # Бесплатное API погоды (без ключа)
            url = f"https://wttr.in/{self.city}?format=%C+%t+%w&lang=ru"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                text = response.text.strip()
                # Парсим ответ
                parts = text.split()
                if len(parts) >= 2:
                    condition = " ".join(parts[:-1])
                    temp = parts[-1]
                    return f"В {self.city} сейчас {condition}, температура {temp}"
            
            return f"Не удалось узнать погоду в {self.city}"
        except Exception as e:
            return f"Ошибка получения погоды: {e}"
    
    def set_city(self, city):
        self.city = city
        self.config["city"] = city
        with open("config.json", 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
        return f"Город изменен на {city}"