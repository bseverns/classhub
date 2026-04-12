import sys
import os
sys.path.insert(0, '/Users/bseverns/Documents/GitHub/selfhosted-classhub/services/classhub')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

try:
    from hub.views import teach_edit_lesson_content
    print("SUCCESS: teach_edit_lesson_content was imported!")
except Exception as e:
    import traceback
    traceback.print_exc()
