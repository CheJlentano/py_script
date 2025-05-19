import os
import re
import time
from ftplib import FTP_TLS, FTP

# === Настройки ===
FTPS_HOST = 'ftp.dlptest.com'
FTPS_PORT = 21
USERNAME = 'dlpuser'
PASSWORD = 'rNrKYTX9g7z3RgJRmxWuGHbeu'

REMOTE_DIR = '/'
LOCAL_DIR = r'C:\Test_FTPS'

Z_PREFIX = 'ABC01'  # переменная z в новом имени

SLEEP_INTERVAL_SECONDS = 2 * 60  # 15 минут

# Регулярное выражение для поиска нужных файлов
pattern = re.compile(r'^(\d+)_(\d{4})-(\d{2})-(\d{2})_(\d{2})_(\d{2})_(\d{2})\.wav$')

class Explicit_FTP_TLS(FTP_TLS):
    def ntransfercmd(self, cmd, rest=None):
        conn, size = FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn,
                                            server_hostname=self.host,
                                            session=self.sock.session)
        return conn, size

def connect_ftps():
    ftps = Explicit_FTP_TLS()
    ftps.connect(FTPS_HOST, FTPS_PORT)
    ftps.login(USERNAME, PASSWORD)
    ftps.prot_p()  # переключение в защищённый режим передачи данных
    return ftps

def list_remote_files(ftps):
    ftps.cwd(REMOTE_DIR)
    files = ftps.nlst()
    return [f for f in files if pattern.match(f)]  # фильтрация по шаблону

def download_file(ftps, filename):
    local_path = os.path.join(LOCAL_DIR, filename)
    with open(local_path, 'wb') as f:
        ftps.retrbinary(f'RETR {filename}', f.write)
    remote_size = ftps.size(filename)  # получаем размер на сервере
    return local_path, remote_size

def check_size(local_path, remote_size):
    try:
        local_size = os.path.getsize(local_path)
        if local_size == remote_size:
            print(f"✅ Размер совпадает: {local_size} байт")
            return True
        else:
            print(f"❌ Размер не совпадает: локально {local_size}, на сервере {remote_size}")
            return False
    except Exception as e:
        print(f"Ошибка при проверке размера файла: {e}")
        return False

def rename_file(old_path):
    old_name = os.path.basename(old_path)
    m = pattern.match(old_name)
    if not m:
        print(f"❌ Пропущен (не совпадает с шаблоном): {old_name}")
        return None
    num, yyyy, dd, mm, hh, mi, ss = m.groups()
    new_name = f"{Z_PREFIX}_{num}-{dd}_{mm}_{yyyy}-{hh}_{mi}_{ss}.wav"
    new_path = os.path.join(LOCAL_DIR, new_name)
    os.rename(old_path, new_path)
    print(f"🔄 Переименован: {old_name} → {new_name}")
    return new_name

def delete_remote_files(ftps, files):
    ftps.cwd(REMOTE_DIR)
    for f in files:
        try:
            ftps.delete(f)
            print(f"🗑️ Удалён файл на сервере: {f}")
        except Exception as e:
            print(f"⚠️ Ошибка удаления файла {f}: {e}")

def main_loop():
    while True:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🔁 Новый цикл обработки")

        try:
            ftps = connect_ftps()
            print("🔐 Подключение к серверу FTPS успешно")
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            time.sleep(60)
            continue

        try:
            remote_files = list_remote_files(ftps)
            if not remote_files:
                print("📂 Нет подходящих файлов на сервере.")
            else:
                for file in remote_files:
                    print(f"⬇️ Загружается: {file}")
                    local_path, remote_size = download_file(ftps, file)

                    if check_size(local_path, remote_size):
                        renamed = rename_file(local_path)
                        if renamed:
                            delete_remote_files(ftps, [file])
                    else:
                        print(f"⚠️ Файл {file} пропущен из-за несоответствия размера")
        finally:
            ftps.quit()
            print("🔒 Соединение с сервером закрыто")

        print(f"⏳ Ожидание {SLEEP_INTERVAL_SECONDS // 60} минут...\n")
        time.sleep(SLEEP_INTERVAL_SECONDS)

if __name__ == '__main__':
    if not os.path.exists(LOCAL_DIR):
        os.makedirs(LOCAL_DIR)
    main_loop()
