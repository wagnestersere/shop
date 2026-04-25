import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
from datetime import datetime
from voice_engine import VoiceEngine
from command_manager import CommandManager
from app_finder import AppFinder
import json

class DravixAssistantGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dravix Assistant - Голосовой помощник")
        self.root.geometry("900x750")
        self.root.minsize(800, 650)
        self.root.configure(bg='#1a1a2e')
        
        # Инициализация
        self.voice = VoiceEngine()
        self.command_manager = CommandManager(self.voice)
        self.app_finder = AppFinder()
        self.is_running = False
        self.listen_thread = None
        
        self.setup_ui()
    
    def setup_ui(self):
        # Верхняя панель
        top_frame = tk.Frame(self.root, bg='#16213e', height=70)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        top_frame.pack_propagate(False)
        
        # Логотип и название
        title_label = tk.Label(top_frame, text="🎤 DRAVIX ASSISTANT", 
                                font=('Arial', 20, 'bold'), bg='#16213e', fg='#e94560')
        title_label.pack(side=tk.LEFT, padx=20)
        
        subtitle_label = tk.Label(top_frame, text="Голосовой помощник", 
                                   font=('Arial', 10), bg='#16213e', fg='#888')
        subtitle_label.pack(side=tk.LEFT, padx=5)
        
        # Статус
        self.status_label = tk.Label(top_frame, text="⚪ Остановлен", 
                                     font=('Arial', 11, 'bold'), bg='#16213e', fg='#888')
        self.status_label.pack(side=tk.RIGHT, padx=20)
        
        # Текущее состояние
        state_frame = tk.Frame(self.root, bg='#1a1a2e')
        state_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.state_text = tk.StringVar(value=f"💤 Скажите '{self.voice.get_wake_word()}' чтобы начать")
        state_label = tk.Label(state_frame, textvariable=self.state_text, 
                               font=('Arial', 13), bg='#1a1a2e', fg='#ccc')
        state_label.pack()
        
        # Область логов
        log_frame = tk.Frame(self.root, bg='#1a1a2e')
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        log_header = tk.Frame(log_frame, bg='#1a1a2e')
        log_header.pack(fill=tk.X)
        
        log_label = tk.Label(log_header, text="📋 Лог диалога", 
                             font=('Arial', 12, 'bold'), bg='#1a1a2e', fg='#e94560')
        log_label.pack(side=tk.LEFT)
        
        clear_btn = tk.Button(log_header, text="🗑 Очистить", 
                              command=self.clear_log,
                              bg='#0f3460', fg='white', font=('Arial', 9),
                              padx=10, pady=2, cursor='hand2')
        clear_btn.pack(side=tk.RIGHT)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, 
                                                   bg='#0f0f1a', fg='#ccc',
                                                   font=('Consolas', 10),
                                                   insertbackground='white')
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Панель команд
        cmd_frame = tk.Frame(self.root, bg='#1a1a2e')
        cmd_frame.pack(fill=tk.X, padx=20, pady=10)
        
        cmd_label = tk.Label(cmd_frame, text="💬 Или введите команду:", 
                             font=('Arial', 10), bg='#1a1a2e', fg='#ccc')
        cmd_label.pack(anchor=tk.W)
        
        cmd_entry_frame = tk.Frame(cmd_frame, bg='#1a1a2e')
        cmd_entry_frame.pack(fill=tk.X, pady=5)
        
        self.command_entry = tk.Entry(cmd_entry_frame, font=('Arial', 11), 
                                       bg='#0f0f1a', fg='white', 
                                       insertbackground='white',
                                       relief=tk.FLAT)
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,10))
        
        send_btn = tk.Button(cmd_entry_frame, text="Отправить", 
                             command=self.send_text_command,
                             bg='#e94560', fg='white', font=('Arial', 10, 'bold'),
                             padx=20, pady=5, cursor='hand2')
        send_btn.pack(side=tk.RIGHT)
        
        # Кнопки управления
        btn_frame = tk.Frame(self.root, bg='#1a1a2e')
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.start_btn = tk.Button(btn_frame, text="▶ ЗАПУСТИТЬ", 
                                   command=self.start_assistant,
                                   bg='#0f3460', fg='white', font=('Arial', 11, 'bold'),
                                   padx=30, pady=10, cursor='hand2')
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="⏹ ОСТАНОВИТЬ", 
                                  command=self.stop_assistant, state=tk.DISABLED,
                                  bg='#e94560', fg='white', font=('Arial', 11, 'bold'),
                                  padx=30, pady=10, cursor='hand2')
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        test_btn = tk.Button(btn_frame, text="🎤 ТЕСТ МИКРОФОНА", 
                             command=self.test_microphone,
                             bg='#0f3460', fg='white', font=('Arial', 10),
                             padx=20, pady=8, cursor='hand2')
        test_btn.pack(side=tk.LEFT, padx=5)
        
        apps_btn = tk.Button(btn_frame, text="📱 ПРИЛОЖЕНИЯ", 
                             command=self.show_apps,
                             bg='#0f3460', fg='white', font=('Arial', 10),
                             padx=20, pady=8, cursor='hand2')
        apps_btn.pack(side=tk.LEFT, padx=5)
        
        # Строка подсказок
        tips_frame = tk.Frame(self.root, bg='#16213e', height=100)
        tips_frame.pack(fill=tk.X, padx=10, pady=10)
        tips_frame.pack_propagate(False)
        
        tips_text = """
💡 ПРИМЕРЫ КОМАНД:
• "открой браузер" — откроет браузер
• "найди рецепт пиццы" — поиск в Google
• "какая погода" — покажет погоду
• "сделай скриншот" — сохранит скриншот
• "как дела" — спросите как у меня дела
• "открой дискорд" — найдет и откроет Discord
• "громче/тише" — регулировка громкости
"""
        tips_label = tk.Label(tips_frame, text=tips_text, font=('Arial', 9), 
                              bg='#16213e', fg='#888', justify=tk.LEFT)
        tips_label.pack(anchor=tk.W, padx=15, pady=8)
    
    def add_log(self, text, log_type="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if log_type == "user":
            formatted = f"[{timestamp}] 👤 {text}\n"
            tag = "user"
        elif log_type == "assistant":
            formatted = f"[{timestamp}] 🤖 {text}\n"
            tag = "assistant"
        elif log_type == "error":
            formatted = f"[{timestamp}] ❌ {text}\n"
            tag = "error"
        else:
            formatted = f"[{timestamp}] ℹ️ {text}\n"
            tag = "info"
        
        self.log_text.insert(tk.END, formatted)
        self.log_text.see(tk.END)
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
        self.add_log("Лог очищен", "info")
    
    def send_text_command(self):
        command = self.command_entry.get().strip()
        if not command:
            return
        
        self.command_entry.delete(0, tk.END)
        self.add_log(command, "user")
        
        # Выполнение команды
        result = self.command_manager.process(command)
        if result:
            self.add_log(result, "assistant")
            self.voice.speak(result)
            self.state_text.set(f"✅ {result[:50]}")
    
    def test_microphone(self):
        self.add_log("Тест микрофона...", "info")
        self.status_label.config(text="🎤 Тест...")
        
        def test():
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    self.add_log("Говорите что-нибудь...", "info")
                    r.adjust_for_ambient_noise(source, duration=1)
                    audio = r.listen(source, timeout=5)
                    text = r.recognize_google(audio, language="ru-RU")
                    self.add_log(f"Распознано: {text}", "assistant")
                    self.voice.speak(f"Я услышал: {text}")
                    self.status_label.config(text="✅ Микрофон работает")
            except Exception as e:
                self.add_log(f"Ошибка: {e}", "error")
                self.status_label.config(text="❌ Ошибка микрофона")
        
        thread = threading.Thread(target=test)
        thread.daemon = True
        thread.start()
    
    def show_apps(self):
        apps = self.app_finder.get_all_found()
        if apps:
            msg = "Найденные приложения:\n\n"
            for name, path in list(apps.items())[:20]:
                msg += f"📌 {name}\n   → {path}\n\n"
            if len(apps) > 20:
                msg += f"... и еще {len(apps)-20} приложений"
            messagebox.showinfo("Найденные приложения", msg)
        else:
            messagebox.showinfo("Найденные приложения", 
                               "Пока не найдено приложений.\nСкажите 'открой что-нибудь' для поиска.")
    
    def listen_loop(self):
        self.add_log(f"Ассистент запущен! Скажите '{self.voice.get_wake_word()}' чтобы активировать", "info")
        
        while self.is_running:
            try:
                self.status_label.config(text="🎙️ Слушаю...", fg='#ffd93d')
                command = self.voice.listen()
                
                if command:
                    self.add_log(command, "user")
                    
                    # Проверка пробуждения
                    wake_word = self.voice.get_wake_word()
                    if wake_word in command and not self.voice.awake:
                        self.voice.set_awake(True)
                        greeting = self.voice.greet()
                        self.add_log(greeting, "assistant")
                        self.state_text.set(f"🎤 {greeting}")
                        continue
                    
                    # Обработка команды
                    if self.voice.awake:
                        self.status_label.config(text="⚡ Обработка...", fg='#e94560')
                        result = self.command_manager.process(command)
                        
                        if result:
                            self.add_log(result, "assistant")
                            self.voice.speak(result)
                            self.state_text.set(f"✅ {result[:50]}")
                        else:
                            self.state_text.set("💤 Ожидаю команду...")
                        
                        # Ассистент засыпает после команды
                        self.voice.set_awake(False)
                        self.state_text.set(f"💤 Скажите '{wake_word}' чтобы продолжить")
                    else:
                        self.state_text.set(f"💤 Скажите '{wake_word}' чтобы начать")
                
                self.status_label.config(text="⚪ Ожидание", fg='#888')
                time.sleep(0.1)
                
            except Exception as e:
                self.add_log(f"Ошибка: {e}", "error")
                time.sleep(1)
    
    def start_assistant(self):
        if not self.is_running:
            self.is_running = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.status_label.config(text="🟢 РАБОТАЕТ", fg='#4ecdc4')
            self.state_text.set(f"🎤 Ассистент активен. Скажите '{self.voice.get_wake_word()}'")
            
            self.listen_thread = threading.Thread(target=self.listen_loop)
            self.listen_thread.daemon = True
            self.listen_thread.start()
            
            self.add_log("🤖 Dravix Assistant запущен!", "assistant")
            self.voice.speak("Дравикс ассистент запущен. Скажите Дэвикс для активации")
    
    def stop_assistant(self):
        if self.is_running:
            self.is_running = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.status_label.config(text="⚪ ОСТАНОВЛЕН", fg='#888')
            self.state_text.set("💤 Ассистент остановлен")
            self.add_log("Ассистент остановлен", "info")
            self.voice.speak("Ассистент остановлен")
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        self.is_running = False
        self.root.destroy()

def main():
    app = DravixAssistantGUI()
    app.run()

if __name__ == "__main__":
    main()