format:
	@poetry run isort .
	@poetry run ruff format .
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
create_oauth_app:
	@python manage.py create_oauth_app

.PHONY: test coverage
test:
	@poetry run pytest --ds=myfinance.test_settings tests
	@node --test tests/js/*.test.mjs

coverage:
	@poetry run coverage run -m pytest --ds=myfinance.test_settings tests
	@poetry run coverage xml --fail-under=0
	@poetry run coverage html --fail-under=0
	@poetry run coverage report
