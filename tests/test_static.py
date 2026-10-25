"""Offline checks that require no Discord/Supabase secrets."""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class ProjectChecks(unittest.TestCase):
    def test_python_syntax(self):
        for name in ('bot.py', 'database.py'):
            ast.parse((ROOT / name).read_text(encoding='utf-8'))

    def test_required_files(self):
        for name in ('Dockerfile', 'render.yaml', '.env.example', 'database.py', 'requirements.txt'):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_postgres_schema(self):
        text = (ROOT / 'database.py').read_text()
        for table in ('characters', 'profiles', 'inventory', 'messages', 'memories'):
            self.assertIn(f'CREATE TABLE IF NOT EXISTS {table}', text)
        self.assertIn('sslmode=require', text)

    def test_no_sqlite(self):
        self.assertNotIn('sqlite3', (ROOT / 'bot.py').read_text())

    def test_healthcheck(self):
        self.assertIn('/health', (ROOT / 'bot.py').read_text())
        self.assertIn('healthCheckPath: /health', (ROOT / 'render.yaml').read_text())

    def test_no_secrets_in_example(self):
        example = (ROOT / '.env.example').read_text()
        self.assertIn('your_discord_bot_token', example)
        self.assertIn('your_gemini_api_key', example)

if __name__ == '__main__':
    unittest.main()
