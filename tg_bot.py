import logging
import re
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from dotenv import load_dotenv
import paramiko
import psycopg2

load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
PASSWORD_ENTRY = 'password_entry'
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_name = os.getenv('DB_NAME')

(FIND_EMAILS, SAVE_EMAILS, FIND_PHONE_NUMBERS, SAVE_PHONE_NUMBERS) = range(4)

# Подключаем логирование
logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context):
    user = update.effective_user
    await update.message.reply_text(f'Привет {user.full_name}! Используйте /setup_ssh для настройки SSH подключения или /help для списка команд.')

async def help_command(update: Update, context):
    help_text = (
        "Доступные команды:\n"
        "/findEmails - Найти email адреса в тексте\n"
        "/findPhoneNumbers - Найти телефонные номера в тексте\n"
        "/get_repl_logs - Получить логи репликации PostgreSQL\n"
        "/setup_ssh - Настройка SSH подключения (введите данные в формате: IP PORT USERNAME PASSWORD)\n"
        "/get_release - Получить информацию о релизе системы\n"
        "/get_uname - Получить информацию об архитектуре, имени хоста и версии ядра\n"
        "/get_uptime - Получить информацию о времени работы системы\n"
        "/get_df - Получить информацию о состоянии файловой системы\n"
        "/get_free - Получить информацию о состоянии оперативной памяти\n"
        "/get_mpstat - Получить информацию о производительности системы\n"
        "/get_w - Получить информацию о работающих пользователях\n"
        "/get_auths - Получить последние 10 входов в систему\n"
        "/get_critical - Получить последние 5 критических событий\n"
        "/get_ps - Получить информацию о запущенных процессах\n"
        "/get_ss - Получить информацию об используемых портах\n"
        "/get_apt_list - Получить список установленных пакетов или информацию о конкретном пакете\n"
        "/get_services - Получить список запущенных сервисов\n"
        "Используйте /help для просмотра этого сообщения снова."
    )
    await update.message.reply_text(help_text)

def save_to_database(data_list, table_name, column_name):
    
    connection = psycopg2.connect(user=db_user, password=db_password, host=db_host, port=db_port, database=db_name)
    cursor = connection.cursor()
    try:
        for data in data_list:
            query = f"INSERT INTO {table_name} ({column_name}) VALUES (%s)"
            cursor.execute(query, (data,))
        connection.commit()
        return True
    except Exception as e:
        logger.error(f"Database error: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

async def setup_ssh_command(update: Update, context):
    await update.message.reply_text('Введите данные для SSH подключения в формате: IP PORT USERNAME PASSWORD')
    return 'ssh_setup'

async def findEmailsCommand(update: Update, context):
    await update.message.reply_text('Введите текст для поиска электронных адресов:')
    return FIND_EMAILS

async def findEmails(update: Update, context):
    user_input = update.message.text
    emailRegex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    emailList = emailRegex.findall(user_input)
    if not emailList:
        await update.message.reply_text('Электронные адреса не найдены')
        return ConversationHandler.END
    context.user_data['emails'] = emailList
    emails = '\n'.join([f'{i+1}. {email}' for i, email in enumerate(emailList)])
    await update.message.reply_text(emails)
    await update.message.reply_text('Хотите сохранить эти email в базу данных? Отправьте "да" или "нет" для продолжения.')
    return SAVE_EMAILS

async def saveEmails(update: Update, context):
    if update.message.text.lower() == 'да':
        if save_to_database(context.user_data.get('emails', []), 'email', 'email'): 
            await update.message.reply_text('Email адреса успешно сохранены.')
        else:
            await update.message.reply_text('Ошибка при сохранении.')
    else:
        await update.message.reply_text('Сохранение отменено.')
    return ConversationHandler.END

async def findPhoneNumbersCommand(update: Update, context):
    await update.message.reply_text('Введите текст для поиска телефонных номеров:')
    return FIND_PHONE_NUMBERS

async def findPhoneNumbers(update: Update, context):
    user_input = update.message.text
    phoneNumRegex = re.compile(r'(\+7|8)[- ]?(\(?\d{3}\)?[- ]?\d{3}[- ]?\d{2}[- ]?\d{2})')
    phoneNumberList = phoneNumRegex.findall(user_input)
    if not phoneNumberList:
        await update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END
    context.user_data['phone_numbers'] = [''.join(num) for num in phoneNumberList]  # Преобразование списка кортежей в список строк
    phoneNumbers = '\n'.join([f'{i+1}. {num}' for i, num in enumerate(context.user_data['phone_numbers'])])
    await update.message.reply_text(f'Найденные номера:\n{phoneNumbers}')
    await update.message.reply_text('Хотите сохранить эти номера телефонов в базу данных? Отправьте "да" или "нет" для продолжения.')
    return SAVE_PHONE_NUMBERS

async def savePhoneNumbers(update: Update, context):
    user_response = update.message.text.lower()
    if user_response == 'да':
        if save_to_database(context.user_data.get('phone_numbers', []), 'phone', 'phone'):
            await update.message.reply_text('Телефонные номера успешно сохранены в базу данных.')
        else:
            await update.message.reply_text('Ошибка при сохранении.')
    else:
        await update.message.reply_text('Сохранение отменено.')
    return ConversationHandler.END

async def get_email(update: Update, context):
    connection = psycopg2.connect(user=db_user, password=db_password, host=db_host, port=db_port, database=db_name)
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT email FROM email")
        emails = cursor.fetchall()
        if emails:
            email_text = '\n'.join([email[0] for email in emails])
            await safe_send_message(update, f"Сохраненные email адреса:\n{email_text}")
        else:
            await update.message.reply_text('В базе данных нет сохраненных email адресов.')
    finally:
        cursor.close()
        connection.close()

async def get_phone(update: Update, context):
    connection = psycopg2.connect(user=db_user, password=db_password, host=db_host, port=db_port, database=db_name)
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT phone FROM phone")
        phones = cursor.fetchall()
        if phones:
            phone_text = '\n'.join([phone[0] for phone in phones])
            await safe_send_message(update, f"Сохраненные телефонные номера:\n{phone_text}")
        else:
            await update.message.reply_text('В базе данных нет сохраненных телефонных номеров.')
    finally:
        cursor.close()
        connection.close()

async def verify_password_command(update: Update, context):
    await update.message.reply_text('Введите ваш пароль:')
    return PASSWORD_ENTRY

async def verify_password(update: Update, context):
    password = update.message.text
    # Регулярное выражение для проверки сложности пароля
    password_regex = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()])[A-Za-z\d!@#$%^&*()]{8,}$')
    if password_regex.match(password):
        await update.message.reply_text('Пароль сложный.')
    else:
        await update.message.reply_text('Пароль простой.')
    return ConversationHandler.END

async def ssh_setup(update: Update, context):
    text = update.message.text
    try:
        ip, port, username, password = text.split()
        # Пробуем подключиться с полученными данными для проверки их валидности
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, int(port), username, password, timeout=10)  # Таймаут для быстрой проверки
        client.close()
        context.user_data['ssh'] = {'ip': ip, 'port': int(port), 'username': username, 'password': password}
        await update.message.reply_text('Данные для подключения проверены и сохранены. Вы можете использовать команды мониторинга.')
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text('Ошибка ввода. Убедитесь, что вы ввели данные в правильном формате: IP PORT USERNAME PASSWORD')
        return 'ssh_setup'
    except Exception as e:
        await update.message.reply_text(f'Ошибка подключения: {str(e)}\nПроверьте введенные данные и попробуйте еще раз.')
        return 'ssh_setup'


def ssh_command(context, command):
    ssh_data = context.user_data.get('ssh', {})
    if not ssh_data:
        return "Ошибка: данные для SSH подключения не найдены. Используйте команду /setup_ssh для настройки."
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ssh_data['ip'], ssh_data['port'], ssh_data['username'], ssh_data['password'])
    stdin, stdout, stderr = client.exec_command(command)
    result = stdout.read() + stderr.read()
    client.close()
    return result.decode()

async def safe_send_message(update: Update, text: str, max_length=4096):
    """
    Функция для отправки длинных сообщений, разбивая текст на несколько частей, если он превышает максимально допустимую длину.
    """
    if len(text) <= max_length:
        await update.message.reply_text(text)
    else:
        for start in range(0, len(text), max_length):
            await update.message.reply_text(text[start:start + max_length])


async def get_release(update: Update, context):
    command = "lsb_release -a"
    result = ssh_command(context, command)
    await safe_send_message(update, f"Release Information:\n{result}")

async def get_uname(update: Update, context):
    command = "uname -a"
    result = ssh_command(context, command)
    await safe_send_message(update, f"System Information:\n{result}")

async def get_uptime(update: Update, context):
    command = "uptime"
    result = ssh_command(context, command)
    await safe_send_message(update, f"Uptime:\n{result}")

async def get_df(update: Update, context):
    command = "df -h"
    result = ssh_command(context, command)
    await safe_send_message(update, f"Disk Usage:\n{result}")

async def get_free(update: Update, context):
    command = "free -h"
    result = ssh_command(context, command)
    await safe_send_message(update, f"Memory Usage:\n{result}")

async def get_mpstat(update: Update, context):
    command = "mpstat"
    result = ssh_command(context, command)
    await safe_send_message(update, f"CPU Performance:\n{result}")

async def get_w(update: Update, context):
    command = "w"
    result = ssh_command(context, command)
    await safe_send_message(update, f"Active Users:\n{result}")

async def get_auths(update: Update, context):
    command = "last -n 10"
    result = ssh_command(context, command)
    await safe_send_message(update, f"Last 10 Logins:\n{result}")

async def get_critical(update: Update, context):
    command = "journalctl -p crit -n 5"
    result = ssh_command(context, command)
    await safe_send_message(update, f"Last 5 Critical Events:\n{result}")

async def get_ps(update: Update, context):
    command = "ps -aux"
    result = ssh_command(context, command)
    await safe_send_message(update, f"Running Processes:\n{result}")

async def get_ss(update: Update, context):
    command = "ss -tulwn"
    result = ssh_command(context, command)
    await safe_send_message(update, f"Open Ports:\n{result}")

async def get_apt_list(update: Update, context):
    args = context.args
    package_name = ' '.join(args) if args else ''
    command = f"apt list --installed | grep {package_name}" if package_name else "apt list --installed"
    result = ssh_command(context, command)
    await safe_send_message(update, f"Installed Packages:\n{result}")

async def get_services(update: Update, context):
    command = "systemctl list-units --type=service --state=running"
    result = ssh_command(context, command)
    await safe_send_message(update, f"Running Services:\n{result}")

async def get_repl_logs(update: Update, context):
    command = "tail -n 100 /var/lib/docker/volumes/education_master_data/_data/logs/*.log"
    result = ssh_command(context, command)
    await safe_send_message(update, f"PostgreSQL Replication Logs:\n{result}")


async def cancel(update: Update, context):
    await update.message.reply_text('Действие отменено.')
    return ConversationHandler.END

async def echo(update: Update, context):
    await update.message.reply_text(update.message.text)

def main():
    app = Application.builder().token(TOKEN).build()

    # Обработчик диалога
    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('findPhoneNumbers', findPhoneNumbersCommand)],
        states={
            FIND_PHONE_NUMBERS: [MessageHandler(filters.Text() & ~filters.Command(), findPhoneNumbers)],
            SAVE_PHONE_NUMBERS: [MessageHandler(filters.Text() & ~filters.Command(), savePhoneNumbers)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    convHandlerFindEmails = ConversationHandler(
        entry_points=[CommandHandler('findEmails', findEmailsCommand)],
        states={
            FIND_EMAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, findEmails)],
            SAVE_EMAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, saveEmails)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    conv_handler_verify_password = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verify_password_command)],
        states={
            PASSWORD_ENTRY: [MessageHandler(filters.Text() & ~filters.Command(), verify_password)]
        },
        fallbacks=[]
    )
    conv_handler_setup_ssh = ConversationHandler(
        entry_points=[CommandHandler('setup_ssh', setup_ssh_command)],
        states={'ssh_setup': [MessageHandler(filters.Text() & ~filters.Command(), ssh_setup)]},
        fallbacks=[]
    )

    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(convHandlerFindPhoneNumbers)
    app.add_handler(convHandlerFindEmails)
    app.add_handler(conv_handler_verify_password)
    app.add_handler(conv_handler_setup_ssh)

    app.add_handler(CommandHandler("get_release", get_release))
    app.add_handler(CommandHandler("get_uname", get_uname))
    app.add_handler(CommandHandler("get_uptime", get_uptime))
    app.add_handler(CommandHandler("get_df", get_df))
    app.add_handler(CommandHandler("get_free", get_free))
    app.add_handler(CommandHandler("get_mpstat", get_mpstat))
    app.add_handler(CommandHandler("get_w", get_w))
    app.add_handler(CommandHandler("get_auths", get_auths))
    app.add_handler(CommandHandler("get_critical", get_critical))
    app.add_handler(CommandHandler("get_ps", get_ps))
    app.add_handler(CommandHandler("get_ss", get_ss))
    app.add_handler(CommandHandler("get_apt_list", get_apt_list))
    app.add_handler(CommandHandler("get_services", get_services))
    app.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    app.add_handler(CommandHandler("get_email", get_email))
    app.add_handler(CommandHandler("get_phone", get_phone))
    
    # Регистрируем обработчик текстовых сообщений
    app.add_handler(MessageHandler(filters.Text() & ~filters.Command(), echo))
    
    # Запускаем бота
    app.run_polling()

if __name__ == '__main__':
    main()
