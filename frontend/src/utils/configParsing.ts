export function parseStepEntries(
  entries: Record<string, Record<string, unknown>>,
): {
  config: Record<string, Record<string, unknown>>;
  enabled: Record<string, boolean>;
} {
  const config: Record<string, Record<string, unknown>> = {};
  const enabled: Record<string, boolean> = {};
  for (const [name, cfg] of Object.entries(entries)) {
    const isEnabled = (cfg as Record<string, unknown>).enabled === true;
    enabled[name] = isEnabled;
    const params = { ...cfg } as Record<string, unknown>;
    delete params.enabled;
    config[name] = params as Record<string, Record<string, unknown>>;
  }
  return { config, enabled };
}

export function buildConfigPayload(
  names: string[],
  configMap: Record<string, Record<string, unknown>>,
  enabledMap: Record<string, boolean>,
  includeDisabled = false,
): Record<string, Record<string, unknown>> {
  const result: Record<string, Record<string, unknown>> = {};
  for (const name of names) {
    const enabled = enabledMap[name] ?? false;
    if (includeDisabled || enabled) {
      result[name] = { ...configMap[name], enabled };
    }
  }
  return result;
}
