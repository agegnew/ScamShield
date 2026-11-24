import type { Graph } from "./api";

type Node = Graph["nodes"][number];
type Edge = Graph["edges"][number];

export type Campaign = {
  nodes: Node[];
  edges: Edge[];
  /** Distinct link types inside the group, most common first. */
  types: Edge["type"][];
  maxScore: number;
};

/** Split the scam network into linked groups (connected components) and lone domains. */
export function toCampaigns(g: Graph | undefined | null): { campaigns: Campaign[]; unlinked: Node[] } {
  if (!g) return { campaigns: [], unlinked: [] };
  const parent = new Map<string, string>(g.nodes.map((n) => [n.id, n.id]));
  const find = (x: string): string => {
    let r = x;
    while (parent.get(r) !== r) r = parent.get(r)!;
    let c = x;
    while (parent.get(c) !== r) {
      const next = parent.get(c)!;
      parent.set(c, r);
      c = next;
    }
    return r;
  };
  for (const e of g.edges) {
    if (!parent.has(e.source) || !parent.has(e.target)) continue;
    const a = find(e.source);
    const b = find(e.target);
    if (a !== b) parent.set(a, b);
  }

  const groups = new Map<string, Node[]>();
  for (const n of g.nodes) {
    const r = find(n.id);
    groups.set(r, [...(groups.get(r) ?? []), n]);
  }

  const campaigns: Campaign[] = [];
  const unlinked: Node[] = [];
  for (const members of groups.values()) {
    if (members.length < 2) {
      unlinked.push(...members);
      continue;
    }
    const ids = new Set(members.map((m) => m.id));
    const edges = g.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
    const counts = new Map<Edge["type"], number>();
    for (const e of edges) counts.set(e.type, (counts.get(e.type) ?? 0) + 1);
    campaigns.push({
      nodes: [...members].sort((a, b) => b.score - a.score),
      edges,
      types: [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([t]) => t),
      maxScore: Math.max(...members.map((m) => m.score)),
    });
  }
  campaigns.sort((a, b) => b.nodes.length - a.nodes.length || b.maxScore - a.maxScore);
  unlinked.sort((a, b) => b.score - a.score);
  return { campaigns, unlinked };
}

/** Demo pages served from the laptop show up as localhost or a private address. */
export function isLocalDemo(domain: string) {
  const d = domain.toLowerCase();
  return (
    d === "localhost" ||
    d.endsWith(".localhost") ||
    /^127\./.test(d) ||
    /^10\./.test(d) ||
    /^192\.168\./.test(d) ||
    /^172\.(1[6-9]|2\d|3[01])\./.test(d)
  );
}
