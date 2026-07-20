from ._shared import *  # noqa: F401,F403
from ._teacher_admin_portal_base import TeacherPortalBaseTests
from ..services.coursepack_registry import build_registry_entry, new_registry_document, upsert_registry_entry, write_registry_document


class TeacherPortalClassContentRegistryOpsTests(TeacherPortalBaseTests):
    def _registry_index(self, *, root: Path, slug: str, version: str) -> Path:
        courses_root = root / "registry_source_courses"
        course_dir = courses_root / slug
        course_dir.mkdir(parents=True)
        (course_dir / "course.yaml").write_text(
            f"""slug: {slug}
title: "Portal Registry Course"
ui_level: advanced
program_profile: advanced
lessons:
  - session: 1
    slug: s01-build
    title: "Build"
    file: lessons/01-build.md
""",
            encoding="utf-8",
        )
        artifact_dir = root / "published_registry" / "artifacts"
        artifact_dir.mkdir(parents=True)
        artifact_path = artifact_dir / f"{slug}_{version}.zip"
        artifact_buffer = BytesIO()
        with zipfile.ZipFile(artifact_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                f"{slug}/course.yaml",
                f"""slug: {slug}
title: "Portal Registry Course"
ui_level: advanced
program_profile: advanced
lessons:
  - session: 1
    slug: s01-build
    title: "Build"
    file: lessons/01-build.md
""",
            )
            archive.writestr(
                f"{slug}/lessons/01-build.md",
                f"""---
course: {slug}
session: 1
slug: s01-build
title: "Build"
submission:
  type: file
  accepted:
    - .sb3
---
# Build
""",
            )
        artifact_path.write_bytes(artifact_buffer.getvalue())
        entry = build_registry_entry(
            slug=slug,
            artifact_path=artifact_path,
            version=version,
            artifact_url=f"artifacts/{artifact_path.name}",
            source_url=f"https://example.org/coursepacks/{slug}",
            sdk_version="0.1.0",
            courses_root=courses_root,
        )
        index_path = root / "published_registry" / "index.json"
        write_registry_document(index_path, upsert_registry_entry(new_registry_document(), entry))
        return index_path

    def test_teach_home_shows_registry_import_tool_for_superuser(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach")

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Import Registry Coursepack")
        self.assertContains(resp, 'action="/teach/import-coursepack-registry"', html=False)

    def test_superuser_can_import_registry_coursepack_from_teach_home(self):
        _force_login_staff_verified(self.client, self.staff)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = self._registry_index(
                root=root,
                slug="portal_registry_course",
                version="20260608T223000Z",
            )
            content_root = root / "content"
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.post(
                    "/teach/import-coursepack-registry",
                    {
                        "registry_index": index_path.as_uri(),
                        "registry_course_slug": "portal_registry_course",
                        "registry_version": "20260608T223000Z",
                        "registry_class_name": "Portal Registry Cohort",
                        "registry_create_class": "1",
                    },
                )

                self.assertEqual(resp.status_code, 302)
                self.assertIn("/teach?notice=", resp["Location"])
                self.assertTrue((content_root / "courses" / "portal_registry_course" / "course.yaml").exists())

        classroom = Class.objects.get(name="Portal Registry Cohort")
        self.assertEqual(classroom.modules.count(), 1)
        self.assertTrue(Material.objects.filter(module__classroom=classroom, title="Homework dropbox").exists())
        event = AuditEvent.objects.filter(action="coursepack.registry.import", classroom=classroom).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)
        self.assertEqual(event.metadata["import_channel"], "teacher_portal")
        self.assertEqual(event.metadata["source_metadata"]["registry_version"], "20260608T223000Z")

    @patch("hub.views.teacher_parts.content_registry_import.import_coursepack_registry")
    def test_registry_live_course_replacement_requires_typed_confirmation(self, import_mock):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            "/teach/import-coursepack-registry",
            {
                "registry_index": "https://example.org/classhub-coursepacks/index.json",
                "registry_course_slug": "protected_course",
                "registry_replace": "1",
                "confirm_overwrite_content": "WRONG",
            },
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn("error=", resp["Location"])
        import_mock.assert_not_called()

    def test_non_superuser_cannot_import_registry_coursepack_from_teach_home(self):
        teacher = get_user_model().objects.create_user(
            username="staff_teacher_registry_blocked",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        _force_login_staff_verified(self.client, teacher)

        resp = self.client.post(
            "/teach/import-coursepack-registry",
            {
                "registry_index": "https://example.org/classhub-coursepacks/index.json",
                "registry_course_slug": "blocked_course",
                "registry_class_name": "Blocked Cohort",
                "registry_create_class": "1",
            },
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])

    def test_superuser_can_filter_content_import_audit_feed(self):
        _force_login_staff_verified(self.client, self.staff)
        class_a = Class.objects.create(name="Audit Alpha Cohort", join_code="AUDIT001")
        class_b = Class.objects.create(name="Audit Beta Cohort", join_code="AUDIT002")
        AuditEvent.objects.create(
            actor_user=self.staff,
            classroom=class_a,
            action="coursepack.registry.import",
            target_type="Coursepack",
            target_id="alpha-course",
            summary="content audit keep alpha",
            metadata={"import_channel": "teacher_portal", "source_kind": "coursepack_registry"},
        )
        AuditEvent.objects.create(
            actor_user=self.staff,
            classroom=class_b,
            action="coursepack.registry.import",
            target_type="Coursepack",
            target_id="beta-course",
            summary="content audit drop beta class",
            metadata={"import_channel": "teacher_portal", "source_kind": "coursepack_registry"},
        )
        AuditEvent.objects.create(
            actor_user=self.staff,
            classroom=class_a,
            action="teacher_templates.generate",
            target_type="AuthoringTemplates",
            target_id="template-course",
            summary="content audit drop action family",
            metadata={},
        )

        resp = self.client.get(
            "/teach",
            {
                "portal_mode": "setup",
                "advanced": "1",
                "content_audit_action": "coursepack.registry.import",
                "content_audit_class_id": str(class_a.id),
                "content_audit_limit": "25",
            },
        )

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Content Import Audit")
        self.assertContains(resp, "content audit keep alpha")
        self.assertNotContains(resp, "content audit drop beta class")
        self.assertNotContains(resp, "content audit drop action family")

    def test_superuser_can_inspect_selected_content_import_audit_event(self):
        _force_login_staff_verified(self.client, self.staff)
        classroom = Class.objects.create(name="Audit Detail Cohort", join_code="AUDIT003")
        event = AuditEvent.objects.create(
            actor_user=self.staff,
            classroom=classroom,
            action="coursepack.registry.import",
            target_type="Coursepack",
            target_id="detail-course",
            summary="content audit inspect detail",
            metadata={
                "import_channel": "teacher_portal",
                "source_kind": "coursepack_registry",
                "source_metadata": {
                    "registry_version": "20260609T010000Z",
                    "artifact_url": "https://example.org/coursepacks/detail-course.zip",
                    "sha256": "abc123",
                    "artifact_bytes": 4242,
                },
            },
        )

        resp = self.client.get(
            "/teach",
            {
                "portal_mode": "setup",
                "advanced": "1",
                "content_audit_action": "coursepack.registry.import",
                "content_audit_class_id": str(classroom.id),
                "content_audit_event_id": str(event.id),
            },
        )

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Selected audit event")
        self.assertContains(resp, "20260609T010000Z")
        self.assertContains(resp, "https://example.org/coursepacks/detail-course.zip")
        self.assertContains(resp, "abc123")
        self.assertContains(resp, "content-audit-row-selected")

    def test_class_dashboard_links_to_prefiltered_content_import_audit(self):
        _force_login_staff_verified(self.client, self.staff)
        classroom = Class.objects.create(name="Audit Shortcut Cohort", join_code="AUDIT004")

        resp = self.client.get(f"/teach/class/{classroom.id}")

        self.assertEqual(resp.status_code, 200)
        self.assertContains(
            resp,
            f'/teach?portal_mode=setup&amp;advanced=1&amp;content_audit_class_id={classroom.id}#content-import-audit',
            html=False,
        )
        self.assertContains(
            resp,
            (
                "/teach?portal_mode=setup&amp;advanced=1&amp;content_audit_class_id="
                f"{classroom.id}&amp;content_audit_action=coursepack.registry.import#content-import-audit"
            ),
            html=False,
        )


__all__ = ["TeacherPortalClassContentRegistryOpsTests"]
