import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const python = path.join(
  root,
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
if (!existsSync(python)) {
  console.error(
    "Create .venv and install apps/backend/requirements.txt first. See README.md.",
  );
  process.exit(1);
}
const migration = spawnSync(
  python,
  ["-m", "alembic", "-c", "apps/backend/alembic.ini", "upgrade", "head"],
  { cwd: root, stdio: "inherit" },
);
if (migration.status !== 0) process.exit(migration.status || 1);
const processes = [
  spawn(
    python,
    [
      "-m",
      "uvicorn",
      "app.main:app",
      "--app-dir",
      "apps/backend",
      "--host",
      "127.0.0.1",
      "--port",
      "8000",
    ],
    { cwd: root, stdio: "inherit" },
  ),
  spawn(
    process.execPath,
    [
      path.join(root, "node_modules/next/dist/bin/next"),
      "dev",
      "-H",
      "127.0.0.1",
      "-p",
      "3000",
    ],
    { cwd: path.join(root, "apps/web"), stdio: "inherit" },
  ),
];
let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const p of processes) p.kill();
  setTimeout(() => process.exit(code), 300).unref();
}
for (const p of processes) {
  p.on("error", (error) => {
    console.error(error.message);
    stop(1);
  });
  p.on("exit", (code) => {
    if (!stopping) stop(code || 0);
  });
}
process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());
