Approved, with these changes:

1. Coverage: do NOT use your command. Use exactly the documented one, from src/:
   coverage run --branch --source=campus --omit="*/migrations/*,*/tests/*" manage.py test
   coverage report -m
   (A plain run counted manage.py and showed 99% before.)

2. Before adding the 3 new login tests to RecordsCheckAtLoginTests, count its public methods. If the class would go over 20, put the new tests in their own new test class. Do not silence the pylint warning.

3. Service docstrings: follow your plan. Do not add ValueError to the service functions.

4. In _copy_records_details use: member.name.strip()[:MEMBER_NAME_MAX_LENGTH].rstrip()
   and add one test: a name whose 150th character is a space is stored without a trailing space.

Start Stage 1, then stop and show me the summary.