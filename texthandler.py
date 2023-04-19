from datetime import date
from aiogram.dispatcher.filters.state import StatesGroup, State
from site_fix import parse_line_before_fix


def handle_new_data(msg: str, msg_date: str) -> list[tuple[str, int]]:
    """ Replaces are based on the html-template of the e-mails from the shop-site. Should be parsing with bs4!!! """
    msg = msg.replace('<li><b><a href=', '').replace('</a></b> <b>', ' ').replace('</b></li', '')
    new_data = msg.split('>')
    new_data = [line for line in new_data if 'Арт.' in line]
    returned_data = list()

    for line in new_data:
        line_list = line.split(' ')
        try:
            amount = int(line_list[-1])
        except ValueError:
            continue
        parsed_fixed = parse_line_before_fix(line, msg_date, amount)  # for db re-filling only
        if parsed_fixed:
            returned_data.append(parsed_fixed)
            continue
        code_start = 0
        code_end = 0
        title_founded = False
        title = ''
        title_start = 0
        title_end = 0
        if '"' in line and line.count('"') == 2:
            title_founded = True

        for index, element in enumerate(line_list):
            if title_founded and '"' in element:
                if element.count('"') == 2:
                    title_start = index
                    title_end = index
                elif not title_start:
                    title_start = index
                else:
                    title_end = index

            elif 'Арт.' in element:
                if element == 'Арт.':
                    code_start = index
                    code_end = index + 1
                else:
                    code_start = index
                    code_end = index

        code = ''.join(line_list[code_start:code_end + 1])
        if title_founded:
            title = ' '.join(line_list[title_start:title_end + 1])
        product = line.replace(code, '').replace(title, '').replace(' x ' + str(amount), '') \
            .replace(' '.join(line_list[code_start:code_end + 1]), '')  # code may be in Арт.1234 or Арт. 1234 format
        product = product.strip()

        returned_data.append((msg_date, product, code, title, amount))
    return returned_data


def handle_entered(period: str, product: str, products_db_list: list[tuple[int, str]]) -> tuple:
    if product == 'product_all':
        formatted_product = [part[0] for part in products_db_list]
    else:
        product = product.replace('product_', '')
        formatted_product = [product]
    formatted_period = list()
    period_dict = {'period_all_the_time': [str(date(2020, 1, 1)),
                                           str(date.today())],
                   'period_this_year': [str(date(date.today().year, 1, 1)),
                                        str(date.today())],
                   'period_previous_year': [str(date(date.today().year-1, 1, 1)),
                                            str(date(date.today().year-1, 12, 31))]}
    if period in period_dict.keys():
        formatted_period = period_dict[period]
    elif period.count('-') == 1:  # if period is from user input
        period_1st_split = period.split('-')
        for date_u in period_1st_split:
            if date_u.count('.') == 2:
                date_u = date_u.strip()
                date_split = date_u.split('.')
                date_split.reverse()
                try:
                    new_date = date(int(date_split[0]),
                                    int(date_split[1]),
                                    int(date_split[2]))
                    formatted_period.append(str(new_date))
                except ValueError:
                    formatted_period = None
                    break
            else:
                formatted_period = None
                break
    else:
        formatted_period = None

    returned_data = (formatted_period, formatted_product)
    return returned_data


def statistics_msg_constructor(data: list, product: str) -> str:
    text = f'<b>{product}</b>\n'
    for code in data:
        text += f'<b>{code[0]}</b> {code[1]} - заказов: <b>{code[2]}</b>, единиц: {code[3]}\n'
    return text


class StatisticsState(StatesGroup):
    selected_period = State()
    selected_product = State()
    entered_period = State()
