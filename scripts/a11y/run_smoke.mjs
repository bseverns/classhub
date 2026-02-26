import AxeBuilder from "@axe-core/playwright";
import { chromium } from "playwright";

const baseUrl = (process.env.A11Y_BASE_URL || "http://localhost").trim().replace(/\/$/, "");
const teacherSessionKey = (process.env.A11Y_TEACHER_SESSION_KEY || "").trim();
const classIdRaw = (process.env.A11Y_CLASS_ID || "").trim();
const classId = Number.parseInt(classIdRaw, 10);
const timeoutMs = Number.parseInt(process.env.A11Y_TIMEOUT_MS || "30000", 10);
const failImpactRaw = (process.env.A11Y_FAIL_IMPACT || "critical").trim().toLowerCase();
const impactRank = {
  minor: 1,
  moderate: 2,
  serious: 3,
  critical: 4,
};
const failImpactThreshold = impactRank[failImpactRaw] || impactRank.critical;

const routes = [
  { name: "Student Join", path: "/", auth: "none" },
  { name: "Teacher Home", path: "/teach", auth: "teacher" },
  { name: "Teacher Lessons", path: "/teach/lessons", auth: "teacher" },
];

if (Number.isFinite(classId) && classId > 0) {
  routes.push(
    { name: "Teacher Class Dashboard", path: `/teach/class/${classId}`, auth: "teacher" },
    { name: "Certificate Eligibility", path: `/teach/class/${classId}/certificate-eligibility`, auth: "teacher" }
  );
}

function violationPriority(violation) {
  return impactRank[String(violation?.impact || "minor").toLowerCase()] || 0;
}

function formatTarget(node) {
  if (!node?.target || !Array.isArray(node.target) || !node.target.length) {
    return "(no target)";
  }
  return node.target.join(" ");
}

async function runRoute(page, route) {
  const url = `${baseUrl}${route.path}`;
  const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: timeoutMs });
  if (!response) {
    throw new Error(`${route.name}: no response from ${url}`);
  }
  const status = response.status();
  if (status >= 400) {
    throw new Error(`${route.name}: ${url} returned HTTP ${status}`);
  }

  const finalUrl = page.url();
  if (route.auth === "teacher") {
    const blockedByLogin = finalUrl.includes("/teach/login") || finalUrl.includes("/admin/login");
    if (blockedByLogin) {
      throw new Error(`${route.name}: expected authenticated teacher view but was redirected to ${finalUrl}`);
    }
  }

  await page.waitForTimeout(250);
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();

  const sortedViolations = [...results.violations].sort((a, b) => violationPriority(b) - violationPriority(a));
  const failViolations = sortedViolations.filter((violation) => violationPriority(violation) >= failImpactThreshold);

  return {
    route,
    totalViolations: sortedViolations.length,
    failViolations,
  };
}

function printRouteSummary(result) {
  const failCount = result.failViolations.length;
  console.log(`[a11y] ${result.route.name}: total=${result.totalViolations}, fail-threshold=${failCount}`);
  if (!failCount) return;

  for (const violation of result.failViolations) {
    const impact = String(violation.impact || "unknown");
    console.log(`  - [${impact}] ${violation.id}: ${violation.description}`);
    const firstNodes = Array.isArray(violation.nodes) ? violation.nodes.slice(0, 3) : [];
    for (const node of firstNodes) {
      console.log(`      selector: ${formatTarget(node)}`);
      if (node.failureSummary) {
        const summary = String(node.failureSummary).trim().split("\n").slice(0, 2).join(" ");
        console.log(`      detail: ${summary}`);
      }
    }
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();

  if (teacherSessionKey) {
    await context.addCookies([
      {
        name: "sessionid",
        value: teacherSessionKey,
        url: baseUrl,
        path: "/",
        sameSite: "Lax",
      },
    ]);
  }

  const page = await context.newPage();
  const results = [];

  for (const route of routes) {
    if (route.auth === "teacher" && !teacherSessionKey) {
      console.log(`[a11y] SKIP ${route.name}: no A11Y_TEACHER_SESSION_KEY provided`);
      continue;
    }
    const result = await runRoute(page, route);
    results.push(result);
    printRouteSummary(result);
  }

  await context.close();
  await browser.close();

  const totalFailViolations = results.reduce((acc, row) => acc + row.failViolations.length, 0);
  if (totalFailViolations > 0) {
    throw new Error(`[a11y] FAIL: found ${totalFailViolations} violation(s) at ${failImpactRaw}+ impact`);
  }

  console.log(`[a11y] PASS: no ${failImpactRaw}+ violations across ${results.length} scanned route(s)`);
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(1);
});
