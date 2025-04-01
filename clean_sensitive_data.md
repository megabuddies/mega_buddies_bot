# Инструкция по очистке чувствительных данных из истории Git

Если ваш токен бота или другие чувствительные данные уже были добавлены в репозиторий, вы можете очистить их из истории. Это важно сделать перед публикацией проекта на GitHub.

## Вариант 1: Использование BFG Repo-Cleaner (рекомендуется)

BFG Repo-Cleaner — это более быстрый и простой инструмент, чем git-filter-branch.

1. Скачайте BFG: https://rtyley.github.io/bfg-repo-cleaner/

2. Создайте файл `replacements.txt` со следующим содержимым:
   ```
   your_actual_bot_token=***REMOVED***
   123456789=***REMOVED***
   ```
   Замените `your_actual_bot_token` и `123456789` на реальные значения, которые нужно удалить.

3. Запустите команду:
   ```bash
   java -jar bfg.jar --replace-text replacements.txt your-repo.git
   ```

4. Очистите ссылки и кэш:
   ```bash
   cd your-repo.git
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   ```

5. Принудительный push изменений:
   ```bash
   git push --force
   ```

## Вариант 2: Использование git-filter-branch

Если вы не можете использовать BFG, можно воспользоваться встроенной командой git-filter-branch:

1. Найдите чувствительные данные:
   ```bash
   git grep "your_bot_token" $(git rev-list --all)
   git grep "admin_id" $(git rev-list --all)
   ```

2. Замените данные во всей истории:
   ```bash
   git filter-branch --force --index-filter \
     "git ls-files -z | xargs -0 sed -i 's/your_actual_bot_token/YOUR_BOT_TOKEN/g'" \
     --prune-empty -- --all
   
   git filter-branch --force --index-filter \
     "git ls-files -z | xargs -0 sed -i 's/123456789/YOUR_ADMIN_ID/g'" \
     --prune-empty -- --all
   ```

3. Очистите ссылки и кэш:
   ```bash
   git for-each-ref --format="delete %(refname)" refs/original | git update-ref --stdin
   git reflog expire --expire=now --all
   git gc --prune=now
   ```

4. Принудительный push изменений:
   ```bash
   git push --force
   ```

## ВАЖНО!

После очистки истории все участники проекта должны заново клонировать репозиторий, так как принудительный push изменяет историю.

## Предотвращение утечек в будущем

1. Всегда храните чувствительные данные в `.env` файле
2. Убедитесь, что `.env` добавлен в `.gitignore`
3. Используйте проверку перед коммитом (pre-commit hook) для поиска чувствительных данных
4. Регулярно меняйте токены и пароли 