"""Teacher portal shared compatibility exports for split endpoint modules."""

from datetime import timedelta
from pathlib import Path
import tempfile
from urllib.parse import urlencode, urlparse
import zipfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.validators import validate_email
from django.db import IntegrityError, models, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST
from django_otp.plugins.otp_totp.models import TOTPDevice

from ...http.headers import apply_download_safety, apply_no_store, safe_attachment_filename
from ...models import (
    Class,
    LessonAsset,
    LessonAssetFolder,
    LessonRelease,
    LessonVideo,
    Material,
    Module,
    StudentEvent,
    StudentIdentity,
    Submission,
    gen_class_code,
)
from ...services.authoring_templates import generate_authoring_templates
from ...services.content_links import build_asset_url
from ...services.filenames import safe_filename
from ...services.markdown_content import load_lesson_markdown
from ...services.release_state import parse_release_date
from ..content import iter_course_lesson_options
from .shared_auth import (
    _AUTHORING_TEMPLATE_SUFFIXES,
    _TEMPLATE_SLUG_RE,
    _build_teacher_setup_token,
    _format_base32_for_display,
    _resolve_teacher_setup_user,
    _send_teacher_onboarding_email,
    _teacher_2fa_device_name,
    _totp_qr_svg,
    _totp_secret_base32,
    staff_member_required,
)
from .shared_ordering import (
    _next_lesson_video_order,
    _normalize_order,
    _title_from_video_filename,
)
from .shared_routing import (
    _audit,
    _authoring_template_output_dir,
    _lesson_asset_redirect_params,
    _lesson_video_redirect_params,
    _normalize_helper_topics_text,
    _normalize_optional_slug_tag,
    _parse_positive_int,
    _resolve_authoring_template_download_path,
    _safe_internal_redirect,
    _safe_teacher_return_path,
    _teach_class_path,
    _teach_module_path,
    _with_notice,
)
from .shared_tracker import (
    _build_class_digest_rows,
    _build_lesson_tracker_rows,
    _local_day_window,
)

# Re-export underscore-prefixed helpers and imported symbols used by split endpoint modules.
__all__ = [name for name in globals() if not name.startswith("__")]
