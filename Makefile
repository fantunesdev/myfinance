format:
	@poetry run isort .
	@poetry run blue .
install:
	@echo "Instalando o MyFinance..."
	@poetry install
run:
	@poetry shell
	@poetry run python manage.py runserver