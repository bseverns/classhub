import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const baseUrl = (process.env.A11Y_BASE_URL || "http://localhost:8000").trim().replace(/\/$/, "");
const teacherSessionKey = (process.env.A11Y_TEACHER_SESSION_KEY || "").trim();
const classIdRaw = (process.env.A11Y_CLASS_ID || "").trim();
const classId = Number.parseInt(classIdRaw, 10);
const timeoutMs = Number.parseInt(process.env.A11Y_TIMEOUT_MS || "30000", 10);
const outDir = path.resolve(process.env.A11Y_CAPTURE_OUT_DIR || "artifacts/press_capture_session");

const routes = [
  { filename: "01-student-join.png", path: "/", auth: "none" },
  { filename: "03-teacher-dashboard.png", path: "/teach", auth: "teacher" },
  { filename: "04-teacher-lesson-tracker.png", path: "/teach/lessons", auth: "teacher" },
];

if (Number.isFinite(classId) && classId > 0) {
  routes.push(
    { filename: "11-invite-only-enrollment.png", path: `/teach/class/${classId}`, auth: "teacher" },
    {
      filename: "12-certificate-eligibility.png",
      path: `/teach/class/${classId}/certificate-eligibility`,
      auth: "teacher",
    }
  );
}

async function captureRoute(page, route) {
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
  await page.setViewportSize({ width: 1400, height: 800 });
  await page.screenshot({ path: path.join(outDir, route.filename), fullPage: false });
  console.log(`[capture] wrote ${route.filename} <- ${finalUrl}`);
}

async function main() {
  await fs.mkdir(outDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1400, height: 800 },
    deviceScaleFactor: 1,
  });

  if (teacherSessionKey) {
    await context.addCookies([
      {
        name: "sessionid",
        value: teacherSessionKey,
        url: baseUrl,
        sameSite: "Lax",
      },
    ]);
  }

  const page = await context.newPage();
  for (const route of routes) {
    if (route.auth === "teacher" && !teacherSessionKey) {
      console.log(`[capture] SKIP ${route.filename}: no A11Y_TEACHER_SESSION_KEY provided`);
      continue;
    }
    await captureRoute(page, route);
  }

  await context.close();
  await browser.close();
  console.log(`[capture] session complete: ${outDir}`);
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(1);
});
