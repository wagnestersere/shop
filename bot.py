import asyncio
import logging
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота (замени на свой)
BOT_TOKEN = "8659258274:AAHyG1ZCp0aBUjWlVqdS6_XJS2ead-2fYEw"

# Файл для хранения настроек
SETTINGS_FILE = "bot_settings.json"
ADMINS_FILE = "admins.json"
PAYMENT_SETTINGS_FILE = "payment_settings.json"

# Класс для работы с настройками
class SettingsManager:
    @staticmethod
    def load_settings(filename, default=None):
        if default is None:
            default = {}
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default
        except Exception as e:
            logging.error(f"Ошибка загрузки {filename}: {e}")
            return default
    
    @staticmethod
    def save_settings(filename, data):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"Ошибка сохранения {filename}: {e}")
            return False

# Загрузка администраторов
def load_admins():
    return SettingsManager.load_settings(ADMINS_FILE, {"admins": []})

# Сохранение администраторов
def save_admins(admins_data):
    return SettingsManager.save_settings(ADMINS_FILE, admins_data)

# Загрузка платежных настроек
def load_payment_settings():
    return SettingsManager.load_settings(PAYMENT_SETTINGS_FILE, {
        "payment_methods": [],
        "default_method": None
    })

# Сохранение платежных настроек
def save_payment_settings(settings):
    return SettingsManager.save_settings(PAYMENT_SETTINGS_FILE, settings)

# Проверка, является ли пользователь администратором
def is_admin(user_id):
    admins_data = load_admins()
    return str(user_id) in [str(admin_id) for admin_id in admins_data.get("admins", [])]

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния для FSM
class OrderStates(StatesGroup):
    choosing_category = State()
    choosing_product = State()
    entering_quantity = State()
    confirming_order = State()
    waiting_for_payment = State()

class AdminStates(StatesGroup):
    waiting_for_new_admin = State()
    waiting_for_remove_admin = State()
    waiting_for_payment_method_name = State()
    waiting_for_payment_method_details = State()
    waiting_for_payment_method_edit = State()

# Класс для хранения данных о товарах
class Product:
    def __init__(self, id, name, price, category, description="", image=None):
        self.id = id
        self.name = name
        self.price = price
        self.category = category
        self.description = description
        self.image = image

# Класс для хранения корзины
class Cart:
    def __init__(self):
        self.items = {}  # {product_id: quantity}
    
    def add_item(self, product_id, quantity=1):
        if product_id in self.items:
            self.items[product_id] += quantity
        else:
            self.items[product_id] = quantity
    
    def remove_item(self, product_id):
        if product_id in self.items:
            del self.items[product_id]
    
    def get_total(self, products):
        total = 0
        for product_id, quantity in self.items.items():
            product = next((p for p in products if p.id == product_id), None)
            if product:
                total += product.price * quantity
        return total
    
    def clear(self):
        self.items.clear()

# База данных товаров
products = [
    Product(1, "Товар 1", 100, "Электроника", "Описание товара 1"),
    Product(2, "Товар 2", 200, "Электроника", "Описание товара 2"),
    Product(3, "Товар 3", 150, "Одежда", "Описание товара 3"),
    Product(4, "Товар 4", 300, "Одежда", "Описание товара 4"),
    Product(5, "Товар 5", 250, "Книги", "Описание товара 5"),
]

# Получение уникальных категорий
categories = list(set([p.category for p in products]))

# Словарь для хранения корзин пользователей
user_carts = {}

def get_user_cart(user_id):
    if user_id not in user_carts:
        user_carts[user_id] = Cart()
    return user_carts[user_id]

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog"))
    keyboard.add(InlineKeyboardButton(text="🛒 Корзина", callback_data="view_cart"))
    keyboard.add(InlineKeyboardButton(text="📞 Контакты", callback_data="contacts"))
    keyboard.add(InlineKeyboardButton(text="ℹ️ О нас", callback_data="about"))
    
    # Добавляем кнопку админ-панели для администраторов
    if is_admin(message.from_user.id):
        keyboard.add(InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel"))
    
    keyboard.adjust(2)
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Добро пожаловать в наш магазин!\n"
        "Здесь ты можешь заказать товары прямо через Telegram.",
        reply_markup=keyboard.as_markup()
    )

# АДМИН-ПАНЕЛЬ
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав доступа!", show_alert=True)
        return
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="👥 Управление администраторами", callback_data="admin_manage"))
    keyboard.add(InlineKeyboardButton(text="💳 Настройка платежей", callback_data="admin_payment_settings"))
    keyboard.add(InlineKeyboardButton(text="📦 Управление товарами", callback_data="admin_products"))
    keyboard.add(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    keyboard.add(InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "🔐 **Панель администратора**\n\n"
        "Выберите раздел для управления:",
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

# УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ
@dp.callback_query(F.data == "admin_manage")
async def admin_management(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав доступа!", show_alert=True)
        return
    
    admins_data = load_admins()
    admins_list = admins_data.get("admins", [])
    
    admin_text = "👥 **Список администраторов:**\n\n"
    
    if admins_list:
        for i, admin_id in enumerate(admins_list, 1):
            try:
                user = await bot.get_chat(int(admin_id))
                admin_name = user.full_name
            except:
                admin_name = "Неизвестный пользователь"
            admin_text += f"{i}. {admin_name} (ID: {admin_id})\n"
    else:
        admin_text += "Список пуст\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="➕ Добавить администратора", callback_data="admin_add"))
    keyboard.add(InlineKeyboardButton(text="➖ Удалить администратора", callback_data="admin_remove"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        admin_text,
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_add")
async def admin_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📝 Отправьте ID пользователя, которого хотите сделать администратором.\n\n"
        "Пользователь может узнать свой ID у бота @userinfobot"
    )
    await state.set_state(AdminStates.waiting_for_new_admin)
    await callback.answer()

@dp.message(AdminStates.waiting_for_new_admin)
async def admin_add_process(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав доступа!")
        await state.clear()
        return
    
    try:
        new_admin_id = int(message.text.strip())
        admins_data = load_admins()
        
        if str(new_admin_id) in [str(admin_id) for admin_id in admins_data.get("admins", [])]:
            await message.answer("❌ Этот пользователь уже является администратором!")
        else:
            admins_data["admins"].append(new_admin_id)
            save_admins(admins_data)
            
            # Уведомляем нового администратора
            try:
                await bot.send_message(
                    new_admin_id,
                    "🎉 Поздравляем! Теперь вы стали администратором магазина!\n"
                    "Используйте /start для доступа к админ-панели."
                )
            except:
                pass
            
            await message.answer(f"✅ Пользователь с ID {new_admin_id} добавлен в администраторы!")
        
        await state.clear()
        
        # Возвращаемся в меню управления
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🔙 Вернуться к управлению", callback_data="admin_manage"))
        await message.answer("Выберите действие:", reply_markup=keyboard.as_markup())
        
    except ValueError:
        await message.answer("❌ Пожалуйста, отправьте корректный ID (только цифры)")

@dp.callback_query(F.data == "admin_remove")
async def admin_remove_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав доступа!", show_alert=True)
        return
    
    admins_data = load_admins()
    admins_list = admins_data.get("admins", [])
    
    if len(admins_list) <= 1:
        await callback.message.edit_text(
            "❌ Нельзя удалить последнего администратора!\n\n"
            "Должен остаться хотя бы один администратор."
        )
        await callback.answer()
        return
    
    keyboard = InlineKeyboardBuilder()
    
    for admin_id in admins_list:
        if str(admin_id) != str(callback.from_user.id):  # Не даем удалить самого себя
            try:
                user = await bot.get_chat(int(admin_id))
                admin_name = user.full_name
            except:
                admin_name = f"ID: {admin_id}"
            
            keyboard.add(InlineKeyboardButton(
                text=f"❌ {admin_name}",
                callback_data=f"remove_admin_{admin_id}"
            ))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "Выберите администратора для удаления:",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("remove_admin_"))
async def admin_remove_process(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав доступа!", show_alert=True)
        return
    
    admin_id_to_remove = int(callback.data.replace("remove_admin_", ""))
    
    admins_data = load_admins()
    
    if str(admin_id_to_remove) in [str(admin_id) for admin_id in admins_data.get("admins", [])]:
        admins_data["admins"].remove(admin_id_to_remove)
        save_admins(admins_data)
        
        # Уведомляем удаленного администратора
        try:
            await bot.send_message(
                admin_id_to_remove,
                "⚠️ Вы были удалены из списка администраторов магазина."
            )
        except:
            pass
        
        await callback.message.edit_text(
            f"✅ Администратор с ID {admin_id_to_remove} удален!"
        )
    else:
        await callback.message.edit_text("❌ Администратор не найден!")
    
    await callback.answer()

# НАСТРОЙКА ПЛАТЕЖЕЙ
@dp.callback_query(F.data == "admin_payment_settings")
async def payment_settings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав доступа!", show_alert=True)
        return
    
    payment_settings = load_payment_settings()
    
    settings_text = "💳 **Настройки платежей**\n\n"
    settings_text += f"**Текущие способы оплаты:**\n"
    
    if payment_settings.get("payment_methods"):
        for i, method in enumerate(payment_settings["payment_methods"], 1):
            is_default = "✅" if method.get("is_default") else ""
            settings_text += f"{i}. {method['name']} {is_default}\n"
            settings_text += f"   📝 {method['details']}\n\n"
    else:
        settings_text += "Способы оплаты не настроены\n\n"
    
    settings_text += f"**Способ по умолчанию:** {payment_settings.get('default_method', 'Не установлен')}"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="➕ Добавить способ", callback_data="payment_add"))
    
    if payment_settings.get("payment_methods"):
        keyboard.add(InlineKeyboardButton(text="✏️ Редактировать", callback_data="payment_edit"))
        keyboard.add(InlineKeyboardButton(text="⭐ Установить по умолчанию", callback_data="payment_set_default"))
        keyboard.add(InlineKeyboardButton(text="🗑 Удалить способ", callback_data="payment_delete"))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        settings_text,
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "payment_add")
async def payment_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📝 Введите название способа оплаты (например: 'Банковская карта', 'ЮMoney' и т.д.):"
    )
    await state.set_state(AdminStates.waiting_for_payment_method_name)
    await callback.answer()

@dp.message(AdminStates.waiting_for_payment_method_name)
async def payment_add_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав доступа!")
        await state.clear()
        return
    
    await state.update_data(payment_name=message.text.strip())
    await message.answer(
        "📝 Теперь введите реквизиты для оплаты.\n"
        "Например: номер карты, кошелек ЮMoney и т.д."
    )
    await state.set_state(AdminStates.waiting_for_payment_method_details)

@dp.message(AdminStates.waiting_for_payment_method_details)
async def payment_add_details(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав доступа!")
        await state.clear()
        return
    
    data = await state.get_data()
    payment_name = data.get("payment_name")
    payment_details = message.text.strip()
    
    payment_settings = load_payment_settings()
    
    if "payment_methods" not in payment_settings:
        payment_settings["payment_methods"] = []
    
    # Если это первый способ, делаем его по умолчанию
    is_default = len(payment_settings["payment_methods"]) == 0
    
    new_method = {
        "name": payment_name,
        "details": payment_details,
        "is_default": is_default
    }
    
    payment_settings["payment_methods"].append(new_method)
    
    if is_default:
        payment_settings["default_method"] = payment_name
    
    save_payment_settings(payment_settings)
    
    await message.answer(
        f"✅ Способ оплаты '{payment_name}' успешно добавлен!"
    )
    await state.clear()
    
    # Возвращаемся к настройкам
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Вернуться к настройкам", callback_data="admin_payment_settings"))
    await message.answer("Выберите действие:", reply_markup=keyboard.as_markup())

@dp.callback_query(F.data == "payment_set_default")
async def payment_set_default(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав доступа!", show_alert=True)
        return
    
    payment_settings = load_payment_settings()
    
    if not payment_settings.get("payment_methods"):
        await callback.answer("Нет доступных способов оплаты!", show_alert=True)
        return
    
    keyboard = InlineKeyboardBuilder()
    
    for method in payment_settings["payment_methods"]:
        keyboard.add(InlineKeyboardButton(
            text=f"⭐ {method['name']}",
            callback_data=f"set_default_{method['name']}"
        ))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_payment_settings"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "Выберите способ оплаты по умолчанию:",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("set_default_"))
async def payment_set_default_process(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав доступа!", show_alert=True)
        return
    
    method_name = callback.data.replace("set_default_", "")
    
    payment_settings = load_payment_settings()
    
    # Сбрасываем флаг is_default у всех способов
    for method in payment_settings["payment_methods"]:
        method["is_default"] = False
    
    # Устанавливаем новый способ по умолчанию
    for method in payment_settings["payment_methods"]:
        if method["name"] == method_name:
            method["is_default"] = True
            payment_settings["default_method"] = method_name
            break
    
    save_payment_settings(payment_settings)
    
    await callback.message.edit_text(
        f"✅ Способ оплаты '{method_name}' установлен по умолчанию!"
    )
    await callback.answer()

@dp.callback_query(F.data == "payment_delete")
async def payment_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав доступа!", show_alert=True)
        return
    
    payment_settings = load_payment_settings()
    
    if not payment_settings.get("payment_methods"):
        await callback.answer("Нет доступных способов оплаты!", show_alert=True)
        return
    
    keyboard = InlineKeyboardBuilder()
    
    for method in payment_settings["payment_methods"]:
        keyboard.add(InlineKeyboardButton(
            text=f"🗑 {method['name']}",
            callback_data=f"delete_payment_{method['name']}"
        ))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_payment_settings"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "Выберите способ оплаты для удаления:",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("delete_payment_"))
async def payment_delete_process(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав доступа!", show_alert=True)
        return
    
    method_name = callback.data.replace("delete_payment_", "")
    
    payment_settings = load_payment_settings()
    
    # Удаляем способ оплаты
    payment_settings["payment_methods"] = [
        method for method in payment_settings["payment_methods"] 
        if method["name"] != method_name
    ]
    
    # Если удалили способ по умолчанию
    if payment_settings.get("default_method") == method_name:
        if payment_settings["payment_methods"]:
            # Делаем первый способ по умолчанию
            payment_settings["payment_methods"][0]["is_default"] = True
            payment_settings["default_method"] = payment_settings["payment_methods"][0]["name"]
        else:
            payment_settings["default_method"] = None
    
    save_payment_settings(payment_settings)
    
    await callback.message.edit_text(
        f"✅ Способ оплаты '{method_name}' удален!"
    )
    await callback.answer()

# ОФОРМЛЕНИЕ ЗАКАЗА (обновленная версия с выбором оплаты)
@dp.callback_query(F.data == "checkout")
async def checkout(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    cart = get_user_cart(user_id)
    
    if not cart.items:
        await callback.answer("Корзина пуста!")
        return
    
    payment_settings = load_payment_settings()
    
    if not payment_settings.get("payment_methods"):
        # Если нет настроенных способов оплаты, используем стандартный
        await show_order_confirmation(callback, state, None)
        return
    
    # Показываем выбор способа оплаты
    keyboard = InlineKeyboardBuilder()
    
    for method in payment_settings["payment_methods"]:
        is_default = "⭐ " if method.get("is_default") else ""
        keyboard.add(InlineKeyboardButton(
            text=f"{is_default}{method['name']}",
            callback_data=f"select_payment_{method['name']}"
        ))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Вернуться в корзину", callback_data="view_cart"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "💳 **Выберите способ оплаты:**",
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(OrderStates.waiting_for_payment)
    await callback.answer()

@dp.callback_query(F.data.startswith("select_payment_"), OrderStates.waiting_for_payment)
async def select_payment_method(callback: CallbackQuery, state: FSMContext):
    payment_method = callback.data.replace("select_payment_", "")
    await state.update_data(selected_payment=payment_method)
    await show_order_confirmation(callback, state, payment_method)

async def show_order_confirmation(callback: CallbackQuery, state: FSMContext, payment_method):
    user_id = callback.from_user.id
    cart = get_user_cart(user_id)
    
    # Формируем текст заказа
    order_text = "📋 **Ваш заказ:**\n\n"
    total = 0
    
    for product_id, quantity in cart.items.items():
        product = next((p for p in products if p.id == product_id), None)
        if product:
            item_total = product.price * quantity
            total += item_total
            order_text += f"• {product.name} x{quantity} = {item_total}₽\n"
    
    order_text += f"\n**ИТОГО: {total}₽**"
    
    if payment_method:
        payment_settings = load_payment_settings()
        payment_details = next(
            (m["details"] for m in payment_settings["payment_methods"] if m["name"] == payment_method),
            "Реквизиты не указаны"
        )
        order_text += f"\n\n**Способ оплаты:** {payment_method}\n"
        order_text += f"**Реквизиты:** {payment_details}"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm_order"))
    keyboard.add(InlineKeyboardButton(text="🔙 Выбрать другой способ", callback_data="checkout"))
    keyboard.add(InlineKeyboardButton(text="🔙 Вернуться в корзину", callback_data="view_cart"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        order_text,
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(OrderStates.confirming_order)
    await callback.answer()

# Обработчик подтверждения заказа (обновленный)
@dp.callback_query(F.data == "confirm_order", OrderStates.confirming_order)
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    cart = get_user_cart(user_id)
    data = await state.get_data()
    payment_method = data.get("selected_payment", "Не указан")
    
    # Формируем текст заказа для администраторов
    order_text = f"🆕 **Новый заказ от пользователя**\n"
    order_text += f"👤 Имя: {callback.from_user.full_name}\n"
    order_text += f"🆔 ID: {user_id}\n"
    order_text += f"📱 Username: @{callback.from_user.username or 'Нет'}\n\n"
    order_text += "**Состав заказа:**\n"
    
    total = 0
    for product_id, quantity in cart.items.items():
        product = next((p for p in products if p.id == product_id), None)
        if product:
            item_total = product.price * quantity
            total += item_total
            order_text += f"• {product.name} x{quantity} = {item_total}₽\n"
    
    order_text += f"\n**ИТОГО: {total}₽**"
    order_text += f"\n**Способ оплаты:** {payment_method}"
    
    # Отправляем заказ всем администраторам
    admins_data = load_admins()
    sent_count = 0
    
    for admin_id in admins_data.get("admins", []):
        try:
            await bot.send_message(admin_id, order_text, parse_mode="Markdown")
            sent_count += 1
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление администратору {admin_id}: {e}")
    
    # Очищаем корзину пользователя
    cart.clear()
    
    # Отправляем подтверждение пользователю
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🛍 Продолжить покупки", callback_data="catalog"))
    keyboard.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
    
    await callback.message.edit_text(
        "✅ **Заказ успешно оформлен!**\n\n"
        "В ближайшее время с вами свяжется наш менеджер "
        "для подтверждения деталей заказа.\n"
        f"Способ оплаты: {payment_method}\n\n"
        "Спасибо за покупку!",
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await state.clear()
    await callback.answer()

# Остальные обработчики остаются без изменений (каталог, корзина и т.д.)
# ... (весь предыдущий код обработчиков из первого ответа)

# Запуск бота
async def main():
    # Создаем файлы настроек при первом запуске
    if not os.path.exists(ADMINS_FILE):
        # Добавляем пользователя, который запускает бота, как первого администратора
        # В реальном проекте нужно указать ID первого администратора
        first_admin_id = 123456789  # Замени на свой ID
        save_admins({"admins": [first_admin_id]})
    
    if not os.path.exists(PAYMENT_SETTINGS_FILE):
        save_payment_settings({
            "payment_methods": [],
            "default_method": None
        })
    
    logging.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())