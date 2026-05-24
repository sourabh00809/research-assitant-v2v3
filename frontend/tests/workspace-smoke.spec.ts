import { expect, test } from "@playwright/test";

test("renders seeded workspace and supervised agent controls", async ({ page, request }, testInfo) => {
  const projectName = `Smoke Workspace ${Date.now()}`;

  await page.goto("/app");
  await expect(page.getByRole("heading", { name: "AI Scientist Workspace" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Legacy UI" })).toHaveAttribute("href", "/legacy");

  await page.getByPlaceholder("email").fill(`owner+${Date.now()}@example.com`);
  await page.getByRole("button", { name: /Sign up \/ refresh|Refreshing/ }).click();
  await expect(page.getByText(/Workspace ready|session refreshed|signed in/i)).toBeVisible();

  await page.getByPlaceholder("New project name").fill(projectName);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("combobox")).toContainText(projectName);
  await page.getByRole("combobox").selectOption({ label: projectName });
  const projectId = await page.getByRole("combobox").inputValue();

  const runResponse = await request.post(`/api/projects/${projectId}/questions/run`, {
    data: {
      question: "What is the evidence that autonomous research agents can improve scientific discovery workflows?",
      max_papers: 4,
      use_memory: true,
    },
  });
  expect(runResponse.ok()).toBeTruthy();
  const runBody = await runResponse.json();

  const planResponse = await request.post(`/api/projects/${projectId}/experiment-plans`, {
    data: { brief_id: runBody.brief.id },
  });
  expect(planResponse.ok()).toBeTruthy();

  await page.reload();
  await page.getByRole("combobox").selectOption({ label: projectName });
  await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();
  await expect(page.getByText("seed_science_001").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Experiment Plans" })).toBeVisible();
  await expect(page.getByText(/Experiment Plan:/).first()).toBeVisible();

  await page.getByRole("button", { name: "Runner" }).click();
  await expect(page.getByText(/Runner agent created|Agent step recorded|Workspace ready/i)).toBeVisible();
  await page.getByRole("button", { name: "Run step" }).click();
  await expect(page.getByRole("button", { name: "Approve" }).first()).toBeVisible();
  await page.getByRole("button", { name: "Approve" }).first().click();
  await expect(page.getByText("Approval recorded for the supervised run.")).toBeVisible();

  await expect(page.getByRole("heading", { name: "Platform Health" })).toBeVisible();
  await page.getByRole("button", { name: /Database/ }).click();
  await expect(page.getByText(/sqlite|local/i).first()).toBeVisible();

  await page.screenshot({
    fullPage: true,
    path: testInfo.outputPath(`workspace-${testInfo.project.name}.png`),
  });
});
