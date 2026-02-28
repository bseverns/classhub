import os
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from hub.models import Class, Module, Material, StudentIdentity, LessonAssetFolder, LessonAsset

class MediaIsolationTests(TestCase):
    def setUp(self):
        self.client_a = Client()
        self.class_a = Class.objects.create(name="Class A")
        self.student_a = StudentIdentity.objects.create(classroom=self.class_a, display_name="Alice")
        
        self.client_b = Client()
        self.class_b = Class.objects.create(name="Class B")
        self.student_b = StudentIdentity.objects.create(classroom=self.class_b, display_name="Bob")

        # Simulate login by setting the student_id in the session
        session_a = self.client_a.session
        session_a["student_id"] = self.student_a.id
        session_a["class_id"] = self.class_a.id
        session_a["session_epoch"] = self.class_a.session_epoch
        session_a.save()
        
        session_b = self.client_b.session
        session_b["student_id"] = self.student_b.id
        session_b["class_id"] = self.class_b.id
        session_b["session_epoch"] = self.class_b.session_epoch
        session_b.save()

        # Class A has access to Course Slug "math-101", Lesson Slug "intro"
        self.module_a = Module.objects.create(classroom=self.class_a, title="Math Week 1")
        Material.objects.create(
            module=self.module_a, 
            type=Material.TYPE_LINK, 
            title="Math Lesson",
            url="/course/math-101/intro"
        )
        
        # Create a lesson asset restricted to math-101 / intro
        self.folder = LessonAssetFolder.objects.create(path="math_assets")
        self.asset = LessonAsset.objects.create(
            folder=self.folder,
            course_slug="math-101",
            lesson_slug="intro",
            title="Math Worksheet",
            file=SimpleUploadedFile("worksheet.pdf", b"file_content", content_type="application/pdf")
        )

    def test_student_can_view_enrolled_asset(self):
        response = self.client_a.get(f"/lesson-asset/{self.asset.id}/download")
        # Allowed because class A has a material link to /course/math-101/intro
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_view_unenrolled_asset(self):
        response = self.client_b.get(f"/lesson-asset/{self.asset.id}/download")
        # Forbidden because class B does NOT have a material link for this asset.
        self.assertEqual(response.status_code, 403)
