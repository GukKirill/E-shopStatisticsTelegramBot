import sqlite3
import aiosqlite
from texthandler import statistics_msg_constructor
import os
from dotenv import load_dotenv


'''
DB structure:
dates - id: int, date: date
products - id: int, product: text
codes - id: int, code: text, title: text, product_id: int
orders - id: int, date_id: int, code_id: int, amount: int
mail - last_uid: int
'''

load_dotenv()
DB_FILE = os.getenv('DB_FILE')


class FromMailDBHandler:
    tables_creation = ('dates (id INTEGER PRIMARY KEY AUTOINCREMENT, date DATE)',
                       'products (id INTEGER PRIMARY KEY AUTOINCREMENT, product TEXT)',
                       'codes (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, title TEXT, product_id INTEGER)',
                       'orders(id INTEGER PRIMARY KEY AUTOINCREMENT, date_id INTEGER, code_id INTEGER, amount INTEGER)',
                       'mail (last_uid INTEGER)')

    def __init__(self):
        self.db = sqlite3.connect(DB_FILE)
        self.cursor = self.db.cursor()
        for table_creation in self.tables_creation:
            self.cursor.execute(f'''CREATE TABLE IF NOT EXISTS {table_creation}''')

    def close_connection(self) -> None:
        self.cursor.close()
        self.db.close()

    def set_mail_last_uid(self, new_uid: int) -> None:
        self.cursor.execute('''UPDATE mail SET last_uid = ?''', (new_uid, ))
        self.db.commit()

    def get_mail_last_uid(self) -> int:
        self.cursor.execute('''SELECT last_uid FROM mail''')
        uid = self.cursor.fetchall()
        if uid:
            return uid[0][0]
        else:
            self.set_mail_start_uid()
            return 1  # self.get_mail_last_uid() should I use recursive function???

    def set_mail_start_uid(self) -> None:
        self.cursor.execute('''INSERT INTO mail (last_uid) VALUES (?)''', (1, ))
        self.db.commit()

    def date_check(self, date: str) -> int:
        self.cursor.execute('''SELECT id, date FROM dates WHERE date = ?''', (date,))
        date_info = self.cursor.fetchall()
        if date_info:
            return date_info[0][0]
        else:
            self.cursor.execute('''INSERT INTO dates (date) VALUES (?)''', (date,))
            self.db.commit()
            return self.date_check(date=date)

    def product_check(self, product: str) -> int:
        self.cursor.execute('''SELECT id, product FROM products WHERE product = ?''', (product,))
        product_info = self.cursor.fetchall()
        if product_info:
            return product_info[0][0]
        else:
            self.cursor.execute('''INSERT INTO products (product) VALUES (?)''', (product,))
            self.db.commit()
            return self.product_check(product=product)

    def code_check(self, code: str, title: str, product_id: int) -> int:
        self.cursor.execute('''SELECT id, code, title FROM codes WHERE code = ?''', (code,))
        code_info = self.cursor.fetchall()
        if code_info:
            if code_info[0][2] != title:
                self.cursor.execute('''UPDATE codes SET title = ? WHERE code = ?''', (title, code))
                self.db.commit()
            return code_info[0][0]
        else:
            self.cursor.execute('''INSERT INTO codes (code, title, product_id) VALUES (?, ?, ?)''',
                                (code, title, product_id))
            self.db.commit()
            return self.code_check(code=code, title=title, product_id=product_id)

    def insert_new_data(self, date: str, product: str, code: str, title: str, amount: int) -> None:
        date_id = self.date_check(date=date)
        product_id = self.product_check(product=product)
        code_id = self.code_check(code=code, title=title, product_id=product_id)
        self.cursor.execute('''INSERT INTO orders (date_id, code_id, amount) VALUES (?, ?, ?)''',
                            (date_id, code_id, amount))
        self.db.commit()


class IntoTelegramDBHandler:
    db = None
    cursor = None

    async def connection(self) -> None:
        self.db = await aiosqlite.connect(DB_FILE)
        self.cursor = await self.db.cursor()

    async def close_connection(self) -> None:
        await self.cursor.close()
        await self.db.close()

    async def get_products_list(self) -> list[tuple[int, str]]:
        await self.connection()
        await self.cursor.execute('''SELECT id, product FROM products ORDER BY product''')
        data = await self.cursor.fetchall()
        products_list = list()
        if data:
            for product in data:
                products_list.append((product[0], product[1]))
        await self.close_connection()
        return products_list

    async def get_statistics(self, period: list[str], product_id: list[int]) -> str:
        await self.connection()
        await self.cursor.execute(
            '''
            SELECT codeC, titleC, COUNT(codeC) AS ccC, SUM(amountO) AS saO 
            FROM 
            (SELECT dates.date, orders.amount AS amountO, orders.code_id AS code_idO
             FROM orders 
             JOIN dates 
             ON orders.date_id = dates.id 
             WHERE dates.date BETWEEN ? AND ?) AS ordersO
            JOIN 
            (SELECT codes.id AS idC, codes.code AS codeC, codes.title AS titleC, products.product
             FROM codes 
             JOIN products 
             ON codes.product_id=products.id
             WHERE codes.product_id = ?) AS codesC
            ON ordersO.code_idO = codesC.idC
            GROUP BY codeC 
            ORDER BY ccC DESC, saO DESC
            ''',
            (period[0], period[1], product_id))
        data = await self.cursor.fetchall()
        await self.cursor.execute('''SELECT product FROM products WHERE id = ?''', (product_id, ))
        product_title = await self.cursor.fetchall()
        await self.close_connection()
        data = list(data)
        product_title = list(product_title)
        text = statistics_msg_constructor(data, product_title[0][0])
        return text
