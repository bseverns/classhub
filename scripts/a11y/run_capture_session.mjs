import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const baseUrl = (process.env.A11Y_BASE_URL || "http://localhost:8000").trim().replace(/\/$/, "");
const timeoutMs = Number.parseInt(process.env.A11Y_TIMEOUT_MS || "30000", 10);
const outDir = path.resolve(process.env.A11Y_CAPTURE_OUT_DIR || "artifacts/press_capture_session");
const fullPage = String(process.env.A11Y_CAPTURE_FULL_PAGE || "1").trim() !== "0";

const teacherSessionKey = (process.env.A11Y_TEACHER_SESSION_KEY || "").trim();
const compactStudentSessionKey = (process.env.A11Y_COMPACT_STUDENT_SESSION_KEY || "").trim();
const standardStudentSessionKey = (process.env.A11Y_STANDARD_STUDENT_SESSION_KEY || "").trim();
const expandedStudentSessionKey = (process.env.A11Y_EXPANDED_STUDENT_SESSION_KEY || "").trim();

const compactClassId = Number.parseInt((process.env.A11Y_COMPACT_CLASS_ID || "").trim(), 10);
const compactLessonUrl = (process.env.A11Y_COMPACT_LESSON_URL || "").trim();
const compactUploadMaterialId = Number.parseInt((process.env.A11Y_COMPACT_UPLOAD_MATERIAL_ID || "").trim(), 10);
const compactGalleryMaterialId = Number.parseInt((process.env.A11Y_COMPACT_GALLERY_MATERIAL_ID || "").trim(), 10);

const authSessions = {
  none: "",
  teacher: teacherSessionKey,
  student_compact: compactStudentSessionKey,
  student_standard: standardStudentSessionKey,
  student_expanded: expandedStudentSessionKey,
};

function buildCatalog() {
  const routes = [
    { filename: "01-student-join.png", path: "/", auth: "none" },
    { filename: "02-student-class-view.png", path: "/student", auth: "student_standard", actions: ["open-first-module"] },
    { filename: "03-teacher-dashboard.png", path: "/teach?portal_mode=day", auth: "teacher" },
    { filename: "04-teacher-lesson-tracker.png", path: "/teach/lessons", auth: "teacher" },
    { filename: "07-admin-login.png", path: "/admin/login/", auth: "none" },
    { filename: "09-teacher-profile-tab.png", path: "/teach?profile_tab=1", auth: "teacher" },
    { filename: "10-org-management-tab.png", path: "/teach?portal_mode=admin&advanced=1", auth: "teacher" },
    { filename: "11-invite-only-enrollment.png", path: compactClassId ? `/teach/class/${compactClassId}` : "", auth: "teacher" },
    {
      filename: "12-certificate-eligibility.png",
      path: compactClassId ? `/teach/class/${compactClassId}/certificate-eligibility` : "",
      auth: "teacher",
    },
    { filename: "14-student-compact-view.png", path: "/student", auth: "student_compact" },
    { filename: "16-student-standard-view.png", path: "/student", auth: "student_standard" },
    { filename: "17-student-expanded-view.png", path: "/student", auth: "student_expanded" },
    {
      filename: "18-teacher-landing-editor.png",
      path: compactClassId ? `/teach/class/${compactClassId}` : "",
      auth: "teacher",
      actions: ["open-landing-editor"],
    },
    { filename: "19-rbac-tools-tab.png", path: "/teach?portal_mode=policy&advanced=1", auth: "teacher" },
    { filename: "20-data-lifespan-evidence.png", path: "/teach/data-lifespan", auth: "teacher" },
  ];

  if (compactLessonUrl) {
    routes.push(
      {
        filename: "05-lesson-with-helper.png",
        path: compactLessonUrl,
        auth: "student_compact",
        actions: ["open-helper"],
      },
      {
        filename: "15-lesson-helper-collapsed.png",
        path: compactLessonUrl,
        auth: "student_compact",
      }
    );
  }

  const uploadMaterialId = Number.isFinite(compactGalleryMaterialId) && compactGalleryMaterialId > 0
    ? compactGalleryMaterialId
    : compactUploadMaterialId;
  if (Number.isFinite(uploadMaterialId) && uploadMaterialId > 0) {
    routes.push({
      filename: "06-submission-dropbox.png",
      path: `/material/${uploadMaterialId}/upload`,
      auth: "student_compact",
    });
  }

  return routes
    .filter((route) => route.path)
    .sort((a, b) => a.filename.localeCompare(b.filename, undefined, { numeric: true }));
}

async function waitForUiSettled(page) {
  await page.waitForTimeout(400);
}

async function clickIfPresent(page, selector) {
  const target = page.locator(selector).first();
  if (await target.count()) {
    await target.click();
    await waitForUiSettled(page);
  }
}

async function applyActions(page, actions = []) {
  for (const action of actions) {
    if (action === "open-helper") {
      await clickIfPresent(page, ".helper-shell > summary");
      continue;
    }
    if (action === "open-landing-editor") {
      await clickIfPresent(page, "#section-landing-page > summary");
      continue;
    }
    if (action === "open-first-module") {
      await clickIfPresent(page, "details.card.module > summary");
      continue;
    }
  }
}

async function buildContext(browser, authKey) {
  const context = await browser.newContext({
    viewport: { width: 1400, height: 800 },
    deviceScaleFactor: 1,
  });
  const sessionKey = authSessions[authKey] || "";
  if (sessionKey) {
    await context.addCookies([
      {
        name: "sessionid",
        value: sessionKey,
        url: baseUrl,
        sameSite: "Lax",
      },
    ]);
  }
  return context;
}

async function captureRoute(browser, route) {
  const context = await buildContext(browser, route.auth);
  const page = await context.newPage();
  const url = `${baseUrl}${route.path}`;
  const response = await page.goto(url, { waitUntil: "networkidle", timeout: timeoutMs });
  if (!response) {
    throw new Error(`${route.filename}: no response from ${url}`);
  }
  if (response.status() >= 400) {
    throw new Error(`${route.filename}: ${url} returned HTTP ${response.status()}`);
  }

  const finalUrl = page.url();
  if (route.auth === "teacher") {
    const blockedByLogin = finalUrl.includes("/teach/login") || finalUrl.includes("/admin/login");
    if (blockedByLogin) {
      throw new Error(`${route.filename}: expected authenticated teacher view but was redirected to ${finalUrl}`);
    }
  }
  if (route.auth.startsWith("student_") && finalUrl.endsWith("/")) {
    throw new Error(`${route.filename}: expected student view but landed on join page`);
  }

  await applyActions(page, route.actions);
  await page.screenshot({ path: path.join(outDir, route.filename), fullPage });
  await context.close();
  return { filename: route.filename, url: finalUrl };
}

async function main() {
  await fs.mkdir(outDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const captured = [];
  const skipped = [];
  const catalog = buildCatalog();

  for (const route of catalog) {
    if (route.auth !== "none" && !authSessions[route.auth]) {
      skipped.push({ filename: route.filename, reason: `missing auth session for ${route.auth}` });
      console.log(`[capture] SKIP ${route.filename}: missing auth session for ${route.auth}`);
      continue;
    }
    try {
      const result = await captureRoute(browser, route);
      captured.push(result);
      console.log(`[capture] wrote ${result.filename} <- ${result.url}`);
    } catch (error) {
      skipped.push({ filename: route.filename, reason: error instanceof Error ? error.message : String(error) });
      console.log(`[capture] SKIP ${route.filename}: ${skipped.at(-1).reason}`);
    }
  }

  await fs.writeFile(
    path.join(outDir, "capture_manifest.json"),
    JSON.stringify(
      {
        baseUrl,
        fullPage,
        captured,
        skipped,
      },
      null,
      2
    ) + "\n"
  );

  await browser.close();
  console.log(`[capture] session complete: ${outDir}`);
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(1);
});
