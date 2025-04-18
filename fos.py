import asyncio
import re
import getpass
from pyppeteer import launch
from typing import List, Dict, Tuple
from dotenv import load_dotenv
import os

# Загружаем переменные из .env файла
load_dotenv()

# Путь к исполняемому файлу браузера (по умолчанию для Windows)
CHROME_PATH = os.getenv('CHROME_PATH', 'C:/Program Files/Google/Chrome/Application/chrome.exe')
class FOSImporter:
    def __init__(self):
        self.browser = None
        self.page = None
        self.debug = True
        self.complist = ''

    async def init_browser(self):
        """Инициализация браузера"""
        self.browser = await launch( executablePath=CHROME_PATH, headless=False )

        self.page = await self.browser.newPage()
        await self.page.setViewport({'width': 1024, 'height': 700})
        await self.page.setUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/106.0.0.0 YaBrowser/22.11.2.807 Yowser/2.5 Safari/537.36"
        )

    async def get_credentials(self) -> Dict[str, str]:
        """Запрос учетных данных у пользователя"""
        print("\nВведите учетные данные для авторизации:")
        username = os.getenv('LOGIN', input("Логин: ").strip())
        password = os.getenv('PASSWORD', getpass.getpass("Пароль: ").strip())
        return {'username': username, 'password': password}

    async def navigate_to_site(self, credentials: Dict[str, str]):
        """Переход на сайт и авторизация"""
        await self._log('Открываем сайт...')
        await self.page.goto('https://iss.vyatsu.ru/kaf/', {'waitUntil': 'networkidle2'})

        await self._log('Авторизуемся...')
        await self._set_input_value('input[id="O60_id-inputEl"]', credentials['username'])
        await self._set_input_value('input[id="O6C_id-inputEl"]', credentials['password'])
        await self._click_element('a[id="O64_id"]')

    async def select_fos_section(self):
        """Выбор раздела ФОС"""
        await self._log('Выбираем раздел ФОС...')
        await self._wait(700)
        await self._click_element('input[id="O19_id-inputEl"]')
        await self._wait_for_selector('li[class="x-boundlist-item"]')
        await self._wait(500)
        await self._click_element('li[class="x-boundlist-item"]:nth-child(2)')
        await self._wait_for_selector('input[id="ODF_id-inputEl"]')
        await self._wait(300)

    async def select_department(self):
        """Выбор кафедры"""
        await self._log('Выбираем кафедру...')
        await self._click_element('input[id="ODF_id-inputEl"]')
        await self._wait_for_selector('div[id="boundlist-1083-listEl"]')
        await self._wait(1000)

        departments = await self._get_list_items('div[id="boundlist-1083-listEl"] li')
        selected = await self._select_from_list(departments, 'кафедры', 'DEPARTMENT')
        await self._click_element(f'div[id="boundlist-1083-listEl"] li:nth-child({selected})')
        await self._wait(1000)

    async def select_specialty(self):
        """Выбор специальности"""
        await self._log('Выбираем специальность...')
        await self._click_element('input[id="OD0_id-inputEl"]')
        await self._wait_for_selector('div[id="boundlist-1086-listEl"]')
        await self._wait(1000)

        specialties = await self._get_list_items('div[id="boundlist-1086-listEl"] li')
        selected = await self._select_from_list(specialties, 'специальности', "SPECIALTY")
        await self._click_element(f'div[id="boundlist-1086-listEl"] li:nth-child({selected})')
        await self._wait(1000)

    async def select_answer_type_practice(self):
        """Выбор практического типа вопроса"""

        element_id = await self.page.evaluate(f'''(text) => {{
            const labels = document.getElementsByTagName('label');
            for (let label of labels) {{
                if (label.innerHTML === text) {{
                    const nextElement = label.nextElementSibling;
                    if (nextElement) {{
                        if (nextElement.id) return nextElement.id;
                        else return null;
                    }} else return null;
                }}
            }}
            return null;
        }}''', "Вид вопроса")
        
        if element_id:
            await self._click_element(f'input[id="{element_id}-inputEl"]')
            await self._wait(300)

            list_id = await self.page.evaluate(f'''(text) => {{
                const listItems = document.getElementsByTagName('li');
                for (let li of listItems) {{
                    if (li.innerHTML === text) {{
                    const grandParent = li.parentElement?.parentElement;
                    return grandParent?.id || null;
                    }}
                }}
                return null;
            }}''', "Практический")

            if list_id:
                await self._click_element(f'div[id="{list_id}"] li:nth-child(2)')
                await self._wait(300)

    async def select_subject(self) -> Tuple[Dict, int]:
        """Выбор предмета и возврат (информация о предмете, его индекс)"""
        await self._log('Получаем список предметов...')
        subjects = await self.page.evaluate('''() => {
            const rows = document.querySelectorAll('tbody[id="gridview-1017-body"] tr')
            return Array.from(rows).map((row, index) => {
                const cols = row.querySelectorAll('div')
                return {
                    index: index,
                    name: cols[0].textContent.trim(),
                    fcount: cols[3].textContent.trim()
                }
            })
        }''')

        selected_index = await self._select_from_list(
            [s['name'] for s in subjects], 
            'предмета',
            "SUBJECT",
            show_index=True
        )
        
        selected_subject = subjects[selected_index]
        await self._log(f'Выбран предмет: {selected_subject["name"]}')
        return selected_index

    async def open_fos_tab(self):
        """Открытие вкладки с ФОС"""
        await self._wait(1000)
        subject_index = await self.select_subject()
        await self._click_element(f'tr[id="gridview-1017-record-{subject_index}"]')
        await self._wait(300)
        await self._click_element('a[id="tab-1030"]')
        await self._wait(1000)
        await self._wait_for_selector('input[id="numberfield-1035-inputEl"]')

    async def settings_competetions(self):
        """Ввод настроек компетенций"""
        variants = ['Считать компетенции каждого вопроса из файла', 'Ввести список компетенций самостоятельно', 'Не вводить компетенции']
        selected_variant = await self._select_from_list(
            variants, 
            'варианта',
            show_index=True
        )
        
        await self._log(f'Выбран вариант: {variants[selected_variant]}')

        if selected_variant == 0:
            self.complist = 'auto'
        elif selected_variant == 1:
            self.complist = input('Введите список компетенций через пробел: ')
        else:
            self.complist = 'none'

    async def import_questions(self):
        """Импорт вопросов из GIFT-файла"""
        file_path = input('Введите имя GIFT-файла (без расширения и точки): ') +  '.gift'
        questions = await self._parse_gift_file(file_path)
        await self._log(f'Найдено {len(questions)} вопросов для импорта')

        if input('Введите "start" для начала импорта: ').lower() != 'start':
            return False

        for i, question in enumerate(questions, 1):
            await self._import_question(question, i, len(questions))

        return True
    
    async def _import_comp_string(self, comp_string):
        """Импорт списка компетенций вопроса"""
        elements = comp_string.split()
        
        # Создаем словарь для замены сокращений
        replacements = {
            'В': 'Входной контроль',
            'Т': 'Текущий контроль',
            'О': 'Остаточные знания',
            'П': 'Промежуточная аттестация',
            'И': 'Итоговая аттестация',
        }

        hashes = {
            "З" : "#знания ",
            "У" : "#умения ",
            "Н" : "#навыки ",
        }
        
        # Заменяем элементы в массиве согласно словарю
        comps = [replacements.get(element, element) for element in elements]
        
        if not comps:
            return
        
        # Формируем комментарий из хештегов
        comment = ''
        for _, comp in enumerate(comps, 1):
            # Если указано, что вопрос практический
            if comp == 'У' or comp == 'Н':
                await self.select_answer_type_practice()
            else:
                await select_checkbox(self.page, comp)
                await self._wait(300)

            # Дублируем типы вопросов в комментарий в виде хештега
            if comp == 'У':
                comment += hashes['У']
            elif comp == 'Н':
                comment += hashes['Н']
            elif comp == 'З':
                comment += hashes['З']

        if comment:
            await self._set_textarea_value(comment, number=1)
            await self._wait(300)            

    async def _import_question(self, question: Dict, current: int, total: int):
        """Импорт одного вопроса"""
        await self._log(f'Импорт вопроса {current}/{total}')
        
        await press_button(self.page, 'Добавить вопрос')
        await self._wait(500)
        
        await self._set_textarea_value(question['text'])
        await self._wait(300)

        if self.complist == 'auto':
            await self._import_comp_string(question['title'])
        elif self.complist == 'none':
            pass
        else:
            await self._import_comp_string(self.complist)
        await self._wait(300)

        await press_button(self.page, 'Сохранить')
        await self._wait(1000)
        
        if len(question['options']) > 0:

            await press_button(self.page, 'Ответы')
            await self._wait(500)
            
            for j, option in enumerate(question['options'], 1):
                await self._import_answer_option(option, j)

            await self._wait(300)
            await press_button(self.page, 'Закрыть')
            await self._wait(1000)

    async def _import_answer_option(self, option: Dict, index: int):
        """Импорт варианта ответа"""
        await press_button(self.page, 'Добавить')
        await self._wait(500)
        
        await self._set_textarea_value(option['text'])
        await self._wait(300)
        
        if option['isCorrect']:
            await select_checkbox(self.page, 'Правильный ответ')
            await self._wait(300)
        
        await press_button(self.page, 'Сохранить')
        await self._wait(1000)

    async def _parse_gift_file(self, file_path: str) -> List[Dict]:
        """Парсинг GIFT-файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = file.read()
            
            lines = [line.strip() for line in data.split('\n') 
                    if line.strip() and not line.strip().startswith('//')]
            
            questions = []
            current_question = None
            
            for line in lines:
                if line.startswith('::'):
                    if current_question:
                        questions.append(current_question)
                    match = re.match(r'^::(.*?)::(.*?)\s*{', line)
                    if match:
                        current_question = {
                            'type': 'multiple',
                            'title': match.group(1).strip(),
                            'text': match.group(2).strip(),
                            'options': [],
                        }
                elif '=' in line or '~' in line:
                    option = line.strip()
                    current_question['options'].append({
                        'text': re.sub(r'^[=~%0-9]+', '', option).strip(),
                        'isCorrect': option.startswith('=')
                    })
            
            if current_question:
                questions.append(current_question)
            return questions[42:]
        except Exception as e:
            raise Exception(f'Ошибка чтения GIFT-файла: {str(e)}')

    async def _get_list_items(self, selector: str) -> List[str]:
        """Получение элементов списка"""
        return await self.page.evaluate(f'''() => {{
            const rows = document.querySelectorAll('{selector}')
            return Array.from(rows).map(row => row.innerText)
        }}''')

    async def _select_from_list(self, items: List[str], name: str, envcode: str = "", show_index: bool = False) -> int:
        """Выбор элемента из списка"""
        prompt = f'Выберите номер {name}:\n'
        prompt += '\n'.join(
            f'{i+1}. {item}' if not show_index else f'{i}. {item}' 
            for i, item in enumerate(items)
        )
        prompt += '\n'
        
        while True:
            try:
                selected = int(os.getenv(envcode, input(prompt)))
                if show_index:
                    if 0 <= selected < len(items):
                        return selected
                else:
                    if 1 <= selected <= len(items):
                        return selected
                print('Неверный номер, попробуйте еще раз')
            except ValueError:
                print('Пожалуйста, введите число')

    async def _log(self, message: str):
        """Логирование сообщений"""
        if self.debug:
            print(message)

    async def _wait(self, ms: int):
        """Ожидание в миллисекундах"""
        await asyncio.sleep(ms / 1000)

    async def _click_element(self, selector: str):
        """Клик по элементу"""
        await self.page.waitForSelector(selector)
        await self.page.click(selector)

    async def _wait_for_selector(self, selector: str):
        """Ожидание появления элемента"""
        await self.page.waitForSelector(selector)

    async def _set_input_value(self, selector: str, value: str):
        """Установка значения input"""
        await self.page.waitForSelector(selector)
        await self.page.evaluate(f'(val) => document.querySelector(`{selector}`).value = val', value)

    async def _set_textarea_value(self, value: str, number = 0):
        """Установка значения textarea"""
        await self.page.waitForSelector('textarea')
        await self.page.evaluate('(data) => document.querySelectorAll("textarea")[data[1]].value = data[0]', [value, number])

    async def close(self):
        """Закрытие браузера"""
        if self.browser:
            await self.browser.close()

async def select_checkbox(page, name: str):
    """Выбор чекбокса по тексту метки"""
    element_id = await page.evaluate(f'''(text) => {{
        const elems = document.querySelectorAll("label");
        const res = Array.from(elems).find(v => v.innerHTML == text);
        return res ? res.id.split('-')[0] : null;
    }}''', name)
    
    if element_id:
        await page.click(f'input[id="{element_id}-inputEl"]')

async def press_button(page, name: str):
    """Нажатие кнопки по тексту"""
    element_id = await page.evaluate(f'''(text) => {{
        const elems = document.querySelectorAll("span");
        const res = Array.from(elems).find(v => v.innerHTML == text);
        return res ? res.id.split('-')[0] : null;
    }}''', name)
    
    if element_id:
        await page.waitForSelector(f'a[id="{element_id}"]')
        await page.click(f'a[id="{element_id}"]')

async def main():
    importer = FOSImporter()
    try:
        credentials = await importer.get_credentials()
        await importer.init_browser()
        await importer.navigate_to_site(credentials)
        await importer.select_fos_section()
        await importer.select_department()
        await importer.select_specialty()
        await importer.open_fos_tab()

        while input('Вы хотите загрузить GIFT файл? (y/n): ').lower() != 'n':
            await importer.settings_competetions()
            await importer.import_questions()
            await importer._wait(1000)

    except Exception as e:
        print(f'\nОшибка: {str(e)}')
        await importer.close()
        print('\nЗавершение работы.')
        
    finally:
        await importer.close()
        print('\nЗавершение работы.')

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())