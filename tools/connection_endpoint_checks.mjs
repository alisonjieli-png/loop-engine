/* Exercise copied settings in the real browser. The provider record is a local fixture; no external connection is made. */
export async function runConnectionEndpointChecks(context, base, check) {
  const resource = "https://canonical.example.invalid/mcp";
  const variants = [
    {name:"canonical_resource", resource, slow:"capabilities", expected:resource},
    {name:"canonical_resource_before_recipes", resource, slow:"recipes", expected:resource},
    {name:"malformed_resource", resource:"https://canonical.example.invalid/mcp?secret=wrong", expected:null},
    {name:"insecure_resource", resource:"http://canonical.example.invalid/mcp", expected:null},
    {name:"unknown_resource_contract", resource, version:"service_oauth_server_capabilities/v99", expected:null},
    {name:"removed_canonical_guard", resource, expected:resource, mutant:true}
  ];
  for (const variant of variants) {
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.name));
    let mutated = false;
    await page.route(base + "/api/v1/capabilities", async route => {
      const response = await route.fetch(), body = await response.json();
      body.result.authorization_server = {...body.result.authorization_server, available:true,
        record_type:variant.version || "service_oauth_server_capabilities/v1", resource:variant.resource};
      if (variant.slow === "capabilities") await new Promise(resolve => setTimeout(resolve, 100));
      await route.fulfill({response, json:body});
    });
    await page.route(url => url.origin === base && url.pathname === "/assets/client-recipes.json", async route => {
      const response = await route.fetch();
      if (variant.slow === "recipes") await new Promise(resolve => setTimeout(resolve, 100));
      await route.fulfill({response});
    });
    if (variant.mutant) await page.route(url => url.origin === base && url.pathname === "/assets/client-access.js", async route => {
      const response = await route.fetch(), original = await response.text();
      const changed = original.replace("? oauth.resource : null", '? origin + "/mcp" : null');
      mutated = changed !== original;
      await route.fulfill({response, body:changed});
    });
    await page.goto(base + "/connect");
    await page.waitForFunction(() => document.querySelector("#service-status").textContent.includes("Service available")
      && document.querySelectorAll('#client-tabs [role="tab"]').length > 0);
    const current = await page.locator("#protocol-url").inputValue();
    const setup = await page.locator("#setup-endpoint").textContent();
    let holds;
    if (variant.expected) {
      holds = current === variant.expected && setup === variant.expected
        && await page.locator("#setup-oauth-endpoint").textContent() === variant.expected;
      for (const tab of await page.locator('#client-tabs [role="tab"]').all()) {
        await tab.click();
        holds = holds && (await page.locator("#client-configuration").textContent()).includes(variant.expected)
          && !await page.locator("#copy-configuration").isDisabled();
      }
    } else {
      holds = current === "" && setup === "Connection address unavailable"
        && await page.locator("#copy-endpoint").isDisabled() && await page.locator("#copy-configuration").isDisabled()
        && await page.locator("#setup-oauth").isHidden()
        && !(await page.locator("#client-configuration").textContent()).includes(variant.resource);
    }
    check("connection_endpoint_" + variant.name, variant.mutant ? mutated && !holds : holds, {errors});
    check("connection_endpoint_" + variant.name + "_has_no_script_error", errors.length === 0);
    await page.close();
  }
}
