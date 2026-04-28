import yaml from "js-yaml";
import { useCallback } from "react";

export interface ParsedYamlConfig {
  config: Record<string, Record<string, unknown>>;
  enabled: Record<string, boolean>;
}

export function useYamlConfig() {
  const parseConfig = useCallback((content: string, topKey: string): ParsedYamlConfig => {
    const parsed = yaml.load(content) as Record<string, unknown>;
    const section = (parsed?.[topKey] ?? parsed) as Record<string, unknown>;
    const config: Record<string, Record<string, unknown>> = {};
    const enabled: Record<string, boolean> = {};
    for (const [key, val] of Object.entries(section)) {
      if (key === "enabled" || key === "debug") continue;
      if (typeof val === "object" && val !== null) {
        const stepVal = { ...(val as Record<string, unknown>) };
        const isEnabled = Boolean(stepVal.enabled ?? false);
        delete stepVal.enabled;
        config[key] = stepVal;
        enabled[key] = isEnabled;
      }
    }
    return { config, enabled };
  }, []);

  return parseConfig;
}
