# Curriculum Operations

This guide explains how to import markdown coursepacks into the database and assign them to teachers.

## Intent

The curriculum is written in YAML/Markdown under `services/classhub/content/courses/`. To serve these to students, Class Hub imports the manifests into a structured `Class` database object. This document shows how to safely create, update, and manage those records in production.

## 1. Import or create a classroom

To turn an authored coursepack into an auditable database Class:

```bash
cd /srv/lms/app
git pull origin main
./scripts/import_coursepacks.sh
```

**Verification:**
`docker compose exec classhub_web python manage.py shell -c "from hub.models import Class; print(Class.objects.count())"` should return a number greater than 0.

### Specific imports

If you only want to import a single course (for example, `swarm_aesthetics`):

```bash
cd /srv/lms/app/compose
docker compose exec classhub_web python manage.py import_coursepack --course-slug swarm_aesthetics --create-class
```

## 2. Pushing curriculum updates

If you modify the markdown files or `course.yaml` manifest in `content/courses` safely update the existing classroom to reflect the latest module structure without losing student data:

```bash
cd /srv/lms/app/compose
docker compose exec classhub_web python manage.py import_coursepack --course-slug swarm_aesthetics --replace
```

**Boundary Note:**
The `--replace` flag drops existing `Module` and `Material` layout records for the class and recreates them. It does **not** delete student file submissions (which are bound to the `Classroom` and `Student` identity directly). 

**Failure Mode:**
Running the command *without* `--replace` on an existing class is additive: you will end up with duplicate Sessions and Modules. 

**Recovery:**
Run the command again *with* `--replace` to flush the duplicates and restore a clean 1:1 mapping of the manifest.

## 3. Pairing a class with a teacher

Once a Class is imported, students cannot join until a staff member takes ownership of it. If you imported the class on the command line, it starts unassigned.

1. Navigate to your server's `/admin` portal.
2. Log in using your Django Superuser or Staff credentials (OTP required).
3. Under **Hub**, click **Class staff assignments**.
4. Click **Add class staff assignment**.
5. Select the imported `Class` and the `User` (the teacher).
6. Save.

**Verification:**
When the teacher logs into `/teach`, they should now see the imported Class on their roster dashboard.
