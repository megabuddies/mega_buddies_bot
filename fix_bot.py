import re

# Читаем содержимое бота
with open('bot.py', 'r', encoding='utf-8') as f:
    bot_content = f.read()

# Определяем функции, которые указаны в списке ошибок
missing_functions = [
    'setup_commands', 
    'menu_command',
    'export_command', 
    'import_command',
    'button_callback',
    'handle_import_file',
    'handle_message'
]

# Словарь для отслеживания уже проверенных функций
processed_functions = {}

print("Начинаем перемещение функций...")

# Сначала найдем определения функций, которые уже были перемещены
for line in bot_content.split('\n'):
    if '# Moved function ' in line:
        function_name = line.strip().replace('# Moved function ', '')
        processed_functions[function_name] = True
        print(f"Функция {function_name} уже была перемещена ранее.")

# Теперь поищем остальные функции
for function_name in missing_functions:
    if function_name in processed_functions:
        print(f"Пропускаем функцию {function_name}, она уже обработана.")
        continue

    print(f"Поиск функции {function_name}...")
    
    # Примерный паттерн функции (с учетом возможных пробелов и отступов)
    pattern = rf'[ \t]+async def {function_name}\s*\('
    
    match = re.search(pattern, bot_content)
    if not match:
        print(f"Функция {function_name} не найдена.")
        continue
    
    # Нашли начало функции
    start_pos = match.start()
    line_start = bot_content.rfind('\n', 0, start_pos) + 1
    
    # Определяем уровень отступа
    indent = ''
    for c in bot_content[line_start:start_pos]:
        if c in ' \t':
            indent += c
        else:
            break
    
    print(f"Найдена функция {function_name} с отступом '{indent}'")
    
    # Ищем конец функции (следующую строку с таким же или меньшим отступом)
    lines = bot_content[start_pos:].split('\n')
    
    # Пропускаем первую строку (определение функции)
    first_line = lines[0]
    lines = lines[1:]
    
    # Собираем содержимое функции
    function_body = [first_line]
    end_pos = start_pos + len(first_line)
    
    for line in lines:
        if line.strip() and not line.startswith(indent):
            break
        function_body.append(line)
        end_pos += len(line) + 1  # +1 для символа новой строки
    
    # Собираем полный текст функции
    full_function = '\n'.join(function_body)
    
    # Удаляем отступы из функции
    unindented_function = first_line.replace(indent, '', 1) + '\n'
    for line in function_body[1:]:
        if line.startswith(indent):
            unindented_function += line.replace(indent, '', 1) + '\n'
        else:
            unindented_function += line + '\n'
    
    # Удаляем функцию из исходного текста
    new_content = bot_content[:start_pos] + bot_content[end_pos:]
    
    # Ищем позицию для вставки (перед функцией main)
    main_pattern = r'def main\(\) -> None:'
    main_match = re.search(main_pattern, new_content)
    
    if main_match:
        insert_pos = main_match.start()
        
        # Вставляем функцию перед main
        new_content = (
            new_content[:insert_pos] + 
            f"\n# Moved function {function_name}\n" + 
            unindented_function + 
            new_content[insert_pos:]
        )
        
        bot_content = new_content
        print(f"Функция {function_name} успешно перемещена.")
    else:
        print("Не найдена функция main(). Невозможно переместить функцию.")

# Записываем изменения в файл
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(bot_content)

print("Файл успешно обновлен!") 