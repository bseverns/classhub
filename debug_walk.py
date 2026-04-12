import sys
import os
import types

sys.path.insert(0, '/Users/bseverns/Documents/GitHub/selfhosted-classhub/services/classhub')

# Mock Django modules enough to bypass the ModuleNotFoundError
django_mock = types.ModuleType('django')
sys.modules['django'] = django_mock

conf = types.ModuleType('conf')
conf.settings = type('Settings', (), {'DEBUG': False})()
sys.modules['django.conf'] = conf

utils = types.ModuleType('utils')
sys.modules['django.utils'] = utils
utils_os = types.ModuleType('_os')
utils_os.safe_join = lambda *args: ""
sys.modules['django.utils._os'] = utils_os

shortcuts = types.ModuleType('shortcuts')
shortcuts.redirect = lambda *args: None
sys.modules['django.shortcuts'] = shortcuts

# Attempt to walk the import chain to isolate the point of failure
print("Starting import walk...")
try:
    from hub.views.teacher_parts.content_lessons import teach_edit_lesson_content
    print("SUCCESS: content_lessons")
    from hub.views.teacher_parts.content import teach_edit_lesson_content
    print("SUCCESS: content")
    from hub.views.teacher_parts import teach_edit_lesson_content
    print("SUCCESS: teacher_parts")
    from hub.views.teacher import teach_edit_lesson_content
    print("SUCCESS: teacher")
    from hub.views import teach_edit_lesson_content
    print("SUCCESS: views")
    print("ALL OK!")
except Exception as e:
    print(f"FAILED AT IMPORT CHAIN: {e}")
    import traceback
    traceback.print_exc()
