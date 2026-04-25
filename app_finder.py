import os
import subprocess
import json

class AppFinder:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.load_config()
        self.app_cache = self.config.get("known_paths", {})
    
    def load_config(self):
        with open(self.config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
    
    def save_config(self):
        self.config["known_paths"] = self.app_cache
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
    
    def find_app(self, app_name):
        app_name = app_name.lower().strip()
        
        # Проверка кэша
        if app_name in self.app_cache:
            path = self.app_cache[app_name]
            if os.path.exists(path):
                return path
        
        # Поиск через where
        try:
            result = subprocess.run(f"where {app_name}.exe", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0]
                self.app_cache[app_name] = path
                self.save_config()
                return path
        except:
            pass
        
        # Поиск в директориях
        search_dirs = self.config.get("search_dirs", [])
        for search_dir in search_dirs:
            if "%USERNAME%" in search_dir:
                search_dir = search_dir.replace("%USERNAME%", os.getlogin())
            
            if os.path.exists(search_dir):
                try:
                    for root, dirs, files in os.walk(search_dir):
                        depth = root.count(os.sep) - search_dir.count(os.sep)
                        if depth > 3:
                            continue
                        
                        for file in files:
                            if file.lower().endswith('.exe') and app_name in file.lower():
                                path = os.path.join(root, file)
                                self.app_cache[app_name] = path
                                self.save_config()
                                return path
                except:
                    pass
        
        return None
    
    def get_all_found(self):
        return self.app_cache