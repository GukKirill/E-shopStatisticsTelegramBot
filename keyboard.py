from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton


class GlobalButtonsBuilder:
    def __init__(self):
        self.start = ReplyKeyboardMarkup(resize_keyboard=True)
        self.info = KeyboardButton('Информация')
        self.statistic = KeyboardButton('Статистика')
        self.update_statistic = KeyboardButton('Обновить статистику')
        self.start.add(self.info, self.statistic)
        self.start.add(self.update_statistic)

    def get_start(self) -> ReplyKeyboardMarkup:
        return self.start


class InlineButtonsBuilder:
    def __init__(self):
        self.periods = [['За все время', 'all_the_time'],
                        ['За этот год', 'this_year'],
                        ['За предыдущий год', 'previous_year'],
                        ['Пользовательский', 'user']]
        self.period_buttons = InlineKeyboardMarkup()
        self.products = None
        self.product_buttons = InlineKeyboardMarkup()

    def period_buttons_builder(self) -> InlineKeyboardMarkup:
        for button in self.periods:
            self.period_buttons.add(InlineKeyboardButton(button[0], callback_data=f'period_{button[1]}'))
        return self.period_buttons

    def products_buttons_builder(self, products: list) -> InlineKeyboardMarkup:
        self.products = products
        self.product_buttons.add(InlineKeyboardButton('Все', callback_data='product_all'))
        for product in self.products:
            self.product_buttons.add(InlineKeyboardButton(product[1], callback_data=f'product_{product[0]}'))
        return self.product_buttons
