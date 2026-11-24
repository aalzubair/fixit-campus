Stage 1 is approved. Start Stage 2 only (services.py and its tests), as in the plan, including the 150-character cut. Use the STUDENT_NAME constant from base.py in the tests. Then stop with a short summary and the results of all the checks.

Run the coverage check with this command, from src/:
coverage run --branch --source=campus --omit="*/migrations/*,*/tests/*" manage.py test
Do not change pyproject.toml.