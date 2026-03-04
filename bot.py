import asyncio
import logging
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8659258274:AAHyG1ZCp0aBUjWlVqdS6_XJS2ead-2fYEw"  # Замени на свой токен
FIRST_ADMIN_ID = 1627442580  # Замени на свой Telegram ID

# Файлы для хранения данных
SETTINGS_FILE = "bot_settings.json"
ADMINS_FILE = "admins.json"
PAYMENT_SETTINGS_FILE = "payment_settings.json"
PRODUCTS_FILE = "products.json"
USERS_FILE = "users.json"
ORDERS_FILE = "orders.json"

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== КЛАССЫ ДЛЯ РАБОТЫ С ДАННЫМИ ====================
class DataManager:
    """Класс для работы с JSON файлами"""
    
    @staticmethod
    def load(filename, default=None):
        if default is None:
            default = {}
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default
        except Exception as e:
            logger.error(f"Ошибка загрузки {filename}: {e}")
            return default
    
    @staticmethod
    def save(filename, data):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения {filename}: {e}")
            return False
    
    @staticmethod
    def backup(filename):
        """Создание резервной копии файла"""
        if os.path.exists(filename):
            backup_name = f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                import shutil
                shutil.copy2(filename, backup_name)
                return True
            except Exception as e:
                logger.error(f"Ошибка создания бэкапа: {e}")
        return False

# ==================== УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ ====================
def load_admins():
    """Загрузка списка администраторов"""
    data = DataManager.load(ADMINS_FILE, {"admins": []})
    if "admins" not in data:
        data["admins"] = []
    return data

def save_admins(admins_data):
    """Сохранение списка администраторов"""
    return DataManager.save(ADMINS_FILE, admins_data)

def is_admin(user_id):
    """Проверка, является ли пользователь администратором"""
    try:
        admins_data = load_admins()
        admins_list = admins_data.get("admins", [])
        user_id_int = int(user_id)
        admins_list_int = [int(a) for a in admins_list]
        return user_id_int in admins_list_int
    except Exception as e:
        logger.error(f"Ошибка в is_admin: {e}")
        return False

# ==================== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ====================
def load_users():
    """Загрузка списка пользователей"""
    data = DataManager.load(USERS_FILE, {"users": []})
    if "users" not in data:
        data["users"] = []
    return data

def save_users(users_data):
    """Сохранение списка пользователей"""
    return DataManager.save(USERS_FILE, users_data)

def register_user(user_id, username, first_name, last_name=None):
    """Регистрация нового пользователя"""
    users_data = load_users()
    
    # Проверяем, есть ли уже пользователь
    for user in users_data["users"]:
        if user["user_id"] == user_id:
            # Обновляем данные
            user["last_seen"] = datetime.now().isoformat()
            user["username"] = username
            user["first_name"] = first_name
            user["last_name"] = last_name
            save_users(users_data)
            return False  # Пользователь уже существовал
    
    # Добавляем нового пользователя
    users_data["users"].append({
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "registered_at": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat()
    })
    save_users(users_data)
    return True  # Новый пользователь

# ==================== УПРАВЛЕНИЕ ТОВАРАМИ ====================
def load_products():
    """Загрузка товаров"""
    default_products = [
        {"id": 1, "name": "Смартфон X", "price": 29990, "category": "Электроника", 
         "description": "Современный смартфон с отличной камерой", "in_stock": 10},
        {"id": 2, "name": "Ноутбук Pro", "price": 59990, "category": "Электроника", 
         "description": "Мощный ноутбук для работы и игр", "in_stock": 5},
        {"id": 3, "name": "Футболка", "price": 990, "category": "Одежда", 
         "description": "Хлопковая футболка", "in_stock": 50},
        {"id": 4, "name": "Джинсы", "price": 2990, "category": "Одежда", 
         "description": "Классические джинсы", "in_stock": 30},
        {"id": 5, "name": "Книга 'Python'", "price": 890, "category": "Книги", 
         "description": "Самоучитель по Python", "in_stock": 15},
    ]
    
    data = DataManager.load(PRODUCTS_FILE, default_products)
    return data

def save_products(products_list):
    """Сохранение товаров"""
    return DataManager.save(PRODUCTS_FILE, products_list)

def get_product(product_id):
    """Получение товара по ID"""
    products = load_products()
    for product in products:
        if product["id"] == product_id:
            return product
    return None

def get_next_product_id():
    """Получение следующего ID для товара"""
    products = load_products()
    if not products:
        return 1
    return max(p["id"] for p in products) + 1

def get_categories():
    """Получение списка категорий"""
    products = load_products()
    return sorted(list(set(p["category"] for p in products)))

# ==================== УПРАВЛЕНИЕ ПЛАТЕЖАМИ ====================
def load_payment_settings():
    """Загрузка настроек платежей"""
    default = {
        "payment_methods": [],
        "default_method": None
    }
    return DataManager.load(PAYMENT_SETTINGS_FILE, default)

def save_payment_settings(settings):
    """Сохранение настроек платежей"""
    return DataManager.save(PAYMENT_SETTINGS_FILE, settings)

# ==================== УПРАВЛЕНИЕ ЗАКАЗАМИ ====================
def load_orders():
    """Загрузка заказов"""
    data = DataManager.load(ORDERS_FILE, {"orders": [], "last_id": 0})
    if "orders" not in data:
        data["orders"] = []
    if "last_id" not in data:
        data["last_id"] = 0
    return data

def save_orders(orders_data):
    """Сохранение заказов"""
    return DataManager.save(ORDERS_FILE, orders_data)

def create_order(user_id, user_name, items, total, payment_method):
    """Создание нового заказа"""
    orders_data = load_orders()
    
    # Увеличиваем счетчик заказов
    orders_data["last_id"] += 1
    order_id = orders_data["last_id"]
    
    # Создаем заказ
    order = {
        "order_id": order_id,
        "user_id": user_id,
        "user_name": user_name,
        "items": items,
        "total": total,
        "payment_method": payment_method,
        "status": "new",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    orders_data["orders"].append(order)
    save_orders(orders_data)
    return order_id

# ==================== КЛАСС КОРЗИНЫ ====================
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
    
    def update_quantity(self, product_id, quantity):
        if quantity <= 0:
            self.remove_item(product_id)
        else:
            self.items[product_id] = quantity
    
    def get_items_with_details(self):
        """Получение товаров в корзине с деталями"""
        products = load_products()
        result = []
        for product_id, quantity in self.items.items():
            product = next((p for p in products if p["id"] == product_id), None)
            if product:
                result.append({
                    "product": product,
                    "quantity": quantity,
                    "total": product["price"] * quantity
                })
        return result
    
    def get_total(self):
        """Получение общей суммы корзины"""
        products = load_products()
        total = 0
        for product_id, quantity in self.items.items():
            product = next((p for p in products if p["id"] == product_id), None)
            if product:
                total += product["price"] * quantity
        return total
    
    def clear(self):
        self.items.clear()
    
    def is_empty(self):
        return len(self.items) == 0

# Словарь для хранения корзин пользователей
user_carts = {}

def get_user_cart(user_id):
    """Получение корзины пользователя"""
    if user_id not in user_carts:
        user_carts[user_id] = Cart()
    return user_carts[user_id]

# ==================== СОСТОЯНИЯ FSM ====================
class OrderStates(StatesGroup):
    choosing_category = State()
    choosing_product = State()
    entering_quantity = State()
    confirming_order = State()
    waiting_for_payment = State()

class AdminStates(StatesGroup):
    # Управление админами
    waiting_for_new_admin = State()
    
    # Управление товарами
    waiting_for_product_name = State()
    waiting_for_product_price = State()
    waiting_for_product_category = State()
    waiting_for_product_description = State()
    waiting_for_product_stock = State()
    waiting_for_product_edit_field = State()
    waiting_for_product_edit_value = State()
    waiting_for_product_id_to_edit = State()
    waiting_for_product_id_to_delete = State()
    
    # Управление категориями
    waiting_for_new_category = State()
    
    # Управление платежами
    waiting_for_payment_method_name = State()
    waiting_for_payment_method_details = State()
    waiting_for_payment_method_edit = State()
    
    # Рассылка
    waiting_for_broadcast_message = State()
    waiting_for_broadcast_confirm = State()

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== КОМАНДЫ ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Регистрируем пользователя
    is_new = register_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    # Приветственное сообщение
    welcome_text = (
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Добро пожаловать в наш магазин!\n"
        "Здесь ты можешь заказать товары прямо через Telegram.\n\n"
        "🛍 Используй кнопки ниже для навигации:"
    )
    
    # Создаем клавиатуру
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog"))
    keyboard.add(InlineKeyboardButton(text="🛒 Корзина", callback_data="view_cart"))
    keyboard.add(InlineKeyboardButton(text="📞 Контакты", callback_data="contacts"))
    keyboard.add(InlineKeyboardButton(text="ℹ️ О нас", callback_data="about"))
    keyboard.add(InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders"))
    
    # Добавляем админ-панель для администраторов
    if is_admin(user_id):
        keyboard.add(InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel"))
    
    keyboard.adjust(2)
    
    await message.answer(welcome_text, reply_markup=keyboard.as_markup())
    
    # Если новый пользователь, уведомляем администраторов
    if is_new:
        admins = load_admins()
        for admin_id in admins.get("admins", []):
            try:
                await bot.send_message(
                    admin_id,
                    f"🆕 **Новый пользователь!**\n\n"
                    f"ID: {user_id}\n"
                    f"Имя: {message.from_user.full_name}\n"
                    f"Username: @{message.from_user.username or 'нет'}"
                )
            except:
                pass

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "📚 **Помощь по боту**\n\n"
        "🛍 **Каталог** - просмотр товаров\n"
        "🛒 **Корзина** - управление корзиной\n"
        "📞 **Контакты** - наши контактные данные\n"
        "ℹ️ **О нас** - информация о магазине\n"
        "📋 **Мои заказы** - история заказов\n\n"
        "Для оформления заказа:\n"
        "1️⃣ Выберите товар в каталоге\n"
        "2️⃣ Добавьте его в корзину\n"
        "3️⃣ Перейдите в корзину и нажмите 'Оформить'\n"
        "4️⃣ Подтвердите заказ"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("checkadmin"))
async def cmd_checkadmin(message: Message):
    """Проверка статуса администратора"""
    user_id = message.from_user.id
    admin_status = is_admin(user_id)
    admins_data = load_admins()
    
    await message.answer(
        f"🔍 **Проверка администратора**\n\n"
        f"Твой ID: `{user_id}`\n"
        f"Статус: {'✅ Администратор' if admin_status else '❌ Пользователь'}\n\n"
        f"Список админов: `{admins_data.get('admins', [])}`",
        parse_mode="Markdown"
    )

# ==================== ОСНОВНЫЕ ОБРАБОТЧИКИ ПОЛЬЗОВАТЕЛЬСКОЙ ЧАСТИ ====================
@dp.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery, state: FSMContext):
    """Показать каталог категорий"""
    categories = get_categories()
    
    if not categories:
        await callback.message.edit_text(
            "📭 В каталоге пока нет товаров.",
            reply_markup=InlineKeyboardBuilder()
            .add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
            .as_markup()
        )
        await callback.answer()
        return
    
    keyboard = InlineKeyboardBuilder()
    
    for category in categories:
        keyboard.add(InlineKeyboardButton(
            text=category,
            callback_data=f"category_{category}"
        ))
    
    keyboard.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "📋 **Категории товаров:**\n\nВыберите категорию:",
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(OrderStates.choosing_category)
    await callback.answer()

@dp.callback_query(F.data.startswith("category_"))
async def show_products_by_category(callback: CallbackQuery, state: FSMContext):
    """Показать товары в категории"""
    category = callback.data.replace("category_", "")
    products = load_products()
    
    # Фильтруем товары по категории
    category_products = [p for p in products if p["category"] == category]
    
    if not category_products:
        await callback.message.edit_text(
            f"📭 В категории '{category}' пока нет товаров.",
            reply_markup=InlineKeyboardBuilder()
            .add(InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="catalog"))
            .add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
            .as_markup()
        )
        await callback.answer()
        return
    
    # Сортируем по цене
    category_products.sort(key=lambda x: x["price"])
    
    keyboard = InlineKeyboardBuilder()
    
    for product in category_products:
        stock_status = "✅" if product.get("in_stock", 0) > 0 else "❌"
        keyboard.add(InlineKeyboardButton(
            text=f"{stock_status} {product['name']} - {product['price']}₽",
            callback_data=f"product_{product['id']}"
        ))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="catalog"))
    keyboard.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        f"📦 **Товары в категории '{category}':**\n\n"
        f"Всего товаров: {len(category_products)}",
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(OrderStates.choosing_product)
    await callback.answer()

@dp.callback_query(F.data.startswith("product_"))
async def show_product_details(callback: CallbackQuery, state: FSMContext):
    """Показать детали товара"""
    product_id = int(callback.data.replace("product_", ""))
    product = get_product(product_id)
    
    if not product:
        await callback.answer("Товар не найден!", show_alert=True)
        return
    
    # Сохраняем выбранный товар
    await state.update_data(selected_product=product_id)
    
    # Проверяем наличие
    in_stock = product.get("in_stock", 0)
    stock_text = f"✅ В наличии: {in_stock} шт." if in_stock > 0 else "❌ Нет в наличии"
    
    product_info = (
        f"📦 **{product['name']}**\n\n"
        f"📝 {product['description']}\n\n"
        f"💰 **Цена:** {product['price']}₽\n"
        f"📁 **Категория:** {product['category']}\n"
        f"{stock_text}\n\n"
        f"🆔 ID товара: {product['id']}"
    )
    
    keyboard = InlineKeyboardBuilder()
    
    if in_stock > 0:
        keyboard.add(InlineKeyboardButton(text="➕ Добавить в корзину", callback_data=f"add_to_cart_{product_id}"))
        keyboard.add(InlineKeyboardButton(text="🔢 Выбрать количество", callback_data=f"choose_quantity_{product_id}"))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад к категории", callback_data=f"category_{product['category']}"))
    keyboard.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(product_info, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: CallbackQuery, state: FSMContext):
    """Добавить товар в корзину"""
    product_id = int(callback.data.replace("add_to_cart_", ""))
    user_id = callback.from_user.id
    cart = get_user_cart(user_id)
    
    product = get_product(product_id)
    if not product:
        await callback.answer("Товар не найден!", show_alert=True)
        return
    
    # Проверяем наличие
    if product.get("in_stock", 0) <= 0:
        await callback.answer("Товара нет в наличии!", show_alert=True)
        return
    
    cart.add_item(product_id)
    
    await callback.answer(f"✅ {product['name']} добавлен в корзину!")
    
    # Обновляем отображение товара
    await show_product_details(callback, state)

@dp.callback_query(F.data.startswith("choose_quantity_"))
async def choose_quantity_start(callback: CallbackQuery, state: FSMContext):
    """Начало выбора количества"""
    product_id = int(callback.data.replace("choose_quantity_", ""))
    product = get_product(product_id)
    
    if not product:
        await callback.answer("Товар не найден!", show_alert=True)
        return
    
    await state.update_data(quantity_product_id=product_id)
    
    await callback.message.edit_text(
        f"🔢 **Выбор количества**\n\n"
        f"Товар: {product['name']}\n"
        f"Цена: {product['price']}₽\n"
        f"В наличии: {product.get('in_stock', 0)} шт.\n\n"
        f"Введите количество (от 1 до {product.get('in_stock', 0)}):"
    )
    await state.set_state(OrderStates.entering_quantity)
    await callback.answer()

@dp.message(OrderStates.entering_quantity)
async def choose_quantity_process(message: Message, state: FSMContext):
    """Обработка выбора количества"""
    try:
        quantity = int(message.text.strip())
        data = await state.get_data()
        product_id = data.get("quantity_product_id")
        product = get_product(product_id)
        
        if not product:
            await message.answer("❌ Товар не найден!")
            await state.clear()
            return
        
        if quantity <= 0:
            await message.answer("❌ Количество должно быть больше 0!")
            return
        
        if quantity > product.get("in_stock", 0):
            await message.answer(f"❌ В наличии только {product.get('in_stock', 0)} шт.")
            return
        
        # Добавляем в корзину
        user_id = message.from_user.id
        cart = get_user_cart(user_id)
        cart.add_item(product_id, quantity)
        
        await message.answer(f"✅ {quantity} шт. товара '{product['name']}' добавлено в корзину!")
        await state.clear()
        
        # Показываем корзину
        await view_cart_from_message(message)
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число!")

@dp.callback_query(F.data == "view_cart")
async def view_cart(callback: CallbackQuery):
    """Просмотр корзины"""
    user_id = callback.from_user.id
    cart = get_user_cart(user_id)
    
    if cart.is_empty():
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🛍 Перейти в каталог", callback_data="catalog"))
        keyboard.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
        
        await callback.message.edit_text(
            "🛒 **Ваша корзина пуста!**",
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    items = cart.get_items_with_details()
    total = cart.get_total()
    
    cart_text = "🛒 **Ваша корзина:**\n\n"
    
    keyboard = InlineKeyboardBuilder()
    
    for item in items:
        product = item["product"]
        quantity = item["quantity"]
        item_total = item["total"]
        
        cart_text += f"📦 **{product['name']}**\n"
        cart_text += f"   Количество: {quantity} шт.\n"
        cart_text += f"   Цена: {product['price']}₽ x {quantity} = {item_total}₽\n\n"
        
        # Кнопки для управления количеством
        row = []
        row.append(InlineKeyboardButton(
            text=f"➖ {product['name']}",
            callback_data=f"cart_decrease_{product['id']}"
        ))
        row.append(InlineKeyboardButton(
            text=f"➕ {product['name']}",
            callback_data=f"cart_increase_{product['id']}"
        ))
        keyboard.row(*row)
        keyboard.add(InlineKeyboardButton(
            text=f"❌ Удалить {product['name']}",
            callback_data=f"cart_remove_{product['id']}"
        ))
    
    cart_text += f"**ИТОГО: {total}₽**"
    
    keyboard.add(InlineKeyboardButton(text="💳 Оформить заказ", callback_data="checkout"))
    keyboard.add(InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="cart_clear"))
    keyboard.add(InlineKeyboardButton(text="🛍 Продолжить покупки", callback_data="catalog"))
    keyboard.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(cart_text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

async def view_cart_from_message(message: Message):
    """Просмотр корзины из сообщения"""
    user_id = message.from_user.id
    cart = get_user_cart(user_id)
    
    if cart.is_empty():
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🛍 Перейти в каталог", callback_data="catalog"))
        keyboard.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
        
        await message.answer(
            "🛒 **Ваша корзина пуста!**",
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        return
    
    items = cart.get_items_with_details()
    total = cart.get_total()
    
    cart_text = "🛒 **Ваша корзина:**\n\n"
    
    keyboard = InlineKeyboardBuilder()
    
    for item in items:
        product = item["product"]
        quantity = item["quantity"]
        item_total = item["total"]
        
        cart_text += f"📦 **{product['name']}**\n"
        cart_text += f"   Количество: {quantity} шт.\n"
        cart_text += f"   Цена: {product['price']}₽ x {quantity} = {item_total}₽\n\n"
        
        # Кнопки для управления количеством
        row = []
        row.append(InlineKeyboardButton(
            text=f"➖ {product['name']}",
            callback_data=f"cart_decrease_{product['id']}"
        ))
        row.append(InlineKeyboardButton(
            text=f"➕ {product['name']}",
            callback_data=f"cart_increase_{product['id']}"
        ))
        keyboard.row(*row)
        keyboard.add(InlineKeyboardButton(
            text=f"❌ Удалить {product['name']}",
            callback_data=f"cart_remove_{product['id']}"
        ))
    
    cart_text += f"**ИТОГО: {total}₽**"
    
    keyboard.add(InlineKeyboardButton(text="💳 Оформить заказ", callback_data="checkout"))
    keyboard.add(InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="cart_clear"))
    keyboard.add(InlineKeyboardButton(text="🛍 Продолжить покупки", callback_data="catalog"))
    keyboard.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
    keyboard.adjust(1)
    
    await message.answer(cart_text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("cart_increase_"))
async def cart_increase(callback: CallbackQuery):
    """Увеличить количество товара в корзине"""
    product_id = int(callback.data.replace("cart_increase_", ""))
    user_id = callback.from_user.id
    cart = get_user_cart(user_id)
    
    product = get_product(product_id)
    if not product:
        await callback.answer("Товар не найден!", show_alert=True)
        return
    
    current_qty = cart.items.get(product_id, 0)
    if current_qty >= product.get("in_stock", 0):
        await callback.answer(f"Нельзя добавить больше {product.get('in_stock', 0)} шт.", show_alert=True)
        return
    
    cart.add_item(product_id, 1)
    await callback.answer("Количество увеличено")
    await view_cart(callback)

@dp.callback_query(F.data.startswith("cart_decrease_"))
async def cart_decrease(callback: CallbackQuery):
    """Уменьшить количество товара в корзине"""
    product_id = int(callback.data.replace("cart_decrease_", ""))
    user_id = callback.from_user.id
    cart = get_user_cart(user_id)
    
    current_qty = cart.items.get(product_id, 0)
    if current_qty <= 1:
        cart.remove_item(product_id)
        await callback.answer("Товар удален из корзины")
    else:
        cart.items[product_id] -= 1
        await callback.answer("Количество уменьшено")
    
    await view_cart(callback)

@dp.callback_query(F.data.startswith("cart_remove_"))
async def cart_remove(callback: CallbackQuery):
    """Удалить товар из корзины"""
    product_id = int(callback.data.replace("cart_remove_", ""))
    user_id = callback.from_user.id
    cart = get_user_cart(user_id)
    
    cart.remove_item(product_id)
    await callback.answer("✅ Товар удален из корзины")
    await view_cart(callback)

@dp.callback_query(F.data == "cart_clear")
async def cart_clear(callback: CallbackQuery):
    """Очистить корзину"""
    user_id = callback.from_user.id
    cart = get_user_cart(user_id)
    
    cart.clear()
    await callback.answer("🗑 Корзина очищена")
    await view_cart(callback)

@dp.callback_query(F.data == "checkout")
async def checkout(callback: CallbackQuery, state: FSMContext):
    """Оформление заказа"""
    user_id = callback.from_user.id
    cart = get_user_cart(user_id)
    
    if cart.is_empty():
        await callback.answer("Корзина пуста!", show_alert=True)
        return
    
    # Проверяем наличие всех товаров
    items = cart.get_items_with_details()
    for item in items:
        product = item["product"]
        if product.get("in_stock", 0) < item["quantity"]:
            await callback.answer(
                f"❌ Товара '{product['name']}' осталось только {product.get('in_stock', 0)} шт.",
                show_alert=True
            )
            return
    
    # Получаем настройки платежей
    payment_settings = load_payment_settings()
    payment_methods = payment_settings.get("payment_methods", [])
    
    if not payment_methods:
        # Если нет способов оплаты, сразу подтверждение
        await show_order_confirmation(callback, state, None)
        return
    
    # Показываем выбор способа оплаты
    keyboard = InlineKeyboardBuilder()
    
    for method in payment_methods:
        default = "⭐ " if method.get("is_default") else ""
        keyboard.add(InlineKeyboardButton(
            text=f"{default}{method['name']}",
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
    """Выбор способа оплаты"""
    payment_method = callback.data.replace("select_payment_", "")
    await state.update_data(selected_payment=payment_method)
    await show_order_confirmation(callback, state, payment_method)

async def show_order_confirmation(callback: CallbackQuery, state: FSMContext, payment_method):
    """Показать подтверждение заказа"""
    user_id = callback.from_user.id
    cart = get_user_cart(user_id)
    items = cart.get_items_with_details()
    total = cart.get_total()
    
    order_text = "📋 **Подтверждение заказа**\n\n"
    order_text += "**Состав заказа:**\n"
    
    for item in items:
        product = item["product"]
        quantity = item["quantity"]
        item_total = item["total"]
        order_text += f"• {product['name']} x{quantity} = {item_total}₽\n"
    
    order_text += f"\n**ИТОГО: {total}₽**"
    
    if payment_method:
        payment_settings = load_payment_settings()
        payment_details = next(
            (m["details"] for m in payment_settings.get("payment_methods", []) if m["name"] == payment_method),
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

@dp.callback_query(F.data == "confirm_order", OrderStates.confirming_order)
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и создание заказа"""
    user_id = callback.from_user.id
    cart = get_user_cart(user_id)
    data = await state.get_data()
    payment_method = data.get("selected_payment", "Не указан")
    
    # Получаем детали корзины
    items = cart.get_items_with_details()
    total = cart.get_total()
    
    # Создаем заказ в базе данных
    order_id = create_order(
        user_id=user_id,
        user_name=callback.from_user.full_name,
        items=[{
            "product_id": item["product"]["id"],
            "product_name": item["product"]["name"],
            "price": item["product"]["price"],
            "quantity": item["quantity"],
            "total": item["total"]
        } for item in items],
        total=total,
        payment_method=payment_method
    )
    
    # Уменьшаем количество товаров на складе
    products = load_products()
    for item in items:
        for product in products:
            if product["id"] == item["product"]["id"]:
                product["in_stock"] = product.get("in_stock", 0) - item["quantity"]
                break
    save_products(products)
    
    # Формируем текст заказа для администраторов
    order_text = f"🆕 **Новый заказ #{order_id}**\n\n"
    order_text += f"👤 **Покупатель:**\n"
    order_text += f"• Имя: {callback.from_user.full_name}\n"
    order_text += f"• ID: {user_id}\n"
    order_text += f"• Username: @{callback.from_user.username or 'нет'}\n\n"
    order_text += f"📦 **Состав заказа:**\n"
    
    for item in items:
        order_text += f"• {item['product']['name']} x{item['quantity']} = {item['total']}₽\n"
    
    order_text += f"\n💰 **ИТОГО: {total}₽**"
    order_text += f"\n💳 **Способ оплаты:** {payment_method}"
    order_text += f"\n🕐 **Время:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    
    # Отправляем заказ всем администраторам
    admins_data = load_admins()
    sent_count = 0
    
    for admin_id in admins_data.get("admins", []):
        try:
            # Создаем клавиатуру для администратора
            admin_keyboard = InlineKeyboardBuilder()
            admin_keyboard.add(InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"admin_order_confirm_{order_id}"
            ))
            admin_keyboard.add(InlineKeyboardButton(
                text="📦 В обработке",
                callback_data=f"admin_order_processing_{order_id}"
            ))
            admin_keyboard.add(InlineKeyboardButton(
                text="✅ Выполнен",
                callback_data=f"admin_order_completed_{order_id}"
            ))
            admin_keyboard.add(InlineKeyboardButton(
                text="❌ Отменить",
                callback_data=f"admin_order_cancel_{order_id}"
            ))
            admin_keyboard.adjust(2)
            
            await bot.send_message(
                admin_id,
                order_text,
                reply_markup=admin_keyboard.as_markup(),
                parse_mode="Markdown"
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление администратору {admin_id}: {e}")
    
    # Очищаем корзину пользователя
    cart.clear()
    
    # Отправляем подтверждение пользователю
    user_keyboard = InlineKeyboardBuilder()
    user_keyboard.add(InlineKeyboardButton(text="🛍 Продолжить покупки", callback_data="catalog"))
    user_keyboard.add(InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders"))
    user_keyboard.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
    user_keyboard.adjust(1)
    
    await callback.message.edit_text(
        f"✅ **Заказ #{order_id} успешно оформлен!**\n\n"
        f"Спасибо за покупку!\n"
        f"В ближайшее время с вами свяжется наш менеджер.\n\n"
        f"💳 Способ оплаты: {payment_method}\n"
        f"💰 Сумма: {total}₽\n\n"
        f"Статус заказа: **Новый**",
        reply_markup=user_keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await state.clear()
    await callback.answer("✅ Заказ оформлен!")

@dp.callback_query(F.data == "my_orders")
async def my_orders(callback: CallbackQuery):
    """Просмотр истории заказов пользователя"""
    user_id = callback.from_user.id
    orders_data = load_orders()
    
    # Фильтруем заказы пользователя
    user_orders = [o for o in orders_data.get("orders", []) if o["user_id"] == user_id]
    user_orders.sort(key=lambda x: x["created_at"], reverse=True)
    
    if not user_orders:
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🛍 Перейти в каталог", callback_data="catalog"))
        keyboard.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
        
        await callback.message.edit_text(
            "📋 У вас пока нет заказов.",
            reply_markup=keyboard.as_markup()
        )
        await callback.answer()
        return
    
    # Показываем последние 5 заказов
    text = "📋 **Мои заказы**\n\n"
    
    for order in user_orders[:5]:
        status_emoji = {
            "new": "🆕",
            "processing": "⚙️",
            "confirmed": "✅",
            "completed": "✔️",
            "cancelled": "❌"
        }.get(order["status"], "📦")
        
        created = datetime.fromisoformat(order["created_at"]).strftime("%d.%m.%Y %H:%M")
        text += f"{status_emoji} **Заказ #{order['order_id']}**\n"
        text += f"   от {created}\n"
        text += f"   Сумма: {order['total']}₽\n"
        text += f"   Статус: {get_status_text(order['status'])}\n\n"
    
    if len(user_orders) > 5:
        text += f"*Показано 5 последних заказов из {len(user_orders)}*\n\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔍 Детали заказа", callback_data="order_details"))
    keyboard.add(InlineKeyboardButton(text="🛍 В каталог", callback_data="catalog"))
    keyboard.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

def get_status_text(status):
    """Получение текста статуса"""
    statuses = {
        "new": "🆕 Новый",
        "processing": "⚙️ В обработке",
        "confirmed": "✅ Подтвержден",
        "completed": "✔️ Выполнен",
        "cancelled": "❌ Отменен"
    }
    return statuses.get(status, status)

@dp.callback_query(F.data == "order_details")
async def order_details_start(callback: CallbackQuery, state: FSMContext):
    """Начало просмотра деталей заказа"""
    await callback.message.edit_text(
        "🔍 Введите номер заказа:"
    )
    # Здесь нужно добавить состояние для ввода номера заказа
    await callback.answer()

@dp.callback_query(F.data == "contacts")
async def show_contacts(callback: CallbackQuery):
    """Показать контакты"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📧 Написать менеджеру", url="https://t.me/manager"))
    keyboard.add(InlineKeyboardButton(text="📞 Позвонить", url="tel:+79991234567"))
    keyboard.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "📞 **Наши контакты**\n\n"
        "📧 Email: shop@example.com\n"
        "📱 Телефон: +7 (999) 123-45-67\n"
        "📍 Адрес: г. Москва, ул. Примерная, д. 1\n"
        "🕒 Время работы: 24/7\n\n"
        "💬 По всем вопросам обращайтесь к менеджеру!",
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "about")
async def show_about(callback: CallbackQuery):
    """Информация о магазине"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📦 Каталог", callback_data="catalog"))
    keyboard.add(InlineKeyboardButton(text="📞 Контакты", callback_data="contacts"))
    keyboard.add(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "ℹ️ **О нашем магазине**\n\n"
        "Мы - современный интернет-магазин, работающий\n"
        "непосредственно через Telegram.\n\n"
        "✅ **Наши преимущества:**\n"
        "• Быстрая доставка по всей стране\n"
        "• Только качественные товары\n"
        "• Гарантия на все товары\n"
        "• Поддержка 24/7\n"
        "• Удобная оплата\n\n"
        "📦 **Доставка:**\n"
        "• Почта России - от 3 дней\n"
        "• СДЭК - от 1 дня\n"
        "• Курьером по Москве - в день заказа\n\n"
        "💰 **Оплата:**\n"
        "• Наличными при получении\n"
        "• Банковской картой\n"
        "• Переводом на карту",
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await cmd_start(callback.message)
    await callback.answer()

# ==================== АДМИН-ПАНЕЛЬ ====================
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    """Главная панель администратора"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав доступа!", show_alert=True)
        return
    
    # Получаем статистику
    products = load_products()
    orders_data = load_orders()
    users_data = load_users()
    
    new_orders = len([o for o in orders_data.get("orders", []) if o["status"] == "new"])
    total_users = len(users_data.get("users", []))
    total_products = len(products)
    
    text = "🔐 **Панель администратора**\n\n"
    text += f"📊 **Статистика:**\n"
    text += f"• Новых заказов: {new_orders}\n"
    text += f"• Пользователей: {total_users}\n"
    text += f"• Товаров: {total_products}\n\n"
    text += "Выберите раздел для управления:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📦 Управление товарами", callback_data="admin_products"))
    keyboard.add(InlineKeyboardButton(text="📋 Управление заказами", callback_data="admin_orders"))
    keyboard.add(InlineKeyboardButton(text="💳 Настройка платежей", callback_data="admin_payment_settings"))
    keyboard.add(InlineKeyboardButton(text="👥 Управление админами", callback_data="admin_manage"))
    keyboard.add(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    keyboard.add(InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast"))
    keyboard.add(InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"))
    keyboard.add(InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    keyboard.adjust(2)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

# ==================== УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ ====================
@dp.callback_query(F.data == "admin_manage")
async def admin_manage(callback: CallbackQuery):
    """Управление администраторами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    admins_data = load_admins()
    admins_list = admins_data.get("admins", [])
    
    text = "👥 **Управление администраторами**\n\n"
    text += f"Всего администраторов: {len(admins_list)}\n\n"
    
    if admins_list:
        text += "**Список администраторов:**\n"
        for i, admin_id in enumerate(admins_list, 1):
            try:
                user = await bot.get_chat(int(admin_id))
                name = user.full_name
            except:
                name = "Неизвестно"
            text += f"{i}. {name} (ID: {admin_id})\n"
    else:
        text += "Список администраторов пуст\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add"))
    if len(admins_list) > 1:
        keyboard.add(InlineKeyboardButton(text="➖ Удалить админа", callback_data="admin_remove_list"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_add")
async def admin_add_start(callback: CallbackQuery, state: FSMContext):
    """Добавление администратора"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📝 **Добавление администратора**\n\n"
        "Отправьте ID пользователя, которого хотите сделать администратором.\n\n"
        "Пользователь может узнать свой ID у бота @userinfobot"
    )
    await state.set_state(AdminStates.waiting_for_new_admin)
    await callback.answer()

@dp.message(AdminStates.waiting_for_new_admin)
async def admin_add_process(message: Message, state: FSMContext):
    """Обработка добавления администратора"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    try:
        new_admin_id = int(message.text.strip())
        admins_data = load_admins()
        
        if new_admin_id in admins_data.get("admins", []):
            await message.answer("❌ Этот пользователь уже является администратором!")
        else:
            admins_data["admins"].append(new_admin_id)
            save_admins(admins_data)
            
            # Уведомляем нового администратора
            try:
                await bot.send_message(
                    new_admin_id,
                    "🎉 **Поздравляем!**\n\n"
                    "Теперь вы стали администратором магазина!\n"
                    "Используйте /start для доступа к админ-панели."
                )
            except:
                pass
            
            await message.answer(f"✅ Пользователь с ID {new_admin_id} добавлен в администраторы!")
        
        await state.clear()
        
        # Возвращаемся в меню
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🔙 Вернуться к управлению", callback_data="admin_manage"))
        await message.answer("Выберите действие:", reply_markup=keyboard.as_markup())
        
    except ValueError:
        await message.answer("❌ Пожалуйста, отправьте корректный ID (только цифры)")

@dp.callback_query(F.data == "admin_remove_list")
async def admin_remove_list(callback: CallbackQuery):
    """Список для удаления администраторов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    admins_data = load_admins()
    admins_list = admins_data.get("admins", [])
    
    if len(admins_list) <= 1:
        await callback.message.edit_text(
            "❌ Нельзя удалить последнего администратора!\n\n"
            "Должен остаться хотя бы один администратор.",
            reply_markup=InlineKeyboardBuilder()
            .add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage"))
            .as_markup()
        )
        await callback.answer()
        return
    
    keyboard = InlineKeyboardBuilder()
    
    for admin_id in admins_list:
        if admin_id != callback.from_user.id:  # Не даем удалить самого себя
            try:
                user = await bot.get_chat(int(admin_id))
                name = user.full_name
            except:
                name = f"ID: {admin_id}"
            
            keyboard.add(InlineKeyboardButton(
                text=f"❌ {name}",
                callback_data=f"admin_remove_{admin_id}"
            ))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "Выберите администратора для удаления:",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_remove_"))
async def admin_remove_process(callback: CallbackQuery):
    """Удаление администратора"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    admin_id_to_remove = int(callback.data.replace("admin_remove_", ""))
    
    if admin_id_to_remove == callback.from_user.id:
        await callback.answer("Нельзя удалить самого себя!", show_alert=True)
        return
    
    admins_data = load_admins()
    
    if admin_id_to_remove in admins_data.get("admins", []):
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

# ==================== УПРАВЛЕНИЕ ТОВАРАМИ ====================
@dp.callback_query(F.data == "admin_products")
async def admin_products(callback: CallbackQuery):
    """Управление товарами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    products = load_products()
    
    text = "📦 **Управление товарами**\n\n"
    text += f"Всего товаров: {len(products)}\n"
    text += f"Категорий: {len(get_categories())}\n\n"
    
    # Товары с малым остатком
    low_stock = [p for p in products if p.get("in_stock", 0) < 5]
    if low_stock:
        text += "⚠️ **Товары с малым остатком:**\n"
        for p in low_stock[:3]:
            text += f"• {p['name']} - осталось {p.get('in_stock', 0)} шт.\n"
        text += "\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_product_add"))
    keyboard.add(InlineKeyboardButton(text="📋 Список товаров", callback_data="admin_product_list"))
    keyboard.add(InlineKeyboardButton(text="✏️ Редактировать товар", callback_data="admin_product_edit"))
    keyboard.add(InlineKeyboardButton(text="🗑 Удалить товар", callback_data="admin_product_delete"))
    keyboard.add(InlineKeyboardButton(text="📁 Управление категориями", callback_data="admin_categories"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_product_add")
async def admin_product_add_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления товара"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📝 **Добавление нового товара**\n\n"
        "Шаг 1 из 5\n"
        "Введите **название** товара:"
    )
    await state.set_state(AdminStates.waiting_for_product_name)
    await callback.answer()

@dp.message(AdminStates.waiting_for_product_name)
async def admin_product_add_name(message: Message, state: FSMContext):
    """Получение названия товара"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    await state.update_data(product_name=message.text.strip())
    await message.answer(
        "Шаг 2 из 5\n"
        "💰 Введите **цену** товара (только цифры, в рублях):"
    )
    await state.set_state(AdminStates.waiting_for_product_price)

@dp.message(AdminStates.waiting_for_product_price)
async def admin_product_add_price(message: Message, state: FSMContext):
    """Получение цены товара"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    try:
        price = float(message.text.strip())
        if price <= 0:
            await message.answer("❌ Цена должна быть больше 0!")
            return
        
        await state.update_data(product_price=price)
        
        # Получаем список категорий
        categories = get_categories()
        text = "Шаг 3 из 5\n"
        text += "📁 Введите **категорию** товара:\n\n"
        
        if categories:
            text += "**Существующие категории:**\n"
            text += "\n".join([f"• {cat}" for cat in categories])
            text += "\n\nВы можете выбрать существующую или создать новую."
        
        await message.answer(text)
        await state.set_state(AdminStates.waiting_for_product_category)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число!")

@dp.message(AdminStates.waiting_for_product_category)
async def admin_product_add_category(message: Message, state: FSMContext):
    """Получение категории товара"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    await state.update_data(product_category=message.text.strip())
    await message.answer(
        "Шаг 4 из 5\n"
        "📝 Введите **описание** товара:"
    )
    await state.set_state(AdminStates.waiting_for_product_description)

@dp.message(AdminStates.waiting_for_product_description)
async def admin_product_add_description(message: Message, state: FSMContext):
    """Получение описания товара"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    await state.update_data(product_description=message.text.strip())
    await message.answer(
        "Шаг 5 из 5\n"
        "📦 Введите **количество** товара в наличии:"
    )
    await state.set_state(AdminStates.waiting_for_product_stock)

@dp.message(AdminStates.waiting_for_product_stock)
async def admin_product_add_stock(message: Message, state: FSMContext):
    """Получение количества и сохранение товара"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    try:
        stock = int(message.text.strip())
        if stock < 0:
            await message.answer("❌ Количество не может быть отрицательным!")
            return
        
        data = await state.get_data()
        products = load_products()
        
        new_product = {
            "id": get_next_product_id(),
            "name": data["product_name"],
            "price": data["product_price"],
            "category": data["product_category"],
            "description": data["product_description"],
            "in_stock": stock
        }
        
        products.append(new_product)
        save_products(products)
        
        await message.answer(
            f"✅ **Товар успешно добавлен!**\n\n"
            f"📦 **{new_product['name']}**\n"
            f"💰 Цена: {new_product['price']}₽\n"
            f"📁 Категория: {new_product['category']}\n"
            f"📦 В наличии: {new_product['in_stock']} шт.\n"
            f"🆔 ID товара: {new_product['id']}"
        )
        await state.clear()
        
        # Возвращаемся в меню товаров
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🔙 Вернуться к товарам", callback_data="admin_products"))
        await message.answer("Выберите действие:", reply_markup=keyboard.as_markup())
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите целое число!")

@dp.callback_query(F.data == "admin_product_list")
async def admin_product_list(callback: CallbackQuery):
    """Просмотр всех товаров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    products = load_products()
    
    if not products:
        await callback.message.edit_text(
            "📦 Товаров пока нет",
            reply_markup=InlineKeyboardBuilder()
            .add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_products"))
            .as_markup()
        )
        await callback.answer()
        return
    
    # Сохраняем текущую страницу в состоянии
    page = 0
    items_per_page = 5
    
    await show_products_page(callback.message, page, products)

async def show_products_page(message, page, products):
    """Показать страницу с товарами"""
    items_per_page = 5
    total_pages = (len(products) + items_per_page - 1) // items_per_page
    
    start = page * items_per_page
    end = start + items_per_page
    current_products = products[start:end]
    
    text = f"📋 **Список товаров (страница {page + 1}/{total_pages})**\n\n"
    
    for product in current_products:
        stock_status = "✅" if product.get("in_stock", 0) > 0 else "❌"
        text += f"🆔 **{product['id']}** | {stock_status} {product['name']}\n"
        text += f"   💰 {product['price']}₽ | 📁 {product['category']}\n"
        text += f"   📦 В наличии: {product.get('in_stock', 0)} шт.\n"
        text += f"   📝 {product['description'][:50]}...\n\n"
    
    keyboard = InlineKeyboardBuilder()
    
    if page > 0:
        keyboard.add(InlineKeyboardButton(text="◀️ Пред", callback_data=f"product_page_{page-1}"))
    if page < total_pages - 1:
        keyboard.add(InlineKeyboardButton(text="След ▶️", callback_data=f"product_page_{page+1}"))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_products"))
    keyboard.adjust(2)
    
    await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("product_page_"))
async def admin_product_page(callback: CallbackQuery):
    """Пагинация списка товаров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    page = int(callback.data.replace("product_page_", ""))
    products = load_products()
    await show_products_page(callback.message, page, products)
    await callback.answer()

@dp.callback_query(F.data == "admin_product_edit")
async def admin_product_edit_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования товара"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "✏️ **Редактирование товара**\n\n"
        "Введите ID товара, который хотите отредактировать:"
    )
    await state.set_state(AdminStates.waiting_for_product_id_to_edit)
    await callback.answer()

@dp.message(AdminStates.waiting_for_product_id_to_edit)
async def admin_product_edit_select(message: Message, state: FSMContext):
    """Выбор товара для редактирования"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    try:
        product_id = int(message.text.strip())
        product = get_product(product_id)
        
        if not product:
            await message.answer("❌ Товар с таким ID не найден!")
            await state.clear()
            return
        
        await state.update_data(edit_product_id=product_id)
        
        text = f"✏️ **Редактирование товара**\n\n"
        text += f"📦 **{product['name']}**\n"
        text += f"💰 Цена: {product['price']}₽\n"
        text += f"📁 Категория: {product['category']}\n"
        text += f"📦 В наличии: {product.get('in_stock', 0)} шт.\n"
        text += f"📝 Описание: {product['description']}\n\n"
        text += "Что хотите изменить?"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="📝 Название", callback_data="edit_field_name"))
        keyboard.add(InlineKeyboardButton(text="💰 Цену", callback_data="edit_field_price"))
        keyboard.add(InlineKeyboardButton(text="📁 Категорию", callback_data="edit_field_category"))
        keyboard.add(InlineKeyboardButton(text="📦 Количество", callback_data="edit_field_stock"))
        keyboard.add(InlineKeyboardButton(text="📝 Описание", callback_data="edit_field_description"))
        keyboard.add(InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_products"))
        keyboard.adjust(2)
        
        await message.answer(text, reply_markup=keyboard.as_markup())
        await state.set_state(AdminStates.waiting_for_product_edit_field)
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число!")

@dp.callback_query(F.data.startswith("edit_field_"), AdminStates.waiting_for_product_edit_field)
async def admin_product_edit_field(callback: CallbackQuery, state: FSMContext):
    """Выбор поля для редактирования"""
    field = callback.data.replace("edit_field_", "")
    
    field_names = {
        "name": "название",
        "price": "цену",
        "category": "категорию",
        "stock": "количество",
        "description": "описание"
    }
    
    await state.update_data(edit_field=field)
    await callback.message.edit_text(
        f"✏️ Введите новое **{field_names.get(field, field)}** товара:"
    )
    await state.set_state(AdminStates.waiting_for_product_edit_value)
    await callback.answer()

@dp.message(AdminStates.waiting_for_product_edit_value)
async def admin_product_edit_value(message: Message, state: FSMContext):
    """Сохранение изменений товара"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    data = await state.get_data()
    product_id = data.get("edit_product_id")
    field = data.get("edit_field")
    
    products = load_products()
    product = None
    
    for p in products:
        if p["id"] == product_id:
            product = p
            break
    
    if not product:
        await message.answer("❌ Товар не найден!")
        await state.clear()
        return
    
    # Валидация в зависимости от поля
    try:
        if field == "price":
            value = float(message.text.strip())
            if value <= 0:
                                await message.answer("❌ Цена должна быть больше 0!")
            return
        elif field == "stock":
            value = int(message.text.strip())
            if value < 0:
                await message.answer("❌ Количество не может быть отрицательным!")
                return
        else:
            value = message.text.strip()
            if not value:
                await message.answer("❌ Значение не может быть пустым!")
                return
    except ValueError:
        await message.answer("❌ Неверный формат данных!")
        return
    
    # Обновляем поле
    old_value = product[field]
    product[field] = value
    
    # Сохраняем изменения
    save_products(products)
    
    await message.answer(
        f"✅ **Товар обновлен!**\n\n"
        f"Поле '{field}' изменено с '{old_value}' на '{value}'"
    )
    await state.clear()
    
    # Возвращаемся в меню товаров
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Вернуться к товарам", callback_data="admin_products"))
    await message.answer("Выберите действие:", reply_markup=keyboard.as_markup())

@dp.callback_query(F.data == "admin_product_delete")
async def admin_product_delete_start(callback: CallbackQuery, state: FSMContext):
    """Начало удаления товара"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🗑 **Удаление товара**\n\n"
        "Введите ID товара, который хотите удалить:"
    )
    await state.set_state(AdminStates.waiting_for_product_id_to_delete)
    await callback.answer()

@dp.message(AdminStates.waiting_for_product_id_to_delete)
async def admin_product_delete_process(message: Message, state: FSMContext):
    """Удаление товара"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    try:
        product_id = int(message.text.strip())
        products = load_products()
        
        # Ищем товар
        product_to_delete = None
        for product in products:
            if product["id"] == product_id:
                product_to_delete = product
                break
        
        if not product_to_delete:
            await message.answer("❌ Товар с таким ID не найден!")
            await state.clear()
            return
        
        # Удаляем товар
        products = [p for p in products if p["id"] != product_id]
        save_products(products)
        
        await message.answer(
            f"✅ **Товар удален!**\n\n"
            f"📦 {product_to_delete['name']}\n"
            f"💰 Цена: {product_to_delete['price']}₽\n"
            f"📁 Категория: {product_to_delete['category']}"
        )
        await state.clear()
        
        # Возвращаемся в меню товаров
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🔙 Вернуться к товарам", callback_data="admin_products"))
        await message.answer("Выберите действие:", reply_markup=keyboard.as_markup())
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число!")

@dp.callback_query(F.data == "admin_categories")
async def admin_categories(callback: CallbackQuery):
    """Управление категориями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    categories = get_categories()
    products = load_products()
    
    text = "📁 **Управление категориями**\n\n"
    text += f"Всего категорий: {len(categories)}\n\n"
    
    if categories:
        text += "**Список категорий:**\n"
        for category in categories:
            # Считаем товары в категории
            count = len([p for p in products if p["category"] == category])
            text += f"• {category} - {count} товаров\n"
    else:
        text += "Категорий пока нет\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin_category_add"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_products"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_category_add")
async def admin_category_add_start(callback: CallbackQuery, state: FSMContext):
    """Добавление новой категории"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📝 Введите название новой категории:"
    )
    await state.set_state(AdminStates.waiting_for_new_category)
    await callback.answer()

@dp.message(AdminStates.waiting_for_new_category)
async def admin_category_add_process(message: Message, state: FSMContext):
    """Сохранение новой категории"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    category_name = message.text.strip()
    categories = get_categories()
    
    if category_name in categories:
        await message.answer("❌ Такая категория уже существует!")
        await state.clear()
        return
    
    # Категория просто создается, когда появится товар с этой категорией
    # Поэтому просто показываем сообщение
    await message.answer(
        f"✅ Категория '{category_name}' будет доступна при добавлении товаров!"
    )
    await state.clear()
    
    # Возвращаемся к категориям
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Вернуться к категориям", callback_data="admin_categories"))
    await message.answer("Выберите действие:", reply_markup=keyboard.as_markup())

# ==================== УПРАВЛЕНИЕ ЗАКАЗАМИ ====================
@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):
    """Управление заказами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    orders_data = load_orders()
    orders = orders_data.get("orders", [])
    
    # Статистика по статусам
    new_count = len([o for o in orders if o["status"] == "new"])
    processing_count = len([o for o in orders if o["status"] == "processing"])
    confirmed_count = len([o for o in orders if o["status"] == "confirmed"])
    completed_count = len([o for o in orders if o["status"] == "completed"])
    cancelled_count = len([o for o in orders if o["status"] == "cancelled"])
    
    text = "📋 **Управление заказами**\n\n"
    text += "**Статистика:**\n"
    text += f"🆕 Новых: {new_count}\n"
    text += f"⚙️ В обработке: {processing_count}\n"
    text += f"✅ Подтвержденных: {confirmed_count}\n"
    text += f"✔️ Выполненных: {completed_count}\n"
    text += f"❌ Отмененных: {cancelled_count}\n"
    text += f"📊 Всего заказов: {len(orders)}\n\n"
    
    # Последние 5 заказов
    if orders:
        text += "**Последние заказы:**\n"
        for order in sorted(orders, key=lambda x: x["created_at"], reverse=True)[:5]:
            created = datetime.fromisoformat(order["created_at"]).strftime("%d.%m %H:%M")
            status_emoji = {
                "new": "🆕",
                "processing": "⚙️",
                "confirmed": "✅",
                "completed": "✔️",
                "cancelled": "❌"
            }.get(order["status"], "📦")
            text += f"{status_emoji} #{order['order_id']} - {order['total']}₽ ({created})\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📋 Список заказов", callback_data="admin_orders_list_new"))
    keyboard.add(InlineKeyboardButton(text="🔍 Поиск заказа", callback_data="admin_order_search"))
    keyboard.add(InlineKeyboardButton(text="📊 Отчет по заказам", callback_data="admin_orders_report"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_orders_list_"))
async def admin_orders_list(callback: CallbackQuery):
    """Список заказов по статусу"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    status = callback.data.replace("admin_orders_list_", "")
    status_names = {
        "new": "🆕 Новые",
        "processing": "⚙️ В обработке",
        "confirmed": "✅ Подтвержденные",
        "completed": "✔️ Выполненные",
        "cancelled": "❌ Отмененные",
        "all": "📋 Все"
    }
    
    orders_data = load_orders()
    orders = orders_data.get("orders", [])
    
    if status != "all":
        orders = [o for o in orders if o["status"] == status]
    
    orders.sort(key=lambda x: x["created_at"], reverse=True)
    
    if not orders:
        await callback.message.edit_text(
            f"{status_names.get(status, 'Заказы')} не найдены",
            reply_markup=InlineKeyboardBuilder()
            .add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_orders"))
            .as_markup()
        )
        await callback.answer()
        return
    
    # Показываем первую страницу
    page = 0
    items_per_page = 5
    
    await show_orders_page(callback.message, page, orders, status)

async def show_orders_page(message, page, orders, status):
    """Показать страницу с заказами"""
    items_per_page = 5
    total_pages = (len(orders) + items_per_page - 1) // items_per_page
    
    start = page * items_per_page
    end = start + items_per_page
    current_orders = orders[start:end]
    
    status_names = {
        "new": "🆕 Новые",
        "processing": "⚙️ В обработке",
        "confirmed": "✅ Подтвержденные",
        "completed": "✔️ Выполненные",
        "cancelled": "❌ Отмененные",
        "all": "📋 Все заказы"
    }
    
    text = f"{status_names.get(status, 'Заказы')} (страница {page + 1}/{total_pages})\n\n"
    
    for order in current_orders:
        created = datetime.fromisoformat(order["created_at"]).strftime("%d.%m.%Y %H:%M")
        status_emoji = {
            "new": "🆕",
            "processing": "⚙️",
            "confirmed": "✅",
            "completed": "✔️",
            "cancelled": "❌"
        }.get(order["status"], "📦")
        
        text += f"{status_emoji} **Заказ #{order['order_id']}**\n"
        text += f"   👤 {order['user_name']}\n"
        text += f"   💰 {order['total']}₽\n"
        text += f"   🕐 {created}\n\n"
    
    keyboard = InlineKeyboardBuilder()
    
    if page > 0:
        keyboard.add(InlineKeyboardButton(text="◀️ Пред", callback_data=f"orders_page_{status}_{page-1}"))
    if page < total_pages - 1:
        keyboard.add(InlineKeyboardButton(text="След ▶️", callback_data=f"orders_page_{status}_{page+1}"))
    
    keyboard.add(InlineKeyboardButton(text="🔍 Детали заказа", callback_data="admin_order_search"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад к списку", callback_data="admin_orders"))
    keyboard.adjust(2)
    
    await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("orders_page_"))
async def admin_orders_page(callback: CallbackQuery):
    """Пагинация списка заказов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    parts = callback.data.replace("orders_page_", "").split("_")
    status = parts[0]
    page = int(parts[1])
    
    orders_data = load_orders()
    orders = orders_data.get("orders", [])
    
    if status != "all":
        orders = [o for o in orders if o["status"] == status]
    
    orders.sort(key=lambda x: x["created_at"], reverse=True)
    
    await show_orders_page(callback.message, page, orders, status)
    await callback.answer()

@dp.callback_query(F.data == "admin_order_search")
async def admin_order_search_start(callback: CallbackQuery, state: FSMContext):
    """Поиск заказа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔍 **Поиск заказа**\n\n"
        "Введите номер заказа или ID пользователя:"
    )
    # Здесь нужно добавить состояние для поиска
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_order_"))
async def admin_order_status_change(callback: CallbackQuery):
    """Изменение статуса заказа администратором"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    parts = callback.data.replace("admin_order_", "").split("_")
    action = parts[0]
    order_id = int(parts[1])
    
    status_map = {
        "confirm": "confirmed",
        "processing": "processing",
        "completed": "completed",
        "cancel": "cancelled"
    }
    
    if action not in status_map:
        await callback.answer("Неизвестное действие!")
        return
    
    new_status = status_map[action]
    
    # Обновляем статус заказа
    orders_data = load_orders()
    order_found = False
    
    for order in orders_data["orders"]:
        if order["order_id"] == order_id:
            order["status"] = new_status
            order["updated_at"] = datetime.now().isoformat()
            order_found = True
            break
    
    if not order_found:
        await callback.answer("Заказ не найден!", show_alert=True)
        return
    
    save_orders(orders_data)
    
    # Уведомляем пользователя об изменении статуса
    for order in orders_data["orders"]:
        if order["order_id"] == order_id:
            try:
                status_text = get_status_text(new_status)
                await bot.send_message(
                    order["user_id"],
                    f"📦 **Статус заказа #{order_id} изменен**\n\n"
                    f"Новый статус: {status_text}"
                )
            except:
                pass
            break
    
    await callback.answer(f"Статус заказа #{order_id} изменен на {new_status}")
    
    # Обновляем сообщение
    await callback.message.edit_text(
        f"✅ Статус заказа #{order_id} изменен на {get_status_text(new_status)}"
    )

@dp.callback_query(F.data == "admin_orders_report")
async def admin_orders_report(callback: CallbackQuery):
    """Отчет по заказам"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    orders_data = load_orders()
    orders = orders_data.get("orders", [])
    
    if not orders:
        await callback.message.edit_text(
            "Нет данных для отчета",
            reply_markup=InlineKeyboardBuilder()
            .add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_orders"))
            .as_markup()
        )
        await callback.answer()
        return
    
    # Общая статистика
    total_sum = sum(o["total"] for o in orders)
    avg_sum = total_sum / len(orders) if orders else 0
    
    # Статистика по дням (последние 7 дней)
    from datetime import timedelta
    today = datetime.now().date()
    
    daily_stats = {}
    for i in range(7):
        day = today - timedelta(days=i)
        daily_stats[day.strftime("%d.%m")] = 0
    
    for order in orders:
        order_date = datetime.fromisoformat(order["created_at"]).date()
        days_ago = (today - order_date).days
        if days_ago < 7:
            daily_stats[order_date.strftime("%d.%m")] += order["total"]
    
    text = "📊 **Отчет по заказам**\n\n"
    text += f"**Общая статистика:**\n"
    text += f"• Всего заказов: {len(orders)}\n"
    text += f"• Общая сумма: {total_sum}₽\n"
    text += f"• Средний чек: {avg_sum:.2f}₽\n\n"
    
    text += "**Статистика по дням:**\n"
    for day, amount in sorted(daily_stats.items()):
        text += f"• {day}: {amount}₽\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_orders"))
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

# ==================== НАСТРОЙКА ПЛАТЕЖЕЙ ====================
@dp.callback_query(F.data == "admin_payment_settings")
async def admin_payment_settings(callback: CallbackQuery):
    """Настройки платежей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    payment_settings = load_payment_settings()
    payment_methods = payment_settings.get("payment_methods", [])
    
    text = "💳 **Настройки платежей**\n\n"
    
    if payment_methods:
        text += "**Способы оплаты:**\n"
        for i, method in enumerate(payment_methods, 1):
            default = "⭐ " if method.get("is_default") else ""
            text += f"{i}. {default}{method['name']}\n"
            text += f"   📝 {method['details'][:50]}...\n\n"
    else:
        text += "Способы оплаты не настроены\n\n"
    
    text += f"**По умолчанию:** {payment_settings.get('default_method', 'Не установлен')}"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="➕ Добавить способ", callback_data="payment_add"))
    
    if payment_methods:
        keyboard.add(InlineKeyboardButton(text="✏️ Редактировать", callback_data="payment_edit_list"))
        keyboard.add(InlineKeyboardButton(text="⭐ Установить по умолчанию", callback_data="payment_set_default"))
        keyboard.add(InlineKeyboardButton(text="🗑 Удалить способ", callback_data="payment_delete_list"))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "payment_add")
async def payment_add_start(callback: CallbackQuery, state: FSMContext):
    """Добавление способа оплаты"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💳 **Добавление способа оплаты**\n\n"
        "Введите **название** способа оплаты (например: Банковская карта, ЮMoney и т.д.):"
    )
    await state.set_state(AdminStates.waiting_for_payment_method_name)
    await callback.answer()

@dp.message(AdminStates.waiting_for_payment_method_name)
async def payment_add_name(message: Message, state: FSMContext):
    """Сохранение названия способа оплаты"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    await state.update_data(payment_name=message.text.strip())
    await message.answer(
        "📝 Введите **реквизиты** для оплаты:\n"
        "Например: номер карты, кошелек и т.д."
    )
    await state.set_state(AdminStates.waiting_for_payment_method_details)

@dp.message(AdminStates.waiting_for_payment_method_details)
async def payment_add_details(message: Message, state: FSMContext):
    """Сохранение реквизитов и добавление способа оплаты"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    data = await state.get_data()
    payment_name = data.get("payment_name")
    payment_details = message.text.strip()
    
    payment_settings = load_payment_settings()
    
    if "payment_methods" not in payment_settings:
        payment_settings["payment_methods"] = []
    
    # Проверяем, есть ли уже такой способ
    for method in payment_settings["payment_methods"]:
        if method["name"].lower() == payment_name.lower():
            await message.answer("❌ Способ оплаты с таким названием уже существует!")
            await state.clear()
            return
    
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
        f"✅ **Способ оплаты добавлен!**\n\n"
        f"Название: {payment_name}\n"
        f"Реквизиты: {payment_details}\n"
        f"{'⭐ Установлен по умолчанию' if is_default else ''}"
    )
    await state.clear()
    
    # Возвращаемся к настройкам
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Вернуться к настройкам", callback_data="admin_payment_settings"))
    await message.answer("Выберите действие:", reply_markup=keyboard.as_markup())

@dp.callback_query(F.data == "payment_edit_list")
async def payment_edit_list(callback: CallbackQuery):
    """Список для редактирования"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    payment_settings = load_payment_settings()
    payment_methods = payment_settings.get("payment_methods", [])
    
    if not payment_methods:
        await callback.answer("Нет способов оплаты!", show_alert=True)
        return
    
    keyboard = InlineKeyboardBuilder()
    
    for method in payment_methods:
        keyboard.add(InlineKeyboardButton(
            text=f"✏️ {method['name']}",
            callback_data=f"payment_edit_{method['name']}"
        ))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_payment_settings"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "Выберите способ оплаты для редактирования:",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("payment_edit_"))
async def payment_edit_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    method_name = callback.data.replace("payment_edit_", "")
    await state.update_data(edit_method_name=method_name)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📝 Изменить название", callback_data="payment_edit_name"))
    keyboard.add(InlineKeyboardButton(text="💰 Изменить реквизиты", callback_data="payment_edit_details"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="payment_edit_list"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        f"Редактирование: **{method_name}**\n\n"
        f"Что хотите изменить?",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "payment_edit_name")
async def payment_edit_name(callback: CallbackQuery, state: FSMContext):
    """Редактирование названия"""
    await callback.message.edit_text("Введите новое название:")
    await state.set_state(AdminStates.waiting_for_payment_method_name)
    await callback.answer()

@dp.callback_query(F.data == "payment_edit_details")
async def payment_edit_details(callback: CallbackQuery, state: FSMContext):
    """Редактирование реквизитов"""
    await callback.message.edit_text("Введите новые реквизиты:")
    await state.set_state(AdminStates.waiting_for_payment_method_details)
    await callback.answer()

@dp.message(AdminStates.waiting_for_payment_method_name)
async def payment_update_name(message: Message, state: FSMContext):
    """Обновление названия"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    data = await state.get_data()
    old_name = data.get("edit_method_name")
    new_name = message.text.strip()
    
    payment_settings = load_payment_settings()
    
    for method in payment_settings["payment_methods"]:
        if method["name"] == old_name:
            method["name"] = new_name
            if payment_settings.get("default_method") == old_name:
                payment_settings["default_method"] = new_name
            break
    
    save_payment_settings(payment_settings)
    
    await message.answer(f"✅ Название изменено на '{new_name}'")
    await state.clear()
    
    # Возвращаемся к настройкам
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Вернуться к настройкам", callback_data="admin_payment_settings"))
    await message.answer("Выберите действие:", reply_markup=keyboard.as_markup())

@dp.message(AdminStates.waiting_for_payment_method_details)
async def payment_update_details(message: Message, state: FSMContext):
    """Обновление реквизитов"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    data = await state.get_data()
    method_name = data.get("edit_method_name")
    new_details = message.text.strip()
    
    payment_settings = load_payment_settings()
    
    for method in payment_settings["payment_methods"]:
        if method["name"] == method_name:
            method["details"] = new_details
            break
    
    save_payment_settings(payment_settings)
    
    await message.answer(f"✅ Реквизиты обновлены!")
    await state.clear()
    
    # Возвращаемся к настройкам
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Вернуться к настройкам", callback_data="admin_payment_settings"))
    await message.answer("Выберите действие:", reply_markup=keyboard.as_markup())

@dp.callback_query(F.data == "payment_set_default")
async def payment_set_default(callback: CallbackQuery):
    """Установка способа по умолчанию"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    payment_settings = load_payment_settings()
    payment_methods = payment_settings.get("payment_methods", [])
    
    if not payment_methods:
        await callback.answer("Нет способов оплаты!", show_alert=True)
        return
    
    keyboard = InlineKeyboardBuilder()
    
    for method in payment_methods:
        default = "⭐ " if method.get("is_default") else ""
        keyboard.add(InlineKeyboardButton(
            text=f"{default}{method['name']}",
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
    """Сохранение способа по умолчанию"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    method_name = callback.data.replace("set_default_", "")
    
    payment_settings = load_payment_settings()
    
    # Сбрасываем флаг у всех
    for method in payment_settings["payment_methods"]:
        method["is_default"] = False
    
    # Устанавливаем новый
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

@dp.callback_query(F.data == "payment_delete_list")
async def payment_delete_list(callback: CallbackQuery):
    """Список для удаления"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    payment_settings = load_payment_settings()
    payment_methods = payment_settings.get("payment_methods", [])
    
    if not payment_methods:
        await callback.answer("Нет способов оплаты!", show_alert=True)
        return
    
    keyboard = InlineKeyboardBuilder()
    
    for method in payment_methods:
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
    """Удаление способа оплаты"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    method_name = callback.data.replace("delete_payment_", "")
    
    payment_settings = load_payment_settings()
    
    # Удаляем способ
    payment_settings["payment_methods"] = [
        m for m in payment_settings["payment_methods"] if m["name"] != method_name
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

# ==================== СТАТИСТИКА ====================
@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Статистика магазина"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    # Загружаем данные
    products = load_products()
    orders_data = load_orders()
    users_data = load_users()
    
    orders = orders_data.get("orders", [])
    users = users_data.get("users", [])
    
    # Статистика по товарам
    total_products = len(products)
    categories = len(get_categories())
    total_stock = sum(p.get("in_stock", 0) for p in products)
    total_value = sum(p["price"] * p.get("in_stock", 0) for p in products)
    
    # Статистика по заказам
    total_orders = len(orders)
    completed_orders = len([o for o in orders if o["status"] == "completed"])
    total_revenue = sum(o["total"] for o in orders if o["status"] == "completed")
    
    # Статистика по пользователям
    total_users = len(users)
    
    # Пользователи онлайн (за последние 24 часа)
    from datetime import timedelta
    day_ago = (datetime.now() - timedelta(days=1)).isoformat()
    active_users = len([u for u in users if u.get("last_seen", "") > day_ago])
    
    text = "📊 **Статистика магазина**\n\n"
    
    text += "**📦 Товары:**\n"
    text += f"• Всего товаров: {total_products}\n"
    text += f"• Категорий: {categories}\n"
    text += f"• Товаров в наличии: {total_stock} шт.\n"
    text += f"• Общая стоимость склада: {total_value}₽\n\n"
    
    text += "**📋 Заказы:**\n"
    text += f"• Всего заказов: {total_orders}\n"
    text += f"• Выполнено: {completed_orders}\n"
    text += f"• Выручка: {total_revenue}₽\n\n"
    
    text += "**👥 Пользователи:**\n"
    text += f"• Всего пользователей: {total_users}\n"
    text += f"• Активных за 24ч: {active_users}\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats"))
    keyboard.add(InlineKeyboardButton(text="📈 Детальная статистика", callback_data="admin_stats_detailed"))
    keyboard.add(InlineKeyboardButton(text="📊 Отчет по заказам", callback_data="admin_orders_report"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_stats_detailed")
async def admin_stats_detailed(callback: CallbackQuery):
    """Детальная статистика"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    products = load_products()
    orders_data = load_orders()
    orders = orders_data.get("orders", [])
    
    text = "📈 **Детальная статистика**\n\n"
    
    # Статистика по категориям
    text += "**📁 Товары по категориям:**\n"
    categories = {}
    for product in products:
        cat = product["category"]
        if cat not in categories:
            categories[cat] = {"count": 0, "stock": 0, "value": 0}
        categories[cat]["count"] += 1
        categories[cat]["stock"] += product.get("in_stock", 0)
        categories[cat]["value"] += product["price"] * product.get("in_stock", 0)
    
    for cat, stats in categories.items():
        text += f"• {cat}: {stats['count']} товаров, {stats['stock']} шт. на {stats['value']}₽\n"
    
    # Статистика по месяцам
    text += "\n**📅 Заказы по месяцам:**\n"
    monthly_stats = {}
    for order in orders:
        month = datetime.fromisoformat(order["created_at"]).strftime("%Y-%m")
        if month not in monthly_stats:
            monthly_stats[month] = {"count": 0, "total": 0}
        monthly_stats[month]["count"] += 1
        monthly_stats[month]["total"] += order["total"]
    
    for month, stats in sorted(monthly_stats.items(), reverse=True)[:6]:
        text += f"• {month}: {stats['count']} заказов, {stats['total']}₽\n"
    
    # Топ популярных товаров
    text += "\n**🔥 Популярные товары:**\n"
    product_sales = {}
    for order in orders:
        for item in order.get("items", []):
            product_name = item.get("product_name", "Неизвестно")
            if product_name not in product_sales:
                product_sales[product_name] = 0
            product_sales[product_name] += item.get("quantity", 0)
    
    top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5]
    for name, sales in top_products:
        text += f"• {name}: {sales} шт.\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_stats"))
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

# ==================== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ====================
@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    """Управление пользователями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    users_data = load_users()
    users = users_data.get("users", [])
    
    text = "👥 **Управление пользователями**\n\n"
    text += f"Всего пользователей: {len(users)}\n\n"
    
    # Последние зарегистрированные
    if users:
        text += "**Последние регистрации:**\n"
        for user in sorted(users, key=lambda x: x["registered_at"], reverse=True)[:5]:
            reg_date = datetime.fromisoformat(user["registered_at"]).strftime("%d.%m.%Y")
            name = user.get("first_name", "Без имени")
            username = f"(@{user['username']})" if user.get('username') else ""
            text += f"• {name} {username} - {reg_date}\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_users_list"))
    keyboard.add(InlineKeyboardButton(text="📊 Активность", callback_data="admin_users_activity"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_users_list")
async def admin_users_list(callback: CallbackQuery):
    """Список пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    users_data = load_users()
    users = users_data.get("users", [])
    
    if not users:
        await callback.message.edit_text(
            "Нет пользователей",
            reply_markup=InlineKeyboardBuilder()
            .add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users"))
            .as_markup()
        )
        await callback.answer()
        return
    
    # Показываем первую страницу
    page = 0
    items_per_page = 5
    
    await show_users_page(callback.message, page, users)

async def show_users_page(message, page, users):
    """Показать страницу с пользователями"""
    items_per_page = 5
    total_pages = (len(users) + items_per_page - 1) // items_per_page
    
    start = page * items_per_page
    end = start + items_per_page
    current_users = users[start:end]
    
    text = f"👥 **Список пользователей (страница {page + 1}/{total_pages})**\n\n"
    
    for user in current_users:
        last_seen = datetime.fromisoformat(user.get("last_seen", user["registered_at"])).strftime("%d.%m.%Y")
        name = user.get("first_name", "Без имени")
        username = f"@{user['username']}" if user.get('username') else "нет username"
        text += f"• {name}\n"
        text += f"  ID: {user['user_id']}\n"
        text += f"  Username: {username}\n"
        text += f"  Последний визит: {last_seen}\n\n"
    
    keyboard = InlineKeyboardBuilder()
    
    if page > 0:
        keyboard.add(InlineKeyboardButton(text="◀️ Пред", callback_data=f"users_page_{page-1}"))
    if page < total_pages - 1:
        keyboard.add(InlineKeyboardButton(text="След ▶️", callback_data=f"users_page_{page+1}"))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users"))
    keyboard.adjust(2)
    
    await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("users_page_"))
async def admin_users_page(callback: CallbackQuery):
    """Пагинация списка пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    page = int(callback.data.replace("users_page_", ""))
    users_data = load_users()
    users = users_data.get("users", [])
    
    await show_users_page(callback.message, page, users)
    await callback.answer()

@dp.callback_query(F.data == "admin_users_activity")
async def admin_users_activity(callback: CallbackQuery):
    """Статистика активности пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    users_data = load_users()
    users = users_data.get("users", [])
    
    from datetime import timedelta
    now = datetime.now()
    
    # Группировка по времени последнего визита
    today = len([u for u in users if datetime.fromisoformat(u.get("last_seen", u["registered_at"])).date() == now.date()])
    week = len([u for u in users if (now - datetime.fromisoformat(u.get("last_seen", u["registered_at"]))).days <= 7])
    month = len([u for u in users if (now - datetime.fromisoformat(u.get("last_seen", u["registered_at"]))).days <= 30])
    
    text = "📊 **Активность пользователей**\n\n"
    text += f"• Сегодня: {today}\n"
    text += f"• За неделю: {week}\n"
    text += f"• За месяц: {month}\n"
    text += f"• Всего: {len(users)}\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users"))
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

# ==================== НАСТРОЙКИ ====================
@dp.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    """Общие настройки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    text = "⚙️ **Настройки бота**\n\n"
    text += "Здесь можно настроить различные параметры работы бота.\n\n"
    text += "В разработке..."
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

# ==================== РАССЫЛКА ====================
@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Начало рассылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📨 **Создание рассылки**\n\n"
        "Отправьте сообщение, которое хотите разослать всем пользователям.\n"
        "Это может быть текст, фото, видео или документ."
    )
    await state.set_state(AdminStates.waiting_for_broadcast_message)
    await callback.answer()

@dp.message(AdminStates.waiting_for_broadcast_message)
async def admin_broadcast_get_message(message: Message, state: FSMContext):
    """Получение сообщения для рассылки"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    # Сохраняем сообщение
    await state.update_data(broadcast_message=message)
    
    # Получаем статистику
    users_data = load_users()
    users = users_data.get("users", [])
    
    # Запрашиваем подтверждение
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm"))
    keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel"))
    
    await message.answer(
        f"📨 **Предпросмотр рассылки**\n\n"
        f"Будет отправлено {len(users)} пользователям.\n\n"
        f"Сообщение готово к отправке. Нажмите 'Отправить' для начала рассылки.",
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(AdminStates.waiting_for_broadcast_confirm)

@dp.callback_query(F.data == "broadcast_confirm", AdminStates.waiting_for_broadcast_confirm)
async def admin_broadcast_confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и отправка рассылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    data = await state.get_data()
    broadcast_message = data.get("broadcast_message")
    
    await callback.message.edit_text("📨 Начинаю рассылку...")
    
    # Получаем список пользователей
    users_data = load_users()
    users = users_data.get("users", [])
    
    sent = 0
    failed = 0
    
    for user in users:
        try:
            # Копируем сообщение каждому пользователю
            await broadcast_message.copy_to(chat_id=user["user_id"])
            sent += 1
            
            # Задержка чтобы не забанили
            if sent % 10 == 0:
                await asyncio.sleep(1)
                
        except Exception as e:
            failed += 1
            logger.error(f"Ошибка отправки пользователю {user['user_id']}: {e}")
    
    await callback.message.edit_text(
        f"✅ **Рассылка завершена!**\n\n"
        f"📨 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}"
    )
    await state.clear()

@dp.callback_query(F.data == "broadcast_cancel", AdminStates.waiting_for_broadcast_confirm)
async def admin_broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    await callback.message.edit_text("❌ Рассылка отменена")
    await state.clear()
    await callback.answer()

# ==================== ОБРАБОТЧИК НЕИЗВЕСТНЫХ СООБЩЕНИЙ ====================
@dp.message()
async def handle_unknown(message: Message):
    """Обработчик неизвестных сообщений"""
    await message.answer(
        "Я не понимаю эту команду.\n"
        "Используйте /start для начала работы или /help для помощи."
    )

# ==================== ЗАПУСК БОТА ====================
async def main():
    """Главная функция запуска бота"""
    # Создаем файлы настроек при первом запуске
    if not os.path.exists(ADMINS_FILE):
        # Создаем первого администратора
        admins_data = {"admins": [FIRST_ADMIN_ID]}
        save_admins(admins_data)
        logger.info(f"Создан файл администраторов с ID {FIRST_ADMIN_ID}")
    
    if not os.path.exists(PAYMENT_SETTINGS_FILE):
        save_payment_settings({
            "payment_methods": [],
            "default_method": None
        })
        logger.info("Создан файл настроек платежей")
    
    if not os.path.exists(PRODUCTS_FILE):
        # Создаем тестовые товары
        default_products = [
            {"id": 1, "name": "Смартфон X", "price": 29990, "category": "Электроника", 
             "description": "Современный смартфон с отличной камерой", "in_stock": 10},
            {"id": 2, "name": "Ноутбук Pro", "price": 59990, "category": "Электроника", 
             "description": "Мощный ноутбук для работы и игр", "in_stock": 5},
            {"id": 3, "name": "Футболка", "price": 990, "category": "Одежда", 
             "description": "Хлопковая футболка", "in_stock": 50},
            {"id": 4, "name": "Джинсы", "price": 2990, "category": "Одежда", 
             "description": "Классические джинсы", "in_stock": 30},
            {"id": 5, "name": "Книга 'Python'", "price": 890, "category": "Книги", 
             "description": "Самоучитель по Python", "in_stock": 15},
        ]
        save_products(default_products)
        logger.info("Создан файл с тестовыми товарами")
    
    if not os.path.exists(USERS_FILE):
        save_users({"users": []})
        logger.info("Создан файл пользователей")
    
    if not os.path.exists(ORDERS_FILE):
        save_orders({"orders": [], "last_id": 0})
        logger.info("Создан файл заказов")
    
    # Проверяем первого администратора
    admins = load_admins()
    if FIRST_ADMIN_ID not in admins.get("admins", []):
        admins["admins"].append(FIRST_ADMIN_ID)
        save_admins(admins)
        logger.info(f"Добавлен первый администратор {FIRST_ADMIN_ID}")
    
    logger.info("=" * 50)
    logger.info("Бот запущен!")
    logger.info(f"Версия: 1.0.0")
    logger.info(f"Первый администратор ID: {FIRST_ADMIN_ID}")
    logger.info("=" * 50)

# ==================== УПРАВЛЕНИЕ ПЛАТЕЖАМИ ====================
@dp.callback_query(F.data == "admin_payment_settings")
async def admin_payment_settings(callback: CallbackQuery):
    """Настройки платежей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    payment_settings = load_payment_settings()
    payment_methods = payment_settings.get("payment_methods", [])
    
    text = "💳 **Настройки платежей**\n\n"
    
    if payment_methods:
        text += "**Способы оплаты:**\n"
        for i, method in enumerate(payment_methods, 1):
            default = "⭐ " if method.get("is_default") else ""
            text += f"{i}. {default}{method['name']}\n"
            text += f"   📝 {method['details'][:50]}...\n\n"
    else:
        text += "Способы оплаты не настроены\n\n"
    
    text += f"**По умолчанию:** {payment_settings.get('default_method', 'Не установлен')}"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="➕ Добавить способ", callback_data="payment_add"))
    
    if payment_methods:
        keyboard.add(InlineKeyboardButton(text="✏️ Редактировать", callback_data="payment_edit_list"))
        keyboard.add(InlineKeyboardButton(text="⭐ Установить по умолчанию", callback_data="payment_set_default"))
        keyboard.add(InlineKeyboardButton(text="🗑 Удалить способ", callback_data="payment_delete_list"))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "payment_add")
async def payment_add_start(callback: CallbackQuery, state: FSMContext):
    """Добавление способа оплаты"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💳 **Добавление способа оплаты**\n\n"
        "Введите **название** способа оплаты (например: Банковская карта, ЮMoney и т.д.):"
    )
    await state.set_state(AdminStates.waiting_for_payment_method_name)
    await callback.answer()

@dp.callback_query(F.data == "payment_edit_list")
async def payment_edit_list(callback: CallbackQuery, state: FSMContext):
    """Список для редактирования"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    payment_settings = load_payment_settings()
    payment_methods = payment_settings.get("payment_methods", [])
    
    if not payment_methods:
        await callback.answer("Нет способов оплаты!", show_alert=True)
        return
    
    keyboard = InlineKeyboardBuilder()
    
    for method in payment_methods:
        keyboard.add(InlineKeyboardButton(
            text=f"✏️ {method['name']}",
            callback_data=f"payment_edit_{method['name']}"
        ))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_payment_settings"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "Выберите способ оплаты для редактирования:",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("payment_edit_"))
async def payment_edit_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    method_name = callback.data.replace("payment_edit_", "")
    await state.update_data(edit_method_name=method_name)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📝 Изменить название", callback_data="payment_edit_name"))
    keyboard.add(InlineKeyboardButton(text="💰 Изменить реквизиты", callback_data="payment_edit_details"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="payment_edit_list"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        f"Редактирование: **{method_name}**\n\n"
        f"Что хотите изменить?",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "payment_edit_name")
async def payment_edit_name(callback: CallbackQuery, state: FSMContext):
    """Редактирование названия"""
    await callback.message.edit_text("Введите новое название:")
    await state.set_state(AdminStates.waiting_for_payment_method_name)
    await callback.answer()

@dp.callback_query(F.data == "payment_edit_details")
async def payment_edit_details(callback: CallbackQuery, state: FSMContext):
    """Редактирование реквизитов"""
    await callback.message.edit_text("Введите новые реквизиты:")
    await state.set_state(AdminStates.waiting_for_payment_method_details)
    await callback.answer()

@dp.callback_query(F.data == "payment_set_default")
async def payment_set_default(callback: CallbackQuery):
    """Установка способа по умолчанию"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    payment_settings = load_payment_settings()
    payment_methods = payment_settings.get("payment_methods", [])
    
    if not payment_methods:
        await callback.answer("Нет способов оплаты!", show_alert=True)
        return
    
    keyboard = InlineKeyboardBuilder()
    
    for method in payment_methods:
        default = "⭐ " if method.get("is_default") else ""
        keyboard.add(InlineKeyboardButton(
            text=f"{default}{method['name']}",
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
    """Сохранение способа по умолчанию"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    method_name = callback.data.replace("set_default_", "")
    
    payment_settings = load_payment_settings()
    
    # Сбрасываем флаг у всех
    for method in payment_settings["payment_methods"]:
        method["is_default"] = False
    
    # Устанавливаем новый
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

@dp.callback_query(F.data == "payment_delete_list")
async def payment_delete_list(callback: CallbackQuery):
    """Список для удаления"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    payment_settings = load_payment_settings()
    payment_methods = payment_settings.get("payment_methods", [])
    
    if not payment_methods:
        await callback.answer("Нет способов оплаты!", show_alert=True)
        return
    
    keyboard = InlineKeyboardBuilder()
    
    for method in payment_methods:
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
    """Удаление способа оплаты"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    method_name = callback.data.replace("delete_payment_", "")
    
    payment_settings = load_payment_settings()
    
    # Удаляем способ
    payment_settings["payment_methods"] = [
        m for m in payment_settings["payment_methods"] if m["name"] != method_name
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

@dp.message(AdminStates.waiting_for_payment_method_name)
async def payment_add_name(message: Message, state: FSMContext):
    """Сохранение названия способа оплаты"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    data = await state.get_data()
    edit_mode = "edit_method_name" in data
    
    if edit_mode:
        # Режим редактирования
        old_name = data.get("edit_method_name")
        new_name = message.text.strip()
        
        payment_settings = load_payment_settings()
        
        for method in payment_settings["payment_methods"]:
            if method["name"] == old_name:
                method["name"] = new_name
                if payment_settings.get("default_method") == old_name:
                    payment_settings["default_method"] = new_name
                break
        
        save_payment_settings(payment_settings)
        
        await message.answer(f"✅ Название изменено на '{new_name}'")
        await state.clear()
    else:
        # Режим добавления
        await state.update_data(payment_name=message.text.strip())
        await message.answer(
            "📝 Введите **реквизиты** для оплаты:\n"
            "Например: номер карты, кошелек и т.д."
        )
        await state.set_state(AdminStates.waiting_for_payment_method_details)

@dp.message(AdminStates.waiting_for_payment_method_details)
async def payment_add_details(message: Message, state: FSMContext):
    """Сохранение реквизитов и добавление способа оплаты"""
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа!")
        await state.clear()
        return
    
    data = await state.get_data()
    
    if "edit_method_name" in data:
        # Режим редактирования реквизитов
        method_name = data.get("edit_method_name")
        new_details = message.text.strip()
        
        payment_settings = load_payment_settings()
        
        for method in payment_settings["payment_methods"]:
            if method["name"] == method_name:
                method["details"] = new_details
                break
        
        save_payment_settings(payment_settings)
        
        await message.answer(f"✅ Реквизиты обновлены!")
        await state.clear()
    else:
        # Режим добавления нового способа
        payment_name = data.get("payment_name")
        payment_details = message.text.strip()
        
        payment_settings = load_payment_settings()
        
        if "payment_methods" not in payment_settings:
            payment_settings["payment_methods"] = []
        
        # Проверяем, есть ли уже такой способ
        for method in payment_settings["payment_methods"]:
            if method["name"].lower() == payment_name.lower():
                await message.answer("❌ Способ оплаты с таким названием уже существует!")
                await state.clear()
                return
        
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
            f"✅ **Способ оплаты добавлен!**\n\n"
            f"Название: {payment_name}\n"
            f"Реквизиты: {payment_details}\n"
            f"{'⭐ Установлен по умолчанию' if is_default else ''}"
        )
        await state.clear()
    
    # Возвращаемся к настройкам
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Вернуться к настройкам", callback_data="admin_payment_settings"))
    await message.answer("Выберите действие:", reply_markup=keyboard.as_markup())

# ==================== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ====================
@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    """Управление пользователями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    users_data = load_users()
    users = users_data.get("users", [])
    
    text = "👥 **Управление пользователями**\n\n"
    text += f"Всего пользователей: {len(users)}\n\n"
    
    # Последние зарегистрированные
    if users:
        text += "**Последние регистрации:**\n"
        for user in sorted(users, key=lambda x: x["registered_at"], reverse=True)[:5]:
            reg_date = datetime.fromisoformat(user["registered_at"]).strftime("%d.%m.%Y")
            name = user.get("first_name", "Без имени")
            username = f"(@{user['username']})" if user.get('username') else ""
            text += f"• {name} {username} - {reg_date}\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_users_list"))
    keyboard.add(InlineKeyboardButton(text="📊 Активность", callback_data="admin_users_activity"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_users_list")
async def admin_users_list(callback: CallbackQuery):
    """Список пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    users_data = load_users()
    users = users_data.get("users", [])
    
    if not users:
        await callback.message.edit_text(
            "Нет пользователей",
            reply_markup=InlineKeyboardBuilder()
            .add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users"))
            .as_markup()
        )
        await callback.answer()
        return
    
    # Показываем первую страницу
    page = 0
    items_per_page = 5
    
    await show_users_page(callback.message, page, users)

async def show_users_page(message, page, users):
    """Показать страницу с пользователями"""
    items_per_page = 5
    total_pages = (len(users) + items_per_page - 1) // items_per_page
    
    start = page * items_per_page
    end = start + items_per_page
    current_users = users[start:end]
    
    text = f"👥 **Список пользователей (страница {page + 1}/{total_pages})**\n\n"
    
    for user in current_users:
        reg_date = datetime.fromisoformat(user["registered_at"]).strftime("%d.%m.%Y %H:%M")
        last_seen = datetime.fromisoformat(user.get("last_seen", user["registered_at"])).strftime("%d.%m.%Y %H:%M")
        name = user.get("first_name", "Без имени")
        if user.get("last_name"):
            name += f" {user['last_name']}"
        username = f"@{user['username']}" if user.get('username') else "нет username"
        
        text += f"👤 **{name}**\n"
        text += f"  🆔 ID: `{user['user_id']}`\n"
        text += f"  📱 Username: {username}\n"
        text += f"  📅 Зарегистрирован: {reg_date}\n"
        text += f"  🕐 Последний визит: {last_seen}\n\n"
    
    keyboard = InlineKeyboardBuilder()
    
    if page > 0:
        keyboard.add(InlineKeyboardButton(text="◀️ Пред", callback_data=f"users_page_{page-1}"))
    if page < total_pages - 1:
        keyboard.add(InlineKeyboardButton(text="След ▶️", callback_data=f"users_page_{page+1}"))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users"))
    keyboard.adjust(2)
    
    await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("users_page_"))
async def admin_users_page(callback: CallbackQuery):
    """Пагинация списка пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    page = int(callback.data.replace("users_page_", ""))
    users_data = load_users()
    users = users_data.get("users", [])
    
    await show_users_page(callback.message, page, users)
    await callback.answer()

@dp.callback_query(F.data == "admin_users_activity")
async def admin_users_activity(callback: CallbackQuery):
    """Статистика активности пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    users_data = load_users()
    users = users_data.get("users", [])
    
    from datetime import timedelta
    now = datetime.now()
    
    # Группировка по времени последнего визита
    today = len([u for u in users if datetime.fromisoformat(u.get("last_seen", u["registered_at"])).date() == now.date()])
    week = len([u for u in users if (now - datetime.fromisoformat(u.get("last_seen", u["registered_at"]))).days <= 7])
    month = len([u for u in users if (now - datetime.fromisoformat(u.get("last_seen", u["registered_at"]))).days <= 30])
    
    # Активные (с корзиной)
    active_carts = len(user_carts)
    
    text = "📊 **Активность пользователей**\n\n"
    text += f"**По визитам:**\n"
    text += f"• Сегодня: {today}\n"
    text += f"• За неделю: {week}\n"
    text += f"• За месяц: {month}\n"
    text += f"• Всего: {len(users)}\n\n"
    text += f"**По корзинам:**\n"
    text += f"• Активных корзин: {active_carts}\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_users_activity"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback.answer()
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")

