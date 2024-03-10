format:
	@poetry run isort .
	@poetry run blue .
install:
	@echo "Instalando o MyFinance..."
	@poetry install
	@poetry run mysql -e 'CREATE DATABASE myfinance;'
	@poetry run python manage.py makemigrations
	@poetry run python manage.py migrate
run:
	@poetry shell
	@poetry run python manage.py runserver