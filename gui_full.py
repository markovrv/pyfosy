#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FOS Importer - Полнофункциональная версия GUI без потоков
Автор: Марков Р. В.
Версия: 3.0 (Полнофункциональная версия без потоков)
"""

import asyncio
import re
import sys
import tkinter as tk
import threading
import concurrent.futures
from tkinter import ttk, messagebox, filedialog
from pyppeteer import launch
from typing import List, Dict, Tuple
from dotenv import load_dotenv
import os

# Загружаем переменные из .env рядом с exe (PyInstaller) или со скриптом
def _app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(_app_dir(), '.env'))

# Путь к исполняемому файлу браузера (по умолчанию для Windows)
CHROME_PATH = os.getenv('CHROME_PATH', 'C:/Program Files/Google/Chrome/Application/chrome.exe')

class FOSImporter:
    def __init__(self, gui_instance=None):
        self.browser = None
        self.page = None
        self.debug = True
        self.complist = ''
        self.gui = gui_instance
        self.departments = []
        self.specialties = []
        self.subjects = []
        
    async def init_browser(self):
        """Инициализация браузера"""
        try:
            self.browser = await launch(
                executablePath=CHROME_PATH,
                headless=False,
                handleSIGINT=False,
                handleSIGTERM=False,
                handleSIGHUP=False,
                autoClose=False
            )
            self.page = await self.browser.newPage()
            await self.page.setViewport({'width': 1024, 'height': 700})
            await self.page.setUserAgent(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/106.0.0.0 YaBrowser/22.11.2.807 Yowser/2.5 Safari/537.36"
            )
        except Exception as e:
            raise Exception(f'Ошибка инициализации браузера: {str(e)}')

    async def navigate_to_site(self, credentials: Dict[str, str]):
        """Переход на сайт и авторизация"""
        await self._log('Открываем сайт...')
        await self.page.goto('https://iss.vyatsu.ru/kaf/', {'waitUntil': 'networkidle2'})

        await self._log('Авторизуемся...')
        await self._set_input_value('input[id="O60_id-inputEl"]', credentials['username'])
        await self._set_input_value('input[id="O6C_id-inputEl"]', credentials['password'])
        await self._click_element('a[id="O64_id"]')
        await self._wait(2000)

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

    async def get_departments(self):
        """Получение списка кафедр"""
        await self._log('Загружаем список кафедр...')
        await self._click_element('input[id="ODF_id-inputEl"]')
        await self._wait_for_selector('div[id="boundlist-1083-listEl"]')
        await self._wait(500)
        departments = await self._get_list_items('div[id="boundlist-1083-listEl"] li')
        await self._click_element('input[id="ODF_id-inputEl"]')
        self.departments = departments
        return departments

    async def select_department(self, department_index: int):
        """Выбор кафедры по индексу"""
        await self._log(f'Выбираем кафедру с индексом {department_index}...')
        await self._click_element('input[id="ODF_id-inputEl"]')
        await self._wait_for_selector('div[id="boundlist-1083-listEl"]')
        await self._wait(500)
        await self._click_element(f'div[id="boundlist-1083-listEl"] li:nth-child({department_index + 1})')
        await self._wait(500)

    async def get_specialties(self):
        """Получение списка специальностей"""
        await self._log('Загружаем список специальностей...')
        await self._wait(500)
        await self._click_element('input[id="OD0_id-inputEl"]')
        await self._wait_for_selector('div[id="boundlist-1086-listEl"]')
        await self._wait(500)
        specialties = await self._get_list_items('div[id="boundlist-1086-listEl"] li')
        await self._click_element('input[id="OD0_id-inputEl"]')
        self.specialties = specialties
        return specialties

    async def select_specialty(self, specialty_index: int):
        """Выбор специальности по индексу"""
        await self._log(f'Выбираем специальность с индексом {specialty_index}...')
        await self._click_element('input[id="OD0_id-inputEl"]')
        await self._wait_for_selector('div[id="boundlist-1086-listEl"]')
        await self._wait(500)
        await self._click_element(f'div[id="boundlist-1086-listEl"] li:nth-child({specialty_index + 1})')
        await self._wait(500)

    async def get_subjects(self):
        """Получение списка предметов"""
        await self._log('Получаем список предметов...')
        await self._wait(2000)
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
        self.subjects = subjects
        return subjects

    async def select_subject(self, subject_index: int):
        """Выбор предмета по индексу"""
        await self._log(f'Выбираем предмет с индексом {subject_index}...')
        await self._wait(800)
        await self._click_element(f'tr[id="gridview-1017-record-{subject_index}"]')
        await self._wait(800)
        await self._click_element('a[id="tab-1030"]')
        await self._wait(1500)
        await self._wait_for_selector('input[id="numberfield-1035-inputEl"]')

    async def return_to_main_tab(self):
        """Возврат на исходную вкладку после импорта/прерывания."""
        await self._log('Возвращаемся на исходную вкладку...')
        await self._click_element('a[id="tab-1015"]')
        await self._wait(1200)

    async def open_generator_popup(self):
        """Открытие popup-окна генератора файла."""
        await self._log('Открываем генератор файла...')
        await self.page.evaluate("""() => {
            window.open(
                'https://n8n.markovrv.ru/form/fef21f73-6b7e-4eef-b298-c56764bb2ba0',
                '_blank',
                'popup=yes,width=800,height=700,resizable=yes,scrollbars=yes'
            );
        }""")
        await self._wait(600)

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

    async def settings_competetions(self):
        """Ввод настроек компетенций"""
        # В GUI мы будем использовать значение 'auto' по умолчанию
        self.complist = 'auto'

    async def import_questions(self, file_path: str):
        """Импорт вопросов из GIFT-файла"""
        questions = await self._parse_gift_file(file_path)
        await self._log(f'Найдено {len(questions)} вопросов для импорта')
        
        for i, question in enumerate(questions, 1):
            await self._import_question(question, i, len(questions))

        return True
    
    async def _import_comp_string(self, comp_string):
        """Импорт списка компетенций вопроса"""
        elements = comp_string.split()
        
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
        
        comps = [replacements.get(element, element) for element in elements]
        
        if not comps:
            return
        
        comment = ''
        for _, comp in enumerate(comps, 1):
            if comp == 'У' or comp == 'Н':
                await self.select_answer_type_practice()
            else:
                await select_checkbox(self.page, comp)
                await self._wait(300)

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

            return questions

        except Exception as e:
            raise Exception(f'Ошибка чтения GIFT-файла: {str(e)}')

    async def _get_list_items(self, selector: str) -> List[str]:
        """Получение элементов списка"""
        return await self.page.evaluate(f'''() => {{
            const rows = document.querySelectorAll('{selector}')
            return Array.from(rows).map(row => row.innerText)
        }}''')

    async def _log(self, message: str):
        """Логирование сообщений"""
        if self.debug:
            print(message)
            if self.gui and hasattr(self.gui, 'status_var'):
                self.gui.status_var.set(message)
                self.gui.log_text.insert(tk.END, f"{message}\n")
                self.gui.log_text.see(tk.END)
                self.gui.root.update_idletasks()

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

class FOSGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FOS Importer - Полнофункциональная версия v3.0")
        self.root.geometry("450x750")
        
        # Флаги состояния
        self.authenticated = False
        self.department_selected = False
        self.specialty_selected = False
        self.subject_selected = False
        
        # Импортер
        self.importer = None
        self.current_operation = None
        self.async_loop = asyncio.new_event_loop()
        self.async_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.async_thread.start()
        
        # Создаем основной фрейм
        main_frame = ttk.Frame(root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Конфигурируем вес для адаптивности
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Заголовок с версией
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        title_label = ttk.Label(title_frame, text="FOS Importer", font=("Arial", 18, "bold"))
        title_label.pack()
        subtitle_label = ttk.Label(title_frame, text="Автоматизированный импорт вопросов ФОС в систему ISS ВятГУ", font=("Arial", 10))
        subtitle_label.pack()
        version_label = ttk.Label(title_frame, text="Версия 3.0 (Полнофункциональная версия без потоков)", font=("Arial", 9), foreground="gray")
        version_label.pack()
        
        # Ввод учетных данных
        login_frame = ttk.LabelFrame(main_frame, text="Учетные данные ВятГУ", padding="10")
        login_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        login_frame.columnconfigure(1, weight=1)
        login_frame.columnconfigure(3, weight=1)
        
        ttk.Label(login_frame, text="Логин:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.login_var = tk.StringVar(value=os.getenv('LOGIN', ''))
        login_entry = ttk.Entry(login_frame, textvariable=self.login_var)
        login_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Label(login_frame, text="Пароль:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.password_var = tk.StringVar(value=os.getenv('PASSWORD', ''))
        password_entry = ttk.Entry(login_frame, textvariable=self.password_var, show="*")
        password_entry.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Кнопка авторизации
        self.auth_btn = ttk.Button(login_frame, text="🔐 Авторизация", command=self.start_authentication)
        self.auth_btn.grid(row=0, column=4, padx=(10, 0))
        
        # Выбор файла
        file_frame = ttk.LabelFrame(main_frame, text="Выбор GIFT файла", padding="10")
        file_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="GIFT файл:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.file_path_var = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, width=50)
        file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        browse_btn = ttk.Button(file_frame, text="Обзор...", command=self.browse_file)
        browse_btn.grid(row=0, column=2)
        generate_btn = ttk.Button(file_frame, text="Сгенерировать файл", command=self.open_generator_file)
        generate_btn.grid(row=0, column=3, padx=(10, 0))
        
        # Информация о файле
        self.file_info_var = tk.StringVar(value="Файл не выбран")
        info_label = ttk.Label(file_frame, textvariable=self.file_info_var, foreground="blue")
        info_label.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(5, 0))
        
        # Выбор параметров
        params_frame = ttk.LabelFrame(main_frame, text="Параметры импорта (доступны после авторизации)", padding="10")
        params_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        params_frame.columnconfigure(1, weight=1)
        
        # Кафедра
        ttk.Label(params_frame, text="Кафедра:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.department_var = tk.StringVar()
        self.department_combo = ttk.Combobox(params_frame, textvariable=self.department_var, state="disabled")
        self.department_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.department_combo.bind('<<ComboboxSelected>>', self.on_department_selected)
        
        # Специальность
        ttk.Label(params_frame, text="Специальность:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.specialty_var = tk.StringVar()
        self.specialty_combo = ttk.Combobox(params_frame, textvariable=self.specialty_var, state="disabled")
        self.specialty_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.specialty_combo.bind('<<ComboboxSelected>>', self.on_specialty_selected)
        
        # Предмет
        ttk.Label(params_frame, text="Предмет:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.subject_var = tk.StringVar()
        self.subject_combo = ttk.Combobox(params_frame, textvariable=self.subject_var, state="disabled")
        self.subject_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.subject_combo.bind('<<ComboboxSelected>>', self.on_subject_selected)
        
        # Статус
        status_frame = ttk.LabelFrame(main_frame, text="Статус операции", padding="10")
        status_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar(value="Готов к работе")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, font=("Arial", 10, "bold"))
        status_label.grid(row=0, column=0, sticky=tk.W)
        
        # Прогресс
        self.progress_bar = ttk.Progressbar(status_frame, mode='determinate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=(15, 10))
        
        self.start_btn = ttk.Button(button_frame, text="🚀 Начать импорт", command=self.start_import, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(button_frame, text="⏹ Остановить", command=self.stop_import, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.test_btn = ttk.Button(button_frame, text="🧪 Тестовый режим", command=self.test_mode)
        self.test_btn.pack(side=tk.LEFT)
        
        # Логи
        log_frame = ttk.LabelFrame(main_frame, text="Журнал операций", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, height=12, width=80, font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Настройка веса для адаптивности
        main_frame.rowconfigure(6, weight=1)
        
        # Добавляем приветственное сообщение
        self.log_text.insert(tk.END, "FOS Importer v3.0 готов к работе\n")
        self.log_text.insert(tk.END, "1. Введите учетные данные\n")
        self.log_text.insert(tk.END, "2. Нажмите 'Авторизация'\n")
        self.log_text.insert(tk.END, "3. После авторизации выберите параметры\n")
        self.log_text.insert(tk.END, "4. Нажмите 'Начать импорт'\n\n")
    
    def start_authentication(self):
        """Начало процесса авторизации"""
        login = self.login_var.get()
        password = self.password_var.get()
        
        if not login or not password:
            messagebox.showwarning("Предупреждение", "Введите логин и пароль")
            return
        
        # Отключаем кнопку авторизации
        self.auth_btn.config(state=tk.DISABLED)
        self.progress_bar['value'] = 10
        
        # Запускаем авторизацию без использования потоков
        self.run_async_operation(self.authenticate_async(login, password))
    
    def run_async_operation(self, coro):
        """Запуск асинхронной операции в event loop"""
        future = asyncio.run_coroutine_threadsafe(coro, self.async_loop)

        def on_done(done_future):
            try:
                done_future.result()
            except Exception as e:
                self.root.after(0, lambda: self._handle_async_error(str(e)))

        future.add_done_callback(on_done)

    def _run_async_loop(self):
        """Фоновый цикл событий для всех операций pyppeteer."""
        asyncio.set_event_loop(self.async_loop)
        self.async_loop.run_forever()

    def _handle_async_error(self, error_msg):
        """Единая обработка ошибок фоновых async-задач."""
        self.status_var.set(f"❌ Ошибка: {error_msg}")
        self.auth_btn.config(state=tk.NORMAL)
    
    async def authenticate_async(self, login, password):
        """Асинхронная авторизация"""
        try:
            self.importer = FOSImporter(self)
            credentials = {'username': login, 'password': password}
            
            await self.importer.init_browser()
            self.progress_bar['value'] = 30
            
            await self.importer.navigate_to_site(credentials)
            self.progress_bar['value'] = 50
            
            await self.importer.select_fos_section()
            self.progress_bar['value'] = 70
            
            # Загружаем кафедры
            departments = await self.importer.get_departments()
            self.progress_bar['value'] = 100
            
            # Обновляем интерфейс в main thread
            self.root.after(0, lambda: self.update_department_list(departments))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: self.handle_auth_error(msg))
    
    def update_department_list(self, departments):
        """Обновление списка кафедр"""
        self.department_combo['values'] = departments
        self.department_combo['state'] = "readonly"
        self.authenticated = True
        self.status_var.set("✅ Авторизация успешна. Выберите кафедру.")
        self.log_text.insert(tk.END, "✅ Авторизация успешна. Кафедры загружены.\n")
        self.log_text.see(tk.END)
        self.auth_btn.config(state=tk.NORMAL)
        self.progress_bar['value'] = 0
    
    def handle_auth_error(self, error_msg):
        """Обработка ошибки авторизации"""
        self.status_var.set("❌ Ошибка авторизации")
        self.log_text.insert(tk.END, f"❌ Ошибка авторизации: {error_msg}\n")
        self.log_text.see(tk.END)
        messagebox.showerror("Ошибка", f"Ошибка авторизации: {error_msg}")
        self.auth_btn.config(state=tk.NORMAL)
        self.progress_bar['value'] = 0
    
    def on_department_selected(self, event):
        """Обработчик выбора кафедры"""
        if not self.authenticated:
            return
        
        dept_name = self.department_var.get()
        dept_index = self.department_combo['values'].index(dept_name)
        
        self.log_text.insert(tk.END, f"Выбрана кафедра: {dept_name}\n")
        self.log_text.see(tk.END)
        
        # Загружаем специальности
        self.run_async_operation(self.load_specialties_async(dept_index))
    
    async def load_specialties_async(self, dept_index):
        """Асинхронная загрузка специальностей"""
        try:
            await self.importer.select_department(dept_index)
            specialties = await self.importer.get_specialties()
            self.root.after(0, lambda: self.update_specialty_list(specialties))
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: self.handle_load_error("специальностей", msg))
    
    def update_specialty_list(self, specialties):
        """Обновление списка специальностей"""
        self.specialty_combo['values'] = specialties
        self.specialty_combo['state'] = "readonly"
        self.specialty_combo.set('')
        self.status_var.set("✅ Специальности загружены. Выберите специальность.")
        self.log_text.insert(tk.END, "✅ Специальности загружены.\n")
        self.log_text.see(tk.END)
    
    def on_specialty_selected(self, event):
        """Обработчик выбора специальности"""
        if not self.authenticated:
            return
        
        spec_name = self.specialty_var.get()
        spec_index = self.specialty_combo['values'].index(spec_name)
        
        self.log_text.insert(tk.END, f"Выбрана специальность: {spec_name}\n")
        self.log_text.see(tk.END)
        
        # Загружаем предметы
        self.run_async_operation(self.load_subjects_async(spec_index))
    
    async def load_subjects_async(self, spec_index):
        """Асинхронная загрузка предметов"""
        try:
            await self.importer.select_specialty(spec_index)
            subjects = await self.importer.get_subjects()
            self.root.after(0, lambda: self.update_subject_list(subjects))
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: self.handle_load_error("предметов", msg))
    
    def update_subject_list(self, subjects):
        """Обновление списка предметов"""
        subject_names = [s['name'] for s in subjects]
        self.subject_combo['values'] = subject_names
        self.subject_combo['state'] = "readonly"
        self.subject_combo.set('')
        self.status_var.set("✅ Предметы загружены. Выберите предмет.")
        self.log_text.insert(tk.END, "✅ Предметы загружены.\n")
        self.log_text.see(tk.END)
    
    def on_subject_selected(self, event):
        """Обработчик выбора предмета"""
        if not self.authenticated:
            return
        
        subj_name = self.subject_var.get()
        self.log_text.insert(tk.END, f"Выбран предмет: {subj_name}\n")
        self.log_text.see(tk.END)
        
        # Активируем кнопку импорта
        self.start_btn.config(state=tk.NORMAL)
        self.status_var.set("✅ Все параметры выбраны. Можно начать импорт.")
    
    def handle_load_error(self, what, error_msg):
        """Обработка ошибки загрузки данных"""
        self.log_text.insert(tk.END, f"❌ Ошибка загрузки {what}: {error_msg}\n")
        self.log_text.see(tk.END)
    
    def test_mode(self):
        """Тестовый режим для демонстрации"""
        # Заполняем тестовые данные
        if not self.login_var.get():
            self.login_var.set("test_user")
        if not self.password_var.get():
            self.password_var.set("test_password")
        
        # Симулируем загруженные данные
        self.authenticated = True
        
        self.department_combo['values'] = ['Кафедра информатики', 'Кафедра математики', 'Кафедра физики']
        self.department_combo['state'] = "readonly"
        self.department_combo.set('Кафедра информатики')
        
        self.specialty_combo['values'] = ['09.03.01 Информатика и ВТ', '01.03.02 Прикладная математика', '03.03.02 Физика']
        self.specialty_combo['state'] = "readonly"
        self.specialty_combo.set('09.03.01 Информатика и ВТ')
        
        self.subject_combo['values'] = ['Программирование', 'Базы данных', 'Веб-технологии']
        self.subject_combo['state'] = "readonly"
        self.subject_combo.set('Программирование')
        
        if not self.file_path_var.get():
            self.file_path_var.set("test.gift")
            self.file_info_var.set("✓ Тестовый файл (2 вопроса)")
        
        self.start_btn.config(state=tk.NORMAL)
        self.status_var.set("✅ Тестовый режим. Все параметры готовы к импорту.")
        
        self.log_text.insert(tk.END, "🧪 Тестовый режим активирован\n")
        self.log_text.insert(tk.END, "Все поля заполнены тестовыми данными\n")
        self.log_text.see(tk.END)
        
        messagebox.showinfo("Тестовый режим", "Все поля заполнены тестовыми данными.\nТеперь можно нажать 'Начать импорт'")
    
    def browse_file(self):
        """Выбор файла"""
        file_path = filedialog.askopenfilename(
            title="Выберите GIFT файл с вопросами",
            filetypes=[("GIFT files", "*.gift"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.update_file_info(file_path)

    def open_generator_file(self):
        """Открыть генератор файла в отдельном popup-окне браузера pyppeteer."""
        if not self.importer or not self.authenticated:
            messagebox.showwarning("Предупреждение", "Сначала выполните авторизацию")
            return
        self.run_async_operation(self.open_generator_popup_async())

    async def open_generator_popup_async(self):
        """Асинхронное открытие окна генератора."""
        try:
            await self.importer.open_generator_popup()
            self.root.after(0, lambda: self.status_var.set("✅ Генератор файла открыт в отдельном окне"))
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("Ошибка", f"Не удалось открыть генератор: {msg}"))
    
    def update_file_info(self, file_path):
        """Обновление информации о файле"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                question_count = sum(1 for line in lines if line.strip().startswith('::'))
                self.file_info_var.set(f"✓ Файл загружен. Найдено вопросов: {question_count}")
                self.log_text.insert(tk.END, f"Выбран файл: {os.path.basename(file_path)} ({question_count} вопросов)\n")
                self.log_text.see(tk.END)
        except Exception as e:
            self.file_info_var.set(f"❌ Ошибка чтения файла: {str(e)}")
    
    def start_import(self):
        """Начать импорт"""
        # Валидация
        login = self.login_var.get()
        password = self.password_var.get()
        file_path = self.file_path_var.get()
        
        if not self.authenticated:
            messagebox.showwarning("Предупреждение", "Сначала выполните авторизацию")
            return
            
        if not login or not password:
            messagebox.showwarning("Предупреждение", "Введите логин и пароль")
            return
            
        if not file_path:
            messagebox.showwarning("Предупреждение", "Выберите GIFT файл")
            return
        
        department = self.department_var.get()
        specialty = self.specialty_var.get()
        subject = self.subject_var.get()
        
        if not department or not specialty or not subject:
            messagebox.showwarning("Предупреждение", "Выберите кафедру, специальность и предмет")
            return
        
        # Отключаем кнопки
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.auth_btn.config(state=tk.DISABLED)
        self.test_btn.config(state=tk.DISABLED)
        
        # Запускаем импорт
        self.run_async_operation(self.import_async(file_path, subject))
    
    async def import_async(self, file_path, subject):
        """Асинхронный импорт"""
        try:
            if self.importer:
                # Выбираем предмет
                subject_names = [s['name'] for s in self.importer.subjects]
                subject_index = subject_names.index(subject) if subject in subject_names else 0
                
                await self.importer.select_subject(subject_index)
                await self.importer.settings_competetions()
                await self.importer.import_questions(file_path)
                
                self.root.after(0, lambda: self.import_completed(file_path))
            else:
                # Режим симуляции
                self.root.after(0, lambda: self.simulate_import_completed(file_path))
                
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: self.import_error(msg))
    
    def import_completed(self, file_path):
        """Завершение импорта"""
        self.status_var.set("✅ Импорт успешно завершен")
        if self.importer:
            self.run_async_operation(self.importer.return_to_main_tab())
        final_message = f"""
🎉 Импорт вопросов завершен успешно!

👤 Пользователь: {self.login_var.get()}
📂 Файл: {os.path.basename(file_path)}
🏢 Кафедра: {self.department_var.get()}
🎓 Специальность: {self.specialty_var.get()}
📚 Предмет: {self.subject_var.get()}

Все вопросы успешно импортированы в систему ФОС ВятГУ.
"""
        messagebox.showinfo("Успех", final_message)
        self.reset_buttons()
    
    def simulate_import_completed(self, file_path):
        """Завершение симуляции импорта"""
        self.status_var.set("✅ Симуляция импорта завершена")
        self.log_text.insert(tk.END, "✅ Симуляция импорта завершена (тестовый режим)\n")
        self.log_text.see(tk.END)
        messagebox.showinfo("Тестовый режим", "Симуляция импорта завершена успешно!")
        self.reset_buttons()
    
    def import_error(self, error_msg):
        """Ошибка импорта"""
        self.status_var.set("❌ Ошибка импорта")
        self.log_text.insert(tk.END, f"❌ Ошибка импорта: {error_msg}\n")
        self.log_text.see(tk.END)
        if self.importer:
            self.run_async_operation(self.importer.return_to_main_tab())
        messagebox.showerror("Ошибка", f"Ошибка импорта: {error_msg}")
        self.reset_buttons()
    
    def stop_import(self):
        """Остановить импорт"""
        self.status_var.set("⏹ Импорт остановлен пользователем")
        self.log_text.insert(tk.END, "⏹ Импорт остановлен пользователем\n")
        self.log_text.see(tk.END)
        if self.importer:
            self.run_async_operation(self.importer.return_to_main_tab())
        self.reset_buttons()
    
    def reset_buttons(self):
        """Сброс состояния кнопок"""
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.auth_btn.config(state=tk.NORMAL)
        self.test_btn.config(state=tk.NORMAL)
        self.progress_bar['value'] = 0

    def on_close(self):
        """Корректное закрытие браузера и async loop."""
        try:
            if self.importer and self.importer.browser:
                future = asyncio.run_coroutine_threadsafe(self.importer.close(), self.async_loop)
                try:
                    future.result(timeout=5)
                except concurrent.futures.TimeoutError:
                    pass
        except Exception:
            pass
        finally:
            try:
                self.async_loop.call_soon_threadsafe(self.async_loop.stop)
            except Exception:
                pass
            self.root.destroy()

def main():
    """Главная функция"""
    root = tk.Tk()
    
    # Настройка стиля
    try:
        style = ttk.Style()
        style.theme_use('clam')  # Используем современную тему
    except:
        pass  # Если тема недоступна, используем по умолчанию
    
    app = FOSGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    
    # Размещаем окно у правого края и по центру по вертикали
    root.update_idletasks()
    x = root.winfo_screenwidth() - root.winfo_width() - 20
    y = 10
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()

if __name__ == '__main__':
    main()