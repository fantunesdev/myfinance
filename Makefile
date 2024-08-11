format:
	@poetry run isort .
	@poetry run blue . --line-length 110
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
	@poetry run python manage.py runserver
update:
	@poetry run python manage.py makemigrations statement
	@poetry run python manage.py migrate statement
	@poetry run python manage.py makemigrations login
	@poetry run python manage.py migrate login
	@poetry run python manage.py collectstatic