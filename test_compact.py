import sys, os
sys.path.insert(0, os.path.abspath('services/homework_helper'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from tutor.engine.memory import compact_turns, save_state, load_state
from django.core.cache import cache

def test_it():
    turns = [
        {"role": "student", "content": "First question", "intent": "general"},
        {"role": "assistant", "content": "Answer one"},
        {"role": "student", "content": "Second question", "intent": "general"},
        {"role": "assistant", "content": "Answer two"},
    ]

    print("compacting from 4 to 2...")
    s, k, c = compact_turns(turns=turns, max_messages=2, summary="", summary_max_chars=400)
    print("summary:", s)
    print("keep:", k)
    print("compacted:", c)

test_it()
