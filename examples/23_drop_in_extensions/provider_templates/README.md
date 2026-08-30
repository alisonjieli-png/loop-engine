# Provider route templates

These are disabled-by-location templates. Loop Engine does not scan this
directory. Copy a reviewed file into an extension root's `providers/` folder,
set the named credential, and inspect it before authorizing a probe.

```bash
mkdir -p .loop-engine/extensions/providers
cp examples/23_drop_in_extensions/provider_templates/zai-glm47-flash.yaml \
  .loop-engine/extensions/providers/

loop-engine extensions providers
loop-engine models inventory
```

Pricing and model availability can change. Review the cited provider source
before copying. `zero_price` routes may activate automatically when their key
exists. Recurring quotas, rolling credits, trial credits, paid routes, and
unknown prices require `--allow-paid-extension-routes` because billing may
begin after the allowance.

No template grants model-call or spending authority.
