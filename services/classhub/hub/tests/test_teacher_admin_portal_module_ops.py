from ._shared import *  # noqa: F401,F403
from ._teacher_admin_portal_base import TeacherPortalBaseTests


class TeacherPortalModuleOpsTests(TeacherPortalBaseTests):
    def test_teach_module_uses_external_css_without_inline_styles(self):
        classroom = Class.objects.create(name="Period Module", join_code="MOD12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        Material.objects.create(
            module=module,
            title="Intro notes",
            type=Material.TYPE_TEXT,
            body="Welcome to session one.",
            order_index=0,
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/module/{module.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/static/css/teach_module.css")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin:0"', html=False)

    def test_teach_module_can_add_image_material_from_upload(self):
        classroom = Class.objects.create(name="Image Module", join_code="IMG12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        Material.objects.create(
            module=module,
            title="Session 1 lesson",
            type=Material.TYPE_LINK,
            url="/course/piper_scratch_12_session/01-welcome-private-workflow",
            order_index=0,
        )
        _force_login_staff_verified(self.client, self.staff)

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                resp = self.client.post(
                    f"/teach/module/{module.id}/add-material",
                    {
                        "type": Material.TYPE_LINK,
                        "title": "Mood board",
                        "asset_description": "Look at the shapes and colors before building.",
                        "asset_file": SimpleUploadedFile(
                            "mood-board.png",
                            b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00",
                            content_type="image/png",
                        ),
                    },
                )

                self.assertEqual(resp.status_code, 302)
                created = Material.objects.filter(module=module, title="Mood board").order_by("-id").first()
                self.assertIsNotNone(created)
                self.assertTrue((created.url or "").startswith("/lesson-asset/"))
                asset = LessonAsset.objects.filter(title="Mood board").order_by("-id").first()
                self.assertIsNotNone(asset)
                self.assertEqual(asset.description, "Look at the shapes and colors before building.")
                self.assertEqual(asset.course_slug, "piper_scratch_12_session")
                self.assertEqual(asset.lesson_slug, "01-welcome-private-workflow")

    def test_teach_module_renders_inline_preview_for_image_asset_material(self):
        classroom = Class.objects.create(name="Image Preview Class", join_code="IMGP1234")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        folder = LessonAssetFolder.objects.create(path="lesson-images")
        asset = LessonAsset.objects.create(
            folder=folder,
            title="Storyboard image",
            description="Notice the colors and layout.",
            original_filename="storyboard.png",
            file=SimpleUploadedFile("storyboard.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00", content_type="image/png"),
        )
        Material.objects.create(
            module=module,
            title="Storyboard image",
            type=Material.TYPE_LINK,
            url=f"/lesson-asset/{asset.id}/download",
            order_index=0,
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/module/{module.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'/lesson-asset/{asset.id}/download')
        self.assertContains(resp, 'class="material-image-preview"', html=False)
        self.assertContains(resp, "Notice the colors and layout.")

    def test_teach_module_can_add_checklist_material(self):
        classroom = Class.objects.create(name="Checklist Class", join_code="CHK12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/module/{module.id}/add-material",
            {
                "type": Material.TYPE_CHECKLIST,
                "title": "Class checklist",
                "checklist_items": "I completed the warm-up\nI tested my code",
            },
        )
        self.assertEqual(resp.status_code, 302)
        created = Material.objects.filter(module=module, type=Material.TYPE_CHECKLIST).first()
        self.assertIsNotNone(created)
        self.assertEqual(created.title, "Class checklist")
        self.assertIn("I completed the warm-up", created.body)

    def test_teach_module_can_add_reflection_material(self):
        classroom = Class.objects.create(name="Reflection Class", join_code="RFL12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/module/{module.id}/add-material",
            {
                "type": Material.TYPE_REFLECTION,
                "title": "Reflection journal",
                "reflection_prompt": "What changed in your code today?",
            },
        )
        self.assertEqual(resp.status_code, 302)
        created = Material.objects.filter(module=module, type=Material.TYPE_REFLECTION).first()
        self.assertIsNotNone(created)
        self.assertEqual(created.title, "Reflection journal")
        self.assertIn("What changed in your code today?", created.body)

    def test_teach_module_can_add_gallery_material(self):
        classroom = Class.objects.create(name="Gallery Class", join_code="GAL12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/module/{module.id}/add-material",
            {
                "type": Material.TYPE_GALLERY,
                "title": "Share to gallery",
                "accepted_extensions": ".png,.jpg,.jpeg,.pdf",
                "max_upload_mb": "20",
            },
        )
        self.assertEqual(resp.status_code, 302)
        created = Material.objects.filter(module=module, type=Material.TYPE_GALLERY).first()
        self.assertIsNotNone(created)
        self.assertEqual(created.title, "Share to gallery")
        self.assertEqual(created.accepted_extensions, ".png,.jpg,.jpeg,.pdf")
        self.assertEqual(created.max_upload_mb, 20)

    def test_teacher_can_toggle_module_session_gallery(self):
        classroom = Class.objects.create(name="Gallery Toggle", join_code="GTL12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0, gallery_enabled=True)
        Material.objects.create(
            module=module,
            title="Share to gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".png,.jpg,.jpeg,.pdf",
            max_upload_mb=20,
            order_index=0,
        )
        _force_login_staff_verified(self.client, self.staff)

        disable = self.client.post(f"/teach/module/{module.id}/set-gallery-enabled", {"gallery_enabled": "0"})
        self.assertEqual(disable.status_code, 302)
        module.refresh_from_db()
        self.assertFalse(module.gallery_enabled)

        enable = self.client.post(f"/teach/module/{module.id}/set-gallery-enabled", {"gallery_enabled": "1"})
        self.assertEqual(enable.status_code, 302)
        module.refresh_from_db()
        self.assertTrue(module.gallery_enabled)

    def test_teacher_can_moderate_gallery_submission(self):
        classroom = Class.objects.create(name="Gallery Moderate", join_code="GMD12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        gallery = Material.objects.create(
            module=module,
            title="Share to gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".png,.jpg,.jpeg,.pdf,.sb3",
            max_upload_mb=50,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        submission = Submission.objects.create(
            material=gallery,
            student=student,
            original_filename="project.sb3",
            file=SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=False,
        )
        _force_login_staff_verified(self.client, self.staff)

        approve = self.client.post(
            f"/teach/material/{gallery.id}/submission/{submission.id}/moderate",
            {"approve": "1", "return_to": f"/teach/material/{gallery.id}/submissions"},
        )
        self.assertEqual(approve.status_code, 302)
        submission.refresh_from_db()
        self.assertTrue(submission.is_gallery_shared)

        unapprove = self.client.post(
            f"/teach/material/{gallery.id}/submission/{submission.id}/moderate",
            {"approve": "0", "return_to": f"/teach/material/{gallery.id}/submissions"},
        )
        self.assertEqual(unapprove.status_code, 302)
        submission.refresh_from_db()
        self.assertFalse(submission.is_gallery_shared)

    def test_teach_module_can_add_rubric_material(self):
        classroom = Class.objects.create(name="Rubric Class", join_code="RUB12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/module/{module.id}/add-material",
            {
                "type": Material.TYPE_RUBRIC,
                "title": "Session rubric",
                "rubric_criteria": "Problem solving\nCode quality\nReflection depth",
                "rubric_scale_max": "5",
            },
        )
        self.assertEqual(resp.status_code, 302)
        created = Material.objects.filter(module=module, type=Material.TYPE_RUBRIC).first()
        self.assertIsNotNone(created)
        self.assertEqual(created.title, "Session rubric")
        self.assertEqual(created.rubric_scale_max, 5)
        self.assertIn("Problem solving", created.body)

    def test_teach_material_submissions_supports_rubric_responses(self):
        classroom = Class.objects.create(name="Rubric Review", join_code="RBR12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        rubric = Material.objects.create(
            module=module,
            title="Session rubric",
            type=Material.TYPE_RUBRIC,
            body="Problem solving\nCode quality",
            rubric_scale_max=4,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        StudentMaterialResponse.objects.create(
            material=rubric,
            student=student,
            rubric_scores=[4, 3],
            rubric_feedback="Strong growth this week.",
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/material/{rubric.id}/submissions")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Responses")
        self.assertContains(resp, "Scale 1-4")
        self.assertContains(resp, "Strong growth this week.")
