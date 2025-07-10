import os
import shutil
import csv
import re
import psycopg2
import tkinter as tk
from tkinter import Tk, filedialog, messagebox, ttk
from math import radians


class GlobalMapperProjCreator:
    def __init__(self):
        self.root = Tk()
        self.root.title("Global Mapper Projection Creator")
        self.root.geometry("550x300")
        self.root.resizable(False, False)
        
        # Центрирование окна
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 550) // 2
        y = (screen_height - 300) // 2
        self.root.geometry(f"550x300+{x}+{y}")
        
        # Переменная для хранения выбранной версии
        self.gm_version = tk.StringVar(value="Global Mapper v25")
        
        # Создание интерфейса
        self.create_widgets()
        
        # Параметры подключения к БД
        self.db_params = {
            "host": "localhost",
            "port": "5432",
            "dbname": "gis",
            "user": "postgres",
            "password": "postgres"
        }
        
        # Запуск главного цикла
        self.root.mainloop()
    
    def create_widgets(self):
        # Заголовок
        header_label = tk.Label(
            self.root, 
            text="Global Mapper Projection Creator", 
            font=("Arial", 16, "bold")
        )
        header_label.pack(pady=20)
        
        # Выбор версии Global Mapper
        version_frame = tk.Frame(self.root)
        version_frame.pack(pady=10)
        
        version_label = tk.Label(
            version_frame, 
            text="Выберите версию Global Mapper:", 
            font=("Arial", 12)
        )
        version_label.pack(side=tk.LEFT, padx=10)
        
        version_combo = ttk.Combobox(
            version_frame, 
            textvariable=self.gm_version, 
            values=["Global Mapper v20", "Global Mapper v25", "Обе версии"],
            state="readonly",
            width=18
        )
        version_combo.pack(side=tk.LEFT, padx=10)
        
        # Кнопка запуска
        start_button = tk.Button(
            self.root, 
            text="Запустить", 
            command=self.start_process,
            font=("Arial", 12),
            width=15,
            height=2
        )
        start_button.pack(pady=20)
        
        # Статус
        self.status_label = tk.Label(
            self.root, 
            text="Готов к работе", 
            font=("Arial", 10),
            fg="green"
        )
        self.status_label.pack(pady=10)
    
    def update_status(self, message, color="black"):
        self.status_label.config(text=message, fg=color)
        self.root.update()
    
    def start_process(self):
        # Получение выбранной версии
        version = self.gm_version.get()
        self.update_status(f"Выбрана версия: {version}", "blue")
        
        # Выбор папки Global Mapper
        self.update_status("Выберите папку Global Mapper...", "blue")
        gm_folder = filedialog.askdirectory(title="Выберите папку Global Mapper")
        if not gm_folder:
            self.update_status("Выбор папки отменен", "red")
            return
        
        try:
            # Подключение к PostgreSQL
            self.update_status("Подключение к базе данных...", "blue")
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()
            
            # Извлечение данных
            self.update_status("Извлечение данных из базы...", "blue")
            cur.execute("""
                SELECT srid, proj4text, srtext 
                FROM public.spatial_ref_sys 
                WHERE auth_name = 'custom'
            """)
            
            # Создание структуры папок
            self.update_status("Создание структуры папок...", "blue")
            folder_structure = self.create_folder_structure(gm_folder)
            
            if version == "Обе версии":
                # Обработка для обеих версий
                for gm_ver in ["Global Mapper v20", "Global Mapper v25"]:
                    self.update_status(f"Обработка данных для {gm_ver}...", "blue")
                    
                    # Обработка данных для текущей версии
                    srid_data = self.process_db_data(cur, gm_ver)
                    
                    # Определение путей для текущей версии
                    ver_suffix = "GMv20" if gm_ver == "Global Mapper v20" else "GMv25"
                    custom_msk_path = os.path.join(folder_structure['custom_msk'], ver_suffix)
                    
                    # Создание временной структуры для текущей версии
                    temp_folder_structure = {
                        'proj_folder': folder_structure['proj_folder'],
                        'custom_msk': custom_msk_path,
                        'damp_folder': os.path.join(folder_structure['damp_folder'], ver_suffix)
                    }
                    
                    # Создание файлов проекций для текущей версии
                    self.update_status(f"Создание файлов проекций для {gm_ver}...", "blue")
                    msk_lines = self.create_projection_files(srid_data, temp_folder_structure)
                    
                    # Распределение файлов по папкам для текущей версии
                    self.update_status(f"Распределение файлов для {gm_ver}...", "blue")
                    self.distribute_files(temp_folder_structure)
                    
                    # Удаление общего файла MSK.prj для текущей версии
                    msk_file = os.path.join(temp_folder_structure['custom_msk'], "MSK.prj")
                    if os.path.exists(msk_file):
                        os.remove(msk_file)
            else:
                # Обработка для одной версии
                # Обработка данных
                self.update_status("Обработка данных...", "blue")
                srid_data = self.process_db_data(cur, version)
                
                # Создание файлов проекций
                self.update_status("Создание файлов проекций...", "blue")
                msk_lines = self.create_projection_files(srid_data, folder_structure)
                
                # Распределение файлов по папкам
                self.update_status("Распределение файлов по папкам...", "blue")
                self.distribute_files(folder_structure)
                
                # Удаление общего файла MSK.prj
                msk_file = os.path.join(folder_structure['custom_msk'], "MSK.prj")
                if os.path.exists(msk_file):
                    os.remove(msk_file)
            
            # Закрытие соединения с БД
            cur.close()
            conn.close()
            
            self.update_status("Обработка успешно завершена!", "green")
            messagebox.showinfo("Успех", "Обработка успешно завершена!")
            
        except Exception as e:
            self.update_status(f"Ошибка: {str(e)}", "red")
            messagebox.showerror("Ошибка", f"Произошла ошибка: {str(e)}")
    
    def process_db_data(self, cur, version):
        # Словарь для хранения трансформаций и параметров
        srid_data = {}
        
        # Обработка данных из БД
        for srid, proj4text, srtext in cur.fetchall():
            if not proj4text or not srtext:
                continue
                
            params = dict(re.findall(r'\+(.*?)=(.*?)(?:\s|$)', proj4text))
            
            # Проверка на валидность параметров
            if 'ellps' not in params or 'towgs84' not in params:
                continue
                
            try:
                # Парсинг параметров трансформации
                dx, dy, dz, rx, ry, rz, s = map(float, params['towgs84'].split(','))
                
                # Расчет параметров
                x_shift = f"{dx:.9f}"  # Точность до 9 знаков
                y_shift = f"{dy:.9f}"  # Точность до 9 знаков
                z_shift = f"{dz:.9f}"  # Точность до 9 знаков
                
                # Разные знаки для разных версий Global Mapper
                if version == "Global Mapper v20":
                    x_rot = f"{-1*(rx):.12f}"  # Инвертированный знак для v20
                    y_rot = f"{-1*(ry):.12f}"  # Инвертированный знак для v20
                    z_rot = f"{-1*(rz):.12f}"  # Инвертированный знак для v20
                else:  # Global Mapper v25
                    x_rot = f"{rx:.12f}"  # Обычный знак для v25
                    y_rot = f"{ry:.12f}"  # Обычный знак для v25
                    z_rot = f"{rz:.12f}"  # Обычный знак для v25
                
                scale = f"{s:.15f}"  # Точность до 15 знаков
                
                # Определение эллипсоида
                ellps = params['ellps']
                cur.execute("""
                    SELECT gm_ellipsoid_id, a, c 
                    FROM public.ellps_all 
                    WHERE name_el = %s
                """, (ellps,))
                ellps_data = cur.fetchone()
                if not ellps_data:
                    print(f"Данные эллипсоида отсутствуют, SRID={srid}")
                    continue
                    
                gm_ellipsoid_id, a, c = ellps_data
                
                # Определение названия датума
                cur.execute("""
                    SELECT name_d 
                    FROM public.datum_all 
                    WHERE datum = %s
                """, (f"+towgs84={params['towgs84']}",))
                datum_data = cur.fetchone()
                if datum_data:
                    datum_name = datum_data[0]
                else:
                    datum_name = f'Transformation_{srid}'
                    
                srid_data[srid] = {
                    'params': (x_shift, y_shift, z_shift, x_rot, y_rot, z_rot, scale),
                    'ellps': gm_ellipsoid_id,
                    'a': a,
                    'c': c,
                    'datum_name': datum_name,
                    'proj_params': params,
                    'srtext': srtext
                }
                
            except (ValueError, KeyError):
                continue
                
        return srid_data
    
    def create_folder_structure(self, gm_folder):
        # Создание основных папок
        proj_folder = os.path.join(gm_folder, "Proj")
        custom_msk = os.path.join(proj_folder, "custom_MSK")
        damp_folder = os.path.join(proj_folder, "damp_custom_MSK")
        
        os.makedirs(custom_msk, exist_ok=True)
        os.makedirs(damp_folder, exist_ok=True)
        
        # Базовая структура папок
        folders = {
            'GSK2011': ['3deg', '6deg'],
            'MSK': [],
            'SK42': ['3deg', '6deg'],
            'SK63': ['3deg', '6deg'],
            'SK95': ['3deg', '6deg'],
            'local': []
        }
        
        # Получение выбранной версии
        version = self.gm_version.get()
        
        # Создание структуры папок в зависимости от выбранной версии
        if version == "Обе версии":
            # Создаем папки GMv20 и GMv25 в custom_msk и damp_folder
            gm_versions = ["GMv20", "GMv25"]
            
            for gm_ver in gm_versions:
                # Создание папок в custom_msk
                gm_folder_path = os.path.join(custom_msk, gm_ver)
                os.makedirs(gm_folder_path, exist_ok=True)
                
                # Создание подпапок в папке версии
                for folder, subfolders in folders.items():
                    folder_path = os.path.join(gm_folder_path, folder)
                    os.makedirs(folder_path, exist_ok=True)
                    
                    for subfolder in subfolders:
                        subfolder_path = os.path.join(folder_path, subfolder)
                        os.makedirs(subfolder_path, exist_ok=True)
                
                # Создание папок в damp_folder
                damp_gm_folder_path = os.path.join(damp_folder, gm_ver)
                os.makedirs(damp_gm_folder_path, exist_ok=True)
                
                # Создание подпапок в папке версии в damp_folder
                for folder, subfolders in folders.items():
                    folder_path = os.path.join(damp_gm_folder_path, folder)
                    os.makedirs(folder_path, exist_ok=True)
                    
                    for subfolder in subfolders:
                        subfolder_path = os.path.join(folder_path, subfolder)
                        os.makedirs(subfolder_path, exist_ok=True)
            
            # Архивирование существующих файлов
            for gm_ver in gm_versions:
                gm_custom_msk = os.path.join(custom_msk, gm_ver)
                gm_damp_folder = os.path.join(damp_folder, gm_ver)
                self.archive_existing_files(gm_custom_msk, gm_damp_folder, folders)
                
            # Возвращаем структуру с учетом выбранной версии
            return {
                'proj_folder': proj_folder,
                'custom_msk': custom_msk,
                'damp_folder': damp_folder,
                'gm_versions': gm_versions
            }
        else:
            # Для одной версии (v20 или v25)
            gm_ver = "GMv20" if version == "Global Mapper v20" else "GMv25"
            
            # Создание папки версии в custom_msk
            gm_folder_path = os.path.join(custom_msk, gm_ver)
            os.makedirs(gm_folder_path, exist_ok=True)
            
            # Создание подпапок в папке версии
            for folder, subfolders in folders.items():
                folder_path = os.path.join(gm_folder_path, folder)
                os.makedirs(folder_path, exist_ok=True)
                
                for subfolder in subfolders:
                    subfolder_path = os.path.join(folder_path, subfolder)
                    os.makedirs(subfolder_path, exist_ok=True)
            
            # Создание папки версии в damp_folder
            damp_gm_folder_path = os.path.join(damp_folder, gm_ver)
            os.makedirs(damp_gm_folder_path, exist_ok=True)
            
            # Создание подпапок в папке версии в damp_folder
            for folder, subfolders in folders.items():
                folder_path = os.path.join(damp_gm_folder_path, folder)
                os.makedirs(folder_path, exist_ok=True)
                
                for subfolder in subfolders:
                    subfolder_path = os.path.join(folder_path, subfolder)
                    os.makedirs(subfolder_path, exist_ok=True)
            
            # Архивирование существующих файлов
            self.archive_existing_files(gm_folder_path, damp_gm_folder_path, folders)
            
            # Возвращаем структуру с учетом выбранной версии
            return {
                'proj_folder': proj_folder,
                'custom_msk': gm_folder_path,  # Изменяем путь к custom_msk на путь к папке версии
                'damp_folder': damp_gm_folder_path,  # Изменяем путь к damp_folder на путь к папке версии
                'gm_versions': [gm_ver]
            }
    
    def archive_existing_files(self, custom_msk, damp_folder, folders):
        """Архивирует существующие файлы из custom_msk в damp_folder"""
        self.update_status("Архивирование существующих файлов...", "blue")
        
        # Архивирование файлов из корня custom_msk
        for f in os.listdir(custom_msk):
            if f.endswith(".prj") and not os.path.isdir(os.path.join(custom_msk, f)):
                src = os.path.join(custom_msk, f)
                dst = os.path.join(damp_folder, f)
                try:
                    shutil.copy2(src, dst)  # Копируем файл вместо перемещения
                    os.remove(src)  # Затем удаляем оригинал
                except Exception as e:
                    print(f"Ошибка при архивировании файла {f}: {str(e)}")
        
        # Архивирование файлов из подпапок
        for folder, subfolders in folders.items():
            custom_folder = os.path.join(custom_msk, folder)
            damp_folder_path = os.path.join(damp_folder, folder)
            
            # Если папка существует
            if os.path.exists(custom_folder) and os.path.isdir(custom_folder):
                # Архивирование файлов из основной папки
                for f in os.listdir(custom_folder):
                    if f.endswith(".prj") and not os.path.isdir(os.path.join(custom_folder, f)):
                        src = os.path.join(custom_folder, f)
                        dst = os.path.join(damp_folder_path, f)
                        try:
                            shutil.copy2(src, dst)
                            os.remove(src)
                        except Exception as e:
                            print(f"Ошибка при архивировании файла {folder}/{f}: {str(e)}")
                
                # Архивирование файлов из подпапок
                for subfolder in subfolders:
                    custom_subfolder = os.path.join(custom_folder, subfolder)
                    damp_subfolder = os.path.join(damp_folder_path, subfolder)
                    
                    if os.path.exists(custom_subfolder) and os.path.isdir(custom_subfolder):
                        for f in os.listdir(custom_subfolder):
                            if f.endswith(".prj"):
                                src = os.path.join(custom_subfolder, f)
                                dst = os.path.join(damp_subfolder, f)
                                try:
                                    shutil.copy2(src, dst)
                                    os.remove(src)
                                except Exception as e:
                                    print(f"Ошибка при архивировании файла {folder}/{subfolder}/{f}: {str(e)}")
    
    def create_projection_files(self, srid_data, folder_structure):
        custom_msk = folder_structure['custom_msk']
        
        # Создание MSK.prj
        msk_file = os.path.join(custom_msk, "MSK.prj")
        msk_lines = []
        
        # Группировка трансформаций
        transformation_groups = {}
        group_counter = 1
        for srid, data in srid_data.items():
            trans_key = data['params']
            if trans_key not in transformation_groups:
                transformation_groups[trans_key] = group_counter
                group_counter += 1
                
        # Маппинг старых имен трансформаций к новым
        name_mapping = {}
        for srid, data in srid_data.items():
            trans_key = data['params']
            group_num = transformation_groups[trans_key]
            name_mapping[f'Transformation_{srid}'] = f'Transformation_{group_num}'
            
        # Формирование строк проекций
        for srid, data in srid_data.items():
            try:
                k = float(data['proj_params'].get('k', 1))
                lon_0 = float(data['proj_params'].get('lon_0', 0))
                lat_0 = float(data['proj_params'].get('lat_0', 0))
                x_0 = float(data['proj_params'].get('x_0', 0))
                y_0 = float(data['proj_params'].get('y_0', 0))
            except ValueError:
                continue
                
            # Определение параметров эллипсоида
            a = data['a']
            c = data['c']
            
            # Переименование Transformation_'srid' на общее значение
            group_num = transformation_groups[data['params']]
            datum_name = data['datum_name']
            
            # Получение параметров трансформации для текущего SRID
            x_shift, y_shift, z_shift, x_rot, y_rot, z_rot, scale = data['params']
            
            # Формирование строки проекции
            proj_line = f'''PROJCS["Transverse_Mercator",GEOGCS["{datum_name}",DATUM["{datum_name}",SPHEROID["{data['ellps']}",{a},{c}],TOWGS84[{x_shift},{y_shift},{z_shift},{x_rot},{y_rot},{z_rot},{scale}]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]],PROJECTION["Transverse_Mercator"],PARAMETER["scale_factor",{k}],PARAMETER["central_meridian",{lon_0}],PARAMETER["latitude_of_origin",{lat_0}],PARAMETER["false_easting",{x_0}],PARAMETER["false_northing",{y_0}],UNIT["Meter",1]]\n'''
            msk_lines.append((srid, proj_line))
            
        # Запись файла MSK.prj
        with open(msk_file, 'w', encoding='utf-8') as prj_file:
            prj_file.writelines([line for _, line in msk_lines])
            
        # Создание отдельных файлов .prj
        for srid, proj_line in msk_lines:
            # Получение значения srtext для названия файла
            srtext = srid_data[srid]['srtext']
            
            # Проверка допустимости символов в имени файла
            invalid_chars = '<>:"/\\|?*'
            filename = ''.join(c for c in srtext if c not in invalid_chars).strip() + ".prj"
            
            if not filename:  # Если имя файла пустое после очистки
                continue
                
            # Создание файла .prj
            file_path = os.path.join(custom_msk, filename)
            with open(file_path, 'w', encoding='utf-8') as prj_file:
                prj_file.write(proj_line)
                
        return msk_lines
    
    def distribute_files(self, folder_structure):
        custom_msk = folder_structure['custom_msk']
        
        # Получение списка всех .prj файлов
        prj_files = [f for f in os.listdir(custom_msk) if f.endswith(".prj") and f != "MSK.prj"]
        
        for filename in prj_files:
            source_path = os.path.join(custom_msk, filename)
            
            # Определение целевой папки
            target_folder = self.determine_target_folder(filename)
            target_path = os.path.join(custom_msk, target_folder)
            
            # Перемещение файла
            shutil.move(source_path, os.path.join(target_path, filename))
    
    def determine_target_folder(self, filename):
        # Определение целевой папки на основе имени файла
        if filename.startswith("GSK11"):
            if filename.endswith(".3.prj"):
                return os.path.join("GSK2011", "3deg")
            else:
                return os.path.join("GSK2011", "6deg")
        elif filename.startswith("MSK"):
            if filename == "MSK_gKrasnoyarsk.prj":
                return "local"
            else:
                return "MSK"
        elif filename.startswith("SK42"):
            if filename.endswith(".3.prj"):
                return os.path.join("SK42", "3deg")
            else:
                return os.path.join("SK42", "6deg")
        elif filename.startswith("SK63"):
            if filename.endswith(".6.prj"):
                return os.path.join("SK63", "6deg")
            else:
                return os.path.join("SK63", "3deg")
        elif filename.startswith("SK95"):
            if filename.endswith(".3.prj"):
                return os.path.join("SK95", "3deg")
            else:
                return os.path.join("SK95", "6deg")
        else:
            # Проверка на префиксы в середине имени
            if filename.startswith("USL_"):
                return "local"
            return "local"


if __name__ == "__main__":
    app = GlobalMapperProjCreator()