#!/usr/bin/env python3
"""
DRAVIX ASSISTANT - Голосовой помощник для ПК
Запуск: python main.py
"""

import os
import sys
import subprocess

def install_dependencies():
    """Установка зависимостей"""
    print("=" * 60)
    print("📦 DRAVIX ASSISTANT - УСТАНОВКА ЗАВИСИМОСТЕЙ")
    print("=" * 60)
    
    with open("requirements.txt", "r") as f:
        deps = [d.strip() for d in f.read().split("\n") if d.strip()]
    
    for dep in deps:
        print(f"   📥 Установка {dep}...")
        subprocess.call([sys.executable, "-m", "pip", "install", dep, "-q"])
    
    print("✅ Все зависимости установлены!\n")

def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     ██████╗ ██████╗  █████╗ ██╗   ██╗██╗██╗  ██╗             ║
    ║     ██╔══██╗██╔══██╗██╔══██╗██║   ██║██║╚██╗██╔╝             ║
    ║     ██║  ██║██████╔╝███████║██║   ██║██║ ╚███╔╝              ║
    ║     ██║  ██║██╔══██╗██╔══██║╚██╗ ██╔╝██║ ██╔██╗              ║
    ║     ██████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║██╔╝ ██╗             ║
    ║     ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚═╝  ╚═╝             ║
    ║                                                               ║
    ║              DRAVIX ASSISTANT - ГОЛОСОВОЙ ПОМОЩНИК            ║
    ║                       ВЕРСИЯ 3.0                              ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Проверка зависимостей
    try:
        import speech_recognition
        import pyttsx3
        print("✅ Все зависимости установлены")
    except ImportError as e:
        print(f"⚠️ Отсутствует зависимость: {e}")
        choice = input("Установить все зависимости? (да/нет): ")
        if choice.lower() == "да":
            install_dependencies()
        else:
            print("❌ Установка отменена")
            return
    
    # Запуск GUI
    try:
        from assistant_gui import main as gui_main
        gui_main()
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        input("Нажмите Enter для выхода...")

if __name__ == "__main__":
    main()