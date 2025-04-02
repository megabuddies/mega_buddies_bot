import re

# Загружаем содержимое файла
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Найдем основные блоки в файле
main_match = re.search(r'def main\(\) -> None:', content)
if_name_match = re.search(r'if __name__ == "__main__":', content)

if not main_match or not if_name_match:
    print("Не удалось найти основные блоки в файле.")
    exit(1)

main_start = main_match.start()
if_name_start = if_name_match.start()
if_name_end = if_name_match.end() + len('\n    main()')

# Получаем все, что идет после блока if __name__
after_if_name = content[if_name_end:].strip()

# Разделим файл на части
part1 = content[:main_start]  # все до main()
part2 = content[main_start:if_name_start]  # main()
part3 = content[if_name_start:if_name_end]  # if __name__ == "__main__": main()
part4 = after_if_name  # все функции после if __name__

# Создаем новую структуру файла
# 1. Все импорты и инициализация
# 2. Все функции из part4
# 3. Функция main()
# 4. Блок if __name__ == "__main__":
new_content = part1 + '\n\n# Functions moved from after if __name__ block\n' + part4 + '\n\n' + part2 + '\n\n' + part3

# Записываем в файл
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Файл успешно реорганизован!") 