import re

# Читаем содержимое бота
with open('bot.py', 'r', encoding='utf-8') as f:
    bot_content = f.read()

# Ищем функции связанные с вкладами
contribution_functions_pattern = r'# Add contribution-related functions\s+(async def show_contribute_menu.*?return ConversationHandler\.END)'
match = re.search(contribution_functions_pattern, bot_content, re.DOTALL)

if match:
    contribution_functions = match.group(1)
    # Удаляем функции из их текущего расположения
    bot_content = bot_content.replace(f'# Add contribution-related functions\n{contribution_functions}', '')
    
    # Находим место перед функцией main()
    main_pattern = r'def main\(\) -> None:'
    main_match = re.search(main_pattern, bot_content)
    
    if main_match:
        insert_pos = main_match.start()
        # Вставляем функции перед main()
        modified_content = (
            bot_content[:insert_pos] + 
            '# Add contribution-related functions\n' + 
            contribution_functions + 
            '\n\n    ' + 
            bot_content[insert_pos:]
        )
        
        # Записываем изменения обратно в файл
        with open('bot.py', 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        print("Файл bot.py успешно исправлен!")
    else:
        print("Функция main() не найдена в файле!")
else:
    print("Функции для работы с вкладами не найдены в файле!") 