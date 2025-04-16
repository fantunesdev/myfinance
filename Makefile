format:
	@poetry run isort .
	@poetry run blue . --line-length 120
	@npm run format:js
install:
	@echo "Instalando o MyFinance..."
	@poetry install
	@poetry run mysql -e 'CREATE DATABASE myfinance'
	@poetry run python manage.py makemigrations statement
	@poetry run python manage.py migrate statement
	@poetry run python manage.py makemigrations login
	@poetry run python manage.py migrate login
	@poetry run python manage.py collectstatic
run:
	@poetry shell
	@poetry run daphne -b 0.0.0.0 -p 8765 myfinance.asgi:application &
	@poetry run python manage.py runserver
update:
	@poetry run python manage.py makemigrations statement
	@poetry run python manage.py migrate statement
	@poetry run python manage.py makemigrations login
	@poetry run python manage.py migrate login
	@poetry run python manage.py collectstatic
kill_daphne:
	@pkill -f "daphne" || true