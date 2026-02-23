// Author: Dr Diego Malpica MD
import { promises as fs } from "fs";
import path from "path";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

interface ChangelogCategory {
  category: string;
  items: string[];
}

interface ChangelogReleaseSummary {
  version: string;
  date: string;
  categories: ChangelogCategory[];
}

function extractBulletTitle(line: string): string {
  const raw = line.replace(/^- /, "").trim();
  const boldMatch = raw.match(/^\*\*(.+?)\*\*/);
  if (boldMatch && boldMatch[1]) {
    return boldMatch[1].trim();
  }
  return raw.replace(/`/g, "").trim();
}

function parseLatestRelease(content: string): ChangelogReleaseSummary | null {
  const lines = content.split(/\r?\n/);
  let releaseStart = -1;
  let version = "";
  let date = "";

  for (let idx = 0; idx < lines.length; idx += 1) {
    const match = lines[idx].match(/^##\s+\[([^\]]+)\]\s*-\s*(.+)$/);
    if (match) {
      releaseStart = idx;
      version = match[1].trim();
      date = match[2].trim();
      break;
    }
  }

  if (releaseStart < 0) {
    return null;
  }

  const categories: ChangelogCategory[] = [];
  let currentCategory: ChangelogCategory | null = null;

  for (let idx = releaseStart + 1; idx < lines.length; idx += 1) {
    const line = lines[idx];
    if (/^##\s+\[/.test(line)) {
      break;
    }
    const categoryMatch = line.match(/^###\s+(.+)$/);
    if (categoryMatch) {
      currentCategory = { category: categoryMatch[1].trim(), items: [] };
      categories.push(currentCategory);
      continue;
    }
    if (!currentCategory) {
      continue;
    }
    if (/^- /.test(line)) {
      const title = extractBulletTitle(line);
      if (title) {
        currentCategory.items.push(title);
      }
    }
  }

  return {
    version,
    date,
    categories,
  };
}

async function pathExists(candidatePath: string): Promise<boolean> {
  try {
    await fs.access(candidatePath);
    return true;
  } catch {
    return false;
  }
}

async function resolveChangelogPath(): Promise<string | null> {
  const cwd = process.cwd();
  const candidates = [
    path.join(cwd, "CHANGELOG.md"),
    path.join(cwd, "..", "CHANGELOG.md"),
    path.join(cwd, "..", "..", "CHANGELOG.md"),
  ];
  for (const candidate of candidates) {
    if (await pathExists(candidate)) {
      return candidate;
    }
  }
  return null;
}

export async function GET() {
  try {
    const changelogPath = await resolveChangelogPath();
    if (!changelogPath) {
      return NextResponse.json(
        { ok: false, release: null, error: "CHANGELOG.md not found" },
        { status: 404 },
      );
    }
    const content = await fs.readFile(changelogPath, "utf-8");
    const release = parseLatestRelease(content);
    if (!release) {
      return NextResponse.json(
        { ok: false, release: null, error: "No release section found in changelog" },
        { status: 422 },
      );
    }
    return NextResponse.json(
      {
        ok: true,
        release,
      },
      {
        status: 200,
        headers: {
          "Cache-Control": "no-store, max-age=0",
        },
      },
    );
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unexpected changelog parsing error";
    return NextResponse.json(
      { ok: false, release: null, error: message },
      { status: 500 },
    );
  }
}

