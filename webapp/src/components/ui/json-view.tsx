"use client";

import { useMemo, useState } from "react";

type JsonValue = unknown;

function tryParse(value: JsonValue): JsonValue {
  if (typeof value === "string") {
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }
  return value;
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function JsonNode({
  name,
  value,
  depth,
  path,
  defaultCollapsedDepth,
}: {
  name?: string;
  value: JsonValue;
  depth: number;
  path: string;
  defaultCollapsedDepth: number;
}) {
  const isArray = Array.isArray(value);
  const isObj = isRecord(value);
  const isContainer = isArray || isObj;
  // Default collapsed for containers at or beyond the configured depth
  const entries = isArray
    ? (value as unknown[]).map((v, i) => [String(i), v] as const)
    : isObj
    ? Object.entries(value as Record<string, unknown>)
    : [];
  const hasChildren = entries.length > 0;
  const [collapsed, setCollapsed] = useState(
    isContainer && depth >= defaultCollapsedDepth
  );

  const header = useMemo(() => {
    if (isArray) return `Array(${(value as unknown[]).length})`;
    if (isObj) return `Object(${Object.keys(value as object).length})`;
    return undefined;
  }, [isArray, isObj, value]);

  const label = name !== undefined ? `${name}: ` : "";

  if (!isContainer) {
    let rendered: string;
    if (typeof value === "string") rendered = JSON.stringify(value);
    else rendered = String(value);
    return (
      <div className="text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span>{rendered}</span>
      </div>
    );
  }

  return (
    <div className="text-xs">
      {isContainer && hasChildren ? (
        <details
          open={!collapsed}
          onToggle={(e) =>
            setCollapsed(!(e.currentTarget as HTMLDetailsElement).open)
          }
        >
          <summary className="text-xs cursor-pointer inline-flex items-center gap-1 align-middle">
            <span className="inline-block w-3 text-center">
              {collapsed ? "▶" : "▼"}
            </span>
            <span className="text-muted-foreground">{label}</span>
            <span className="font-mono">{isArray ? "[" : "{"}</span>
            <span className="text-muted-foreground ml-1">{header}</span>
            <span className="font-mono">{isArray ? "]" : "}"}</span>
          </summary>
          <div className="ml-4 mt-1 border-l pl-3">
            {entries.map(([k, v]) => (
              <JsonNode
                key={`${path}.${k}`}
                name={isArray ? undefined : k}
                value={v}
                depth={depth + 1}
                path={`${path}.${k}`}
                defaultCollapsedDepth={defaultCollapsedDepth}
              />
            ))}
          </div>
        </details>
      ) : (
        <div className="inline-flex items-center gap-1 align-middle">
          <span className="text-muted-foreground">{label}</span>
          <span className="font-mono">{isArray ? "[" : "{"}</span>
          <span className="text-muted-foreground ml-1">{header}</span>
          <span className="font-mono">{isArray ? "]" : "}"}</span>
        </div>
      )}
    </div>
  );
}

export function JsonView({
  value,
  defaultCollapsedDepth = 0,
}: {
  value: JsonValue;
  defaultCollapsedDepth?: number;
}) {
  const data = tryParse(value);
  return (
    <div className="text-xs mt-1">
      <JsonNode
        value={data}
        depth={0}
        path="$"
        defaultCollapsedDepth={defaultCollapsedDepth}
      />
    </div>
  );
}
