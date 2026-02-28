"""Media streaming/download endpoint callables."""

import mimetypes
import re
from pathlib import Path

from django.db.utils import OperationalError, ProgrammingError
from django.http import FileResponse, HttpResponse, StreamingHttpResponse

from ..http.headers import (
    apply_download_safety,
    apply_inline_asset_safety,
    apply_no_store,
    safe_attachment_filename,
)
from ..models import LessonAsset, LessonVideo
from ..services.content_links import video_mime_type

_INLINE_ASSET_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "video/mp4",
    "video/webm",
    "video/ogg",
    "application/pdf",
}


def _asset_allows_inline(content_type: str) -> bool:
    normalized = (content_type or "").strip().lower()
    return normalized in _INLINE_ASSET_MIME_TYPES


def _request_can_view_course_lesson(request, course_slug: str, lesson_slug: str) -> bool:
    if request.user.is_authenticated and request.user.is_staff:
        return True
    student = getattr(request, "student", None)
    if not student:
        return False
        
    if not course_slug and not lesson_slug:
        return True

    from django.db.models import Q
    from ..models import Material
    expected_path = f"/course/{course_slug}/{lesson_slug}"
    return Material.objects.filter(
        Q(url__endswith=expected_path) | Q(url__endswith=expected_path + "/"),
        module__classroom=student.classroom,
        type=Material.TYPE_LINK,
    ).exists()


def _stream_file_with_range(request, file_path: Path, content_type: str):
    # Supports HTTP byte-range requests for seekable video playback.
    file_size = file_path.stat().st_size
    range_header = request.headers.get("Range") or request.META.get("HTTP_RANGE", "")
    if not range_header:
        response = FileResponse(open(file_path, "rb"), content_type=content_type)
        response["Content-Length"] = str(file_size)
        response["Accept-Ranges"] = "bytes"
        return response

    m = re.match(r"bytes=(\d*)-(\d*)", range_header)
    if not m:
        response = HttpResponse(status=416)
        response["Content-Range"] = f"bytes */{file_size}"
        return response

    start_raw, end_raw = m.group(1), m.group(2)
    if not start_raw and not end_raw:
        response = HttpResponse(status=416)
        response["Content-Range"] = f"bytes */{file_size}"
        return response

    if start_raw:
        start = int(start_raw)
        end = int(end_raw) if end_raw else file_size - 1
    else:
        suffix_len = int(end_raw)
        if suffix_len <= 0:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{file_size}"
            return response
        start = max(file_size - suffix_len, 0)
        end = file_size - 1

    if start >= file_size or end < start:
        response = HttpResponse(status=416)
        response["Content-Range"] = f"bytes */{file_size}"
        return response

    end = min(end, file_size - 1)
    length = (end - start) + 1

    file_handle = open(file_path, "rb")

    def _iter_file(handle, offset: int, remaining: int, chunk_size: int = 64 * 1024):
        try:
            handle.seek(offset)
            left = remaining
            while left > 0:
                chunk = handle.read(min(chunk_size, left))
                if not chunk:
                    break
                left -= len(chunk)
                yield chunk
        finally:
            handle.close()

    response = StreamingHttpResponse(
        _iter_file(file_handle, start, length),
        status=206,
        content_type=content_type,
    )
    response["Content-Length"] = str(length)
    response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    response["Accept-Ranges"] = "bytes"
    return response


def lesson_video_stream(request, video_id: int):
    try:
        video = LessonVideo.objects.filter(id=video_id).first()
    except (OperationalError, ProgrammingError) as exc:
        if "hub_lessonvideo" in str(exc).lower():
            return HttpResponse("Not found", status=404)
        raise
    if not video or not video.video_file:
        return HttpResponse("Not found", status=404)

    is_staff_user = bool(request.user.is_authenticated and request.user.is_staff)
    if not video.is_active and not is_staff_user:
        return HttpResponse("Not found", status=404)

    if not _request_can_view_course_lesson(request, video.course_slug, video.lesson_slug):
        return HttpResponse("Forbidden", status=403)

    try:
        file_path = Path(video.video_file.path)
    except Exception:
        return HttpResponse("Not found", status=404)
    if not file_path.exists():
        return HttpResponse("Not found", status=404)

    content_type = video_mime_type(video.video_file.name)
    return _stream_file_with_range(request, file_path, content_type)


def lesson_asset_download(request, asset_id: int):
    try:
        asset = LessonAsset.objects.select_related("folder").filter(id=asset_id).first()
    except (OperationalError, ProgrammingError) as exc:
        if "hub_lessonasset" in str(exc).lower():
            return HttpResponse("Not found", status=404)
        raise
    if not asset or not asset.file:
        return HttpResponse("Not found", status=404)

    is_staff_user = bool(request.user.is_authenticated and request.user.is_staff)
    if not asset.is_active and not is_staff_user:
        return HttpResponse("Not found", status=404)

    if not _request_can_view_course_lesson(request, asset.course_slug, asset.lesson_slug):
        return HttpResponse("Forbidden", status=403)

    try:
        file_path = Path(asset.file.path)
    except Exception:
        return HttpResponse("Not found", status=404)
    if not file_path.exists():
        return HttpResponse("Not found", status=404)

    filename = safe_attachment_filename(asset.original_filename or file_path.name or "asset", fallback="asset")
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    inline_allowed = _asset_allows_inline(content_type)
    response = FileResponse(
        open(file_path, "rb"),
        as_attachment=not inline_allowed,
        filename=filename,
        content_type=content_type,
    )
    if inline_allowed:
        apply_inline_asset_safety(response, max_age_seconds=60)
    else:
        apply_download_safety(response)
        apply_no_store(response, private=True, pragma=True)
    return response


__all__ = [
    "lesson_video_stream",
    "lesson_asset_download",
]
