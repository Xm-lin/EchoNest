import logging
import os
import re
import sys

class SafeFormatter(logging.Formatter):
    def format(self, record):
        rendered=super().format(record)
        for key in ('DISCORD_TOKEN','GEMINI_API_KEY','AGENS_API_KEY','SUPABASE_SERVICE_ROLE_KEY','DATABASE_URL'):
            secret=os.getenv(key)
            if secret: rendered=rendered.replace(secret,'[REDACTED]')
        return re.sub(r'(?i)(authorization|api[_-]?key|token)\s*[:=]\s*\S+',r'\1=[REDACTED]',rendered)

class SecretFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.secrets = [os.getenv(k) for k in ('DISCORD_TOKEN', 'GEMINI_API_KEY', 'AGENS_API_KEY', 'SUPABASE_SERVICE_ROLE_KEY', 'DATABASE_URL') if os.getenv(k)]

    def filter(self, record):
        msg = record.getMessage()
        for secret in self.secrets:
            msg = msg.replace(secret, '[REDACTED]')
        msg = re.sub(r'(?i)(authorization|api[_-]?key|token)\s*[:=]\s*\S+', r'\1=[REDACTED]', msg)
        record.msg, record.args = msg, ()
        return True

def setup():
    handler = logging.StreamHandler(sys.stderr)
    handler.addFilter(SecretFilter())
    handler.setFormatter(SafeFormatter('%(asctime)s %(levelname)s [%(name)s] %(message)s', '%Y-%m-%dT%H:%M:%S'))
    root = logging.getLogger()
    root.setLevel(os.getenv('LOG_LEVEL', 'INFO').upper())
    if not root.handlers: root.addHandler(handler)
