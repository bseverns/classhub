import csv
import json
import re
import tempfile
import zipfile
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail, signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.utils import timezone

from common.helper_scope import parse_scope_token

from ..models import (
    AuditEvent,
    Class,
    LessonAsset,
    LessonAssetFolder,
    LessonVideo,
    LessonRelease,
    Material,
    Module,
    StudentEvent,
    StudentIdentity,
    Submission,
)
from ..services.helper_control import HelperResetResult
from ..services.upload_scan import ScanResult


def _sample_sb3_bytes() -> bytes:
    """Build a tiny valid Scratch archive for upload-path tests."""
    buf = BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project.json", '{"targets":[],"meta":{"semver":"3.0.0"}}')
    return buf.getvalue()


def _force_login_staff_verified(client: Client, user) -> None:
    """Authenticate and mark OTP as verified for /teach tests."""
    client.force_login(user)
    device, _ = TOTPDevice.objects.get_or_create(
        user=user,
        name="teacher-primary",
        defaults={"confirmed": True},
    )
    if not device.confirmed:
        device.confirmed = True
        device.save(update_fields=["confirmed"])
    session = client.session
    session["otp_device_id"] = device.persistent_id
    session.save()


__all__ = [name for name in globals() if not name.startswith("__")]
