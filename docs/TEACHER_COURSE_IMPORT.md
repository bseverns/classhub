# Syllabus Import Guide (Teachers)

Staff users can ingest syllabus sources directly into the ClassHub platform using the **Import Syllabus Source** tool found on the Teacher Portal home page (`/teach`).

> [!NOTE]
> This is a non-technical guide utilizing the teacher portal web interface. For rigorous CLI SDK development, see [COURSE_AUTHORING.md](COURSE_AUTHORING.md).

## Accepted Source Types
- `.md` session plan file
- `.docx` session plan file
- `.zip` bundle containing source docs and directories

## Import Process

When running the import, you will see a form allowing several optional inputs:
- **Course slug** (if blank, derived from title)
- **Course title override**
- **Default UI level** (choose between `elementary`, `secondary`, `advanced`)
- **Session parser mode** (leave at `auto` unless you have strict needs: `template`, `verbose`)
- **Overview file** (`.md` or `.docx`) when uploading a single session plan
- **Overwrite existing course folder** (toggles updating vs generating a new entry)

### Zip Handling Rules
If you upload an entire `.zip` bundle of curriculum material:
- The importer automatically scans `.md` and `.docx` files in the archive.
- It prioritizes files located inside `sessions/` or `lessons/` folders and files named things like `session01_*`.
- It derives the global overview and title metadata from files titled `COURSE_DESCRIPTION.md`, files containing `overview`, `syllabus`, or standard `README`s.
- Support images named with session prefixes will be mapped automatically (e.g. `01-circuit-layout.png`). They will be attached as Lesson Assets directly into the module links within the system.

*(For changing exact syllabus layout attributes like age-bands or fine-tuning helper variables, please consult the system administrator workflow in `COURSE_AUTHORING.md`)*
