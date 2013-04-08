TESTS=tests

test:
	cd tests && DJANGO_SETTINGS_MODULE=tests.test_sqlite $(COVERAGE_COMMAND) ./manage.py test $(TESTS) --verbosity=2

coverage:
	+make test COVERAGE_COMMAND='coverage run --source=ool --branch'
	cd tests && coverage html

.PHONY: test
