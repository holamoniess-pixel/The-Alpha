// ============================================================
//  SMART AGENT TASK RUNNER — TypeScript
//  Features:
//   - Sequential execution (waits for task N before N+1)
//   - Self-verification after every task
//   - Complexity detection (simple vs complex)
//   - Graceful error handling & user feedback
//   - Retry logic with exponential back-off
// ============================================================

import { execSync, exec } from "child_process";
import { promisify } from "util";
import * as fs from "fs";
import * as path from "path";

const execAsync = promisify(exec);

// ─────────────────────────────────────
//  TYPES
// ─────────────────────────────────────

export type TaskStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped";

export type TaskComplexity = "simple" | "moderate" | "complex";

export interface Task {
  id: string;
  name: string;
  description: string;
  type: "shell" | "file" | "search" | "app" | "custom";
  action: () => Promise<TaskResult>;
  /** How to verify the task actually worked */
  verify?: () => Promise<boolean>;
  /** Max retries before giving up */
  maxRetries?: number;
  /** Delay in ms between retries */
  retryDelay?: number;
  /** Timeout in ms — default 15000 */
  timeout?: number;
  complexity?: TaskComplexity;
  dependsOn?: string[]; // task IDs that must complete first
}

export interface TaskResult {
  success: boolean;
  output?: string;
  error?: string;
  duration?: number; // ms
}

export interface TaskRunRecord {
  task: Task;
  status: TaskStatus;
  result?: TaskResult;
  attempts: number;
  startedAt?: Date;
  completedAt?: Date;
}

// ─────────────────────────────────────
//  COMPLEXITY DETECTOR
//  Reads the task description / type and assigns
//  a complexity score before trying to run it.
// ─────────────────────────────────────

export class ComplexityDetector {
  private static readonly COMPLEX_KEYWORDS = [
    "install",
    "uninstall",
    "delete all",
    "format",
    "reboot",
    "registry",
    "system32",
    "sudo",
    "root",
    "chmod 777",
    "drop database",
    "rm -rf",
    "docker",
    "kubernetes",
    "compile",
    "build",
    "deploy",
    "migrate",
    "backup",
    "restore",
    "encrypt",
    "decrypt"
  ];

  private static readonly MODERATE_KEYWORDS = [
    "open",
    "launch",
    "create file",
    "write",
    "search",
    "read",
    "list",
    "rename",
    "move file",
    "copy",
    "download",
    "upload",
    "compress",
    "extract",
    "update",
    "configure",
    "install package",
    "run script",
    "test",
    "debug",
    "monitor"
  ];

  static detect(task: Task): TaskComplexity {
    if (task.complexity) return task.complexity; // honour explicit override

    const haystack = (task.description + " " + task.name).toLowerCase();

    if (
      ComplexityDetector.COMPLEX_KEYWORDS.some((kw) => haystack.includes(kw))
    ) {
      return "complex";
    }
    if (
      ComplexityDetector.MODERATE_KEYWORDS.some((kw) => haystack.includes(kw))
    ) {
      return "moderate";
    }
    return "simple";
  }
}

// ─────────────────────────────────────
//  TASK VERIFIER
//  Provides default verifiers when task author hasn't supplied one.
// ─────────────────────────────────────

export class TaskVerifier {
  /** Check a file exists */
  static fileExists(filePath: string): () => Promise<boolean> => {
    return async () => fs.existsSync(filePath);
  }

  /** Check a process is running (Linux/Mac) */
  static processRunning(processName: string): () => Promise<boolean> => {
    return async () => {
      try {
        const { stdout } = await execAsync(`pgrep -x "${processName}"`);
        return stdout.trim().length > 0;
      } catch {
        return false;
      }
    };
  }

  /** Check a URL is reachable */
  static urlReachable(url: string): () => Promise<boolean> => {
    return async () => {
      try {
        const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
        return res.ok;
      } catch {
        return false;
      }
    };
  }

  /** Check a directory exists and is writable */
  static directoryWritable(dirPath: string): () => Promise<boolean> => {
    return async () => {
      try {
        fs.accessSync(dirPath, fs.constants.W_OK);
        return true;
      } catch {
        return false;
      }
    };
  }

  /** Check if a command exists in PATH */
  static commandExists(command: string): () => Promise<boolean> => {
    return async () => {
      try {
        execSync(`which ${command}`, { stdio: 'ignore' });
        return true;
      } catch {
        return false;
      }
    };
  }

  /** Always returns true — use when there's nothing concrete to verify */
  static alwaysTrue(): () => Promise<boolean> => {
    return async () => true;
  }
}

// ─────────────────────────────────────
//  LOGGER
// ─────────────────────────────────────

class Logger {
  private static timestamp(): string {
    return new Date().toISOString().replace("T", " ").slice(0, 19);
  }

  static info(msg: string): void {
    console.log(`\x1b[36m[${this.timestamp()}] ℹ  ${msg}\x1b[0m`);
  }

  static success(msg: string): void {
    console.log(`\x1b[32m[${this.timestamp()}] ✅ ${msg}\x1b[0m`);
  }

  static warn(msg: string): void {
    console.log(`\x1b[33m[${this.timestamp()}] ⚠  ${msg}\x1b[0m`);
  }

  static error(msg: string): void {
    console.log(`\x1b[31m[${this.timestamp()}] ❌ ${msg}\x1b[0m`);
  }

  static task(msg: string): void {
    console.log(`\x1b[35m[${this.timestamp()}] 🔧 ${msg}\x1b[0m`);
  }
}

// ─────────────────────────────────────
//  CORE TASK RUNNER
// ─────────────────────────────────────

export class AgentTaskRunner {
  private queue: Task[] = [];
  private records = new Map<string, TaskRunRecord>();
  private isRunning = false;

  // ── Public API ──────────────────────

  /** Add one or more tasks to queue */
  addTask(...tasks: Task[]): this {
    for (const t of tasks) {
      this.queue.push(t);
      this.records.set(t.id, {
        task: t,
        status: "pending",
        attempts: 0,
      });
    }
    return this; // fluent
  }

  /** Run the full queue sequentially */
  async run(): Promise<Map<string, TaskRunRecord>> {
    if (this.isRunning) {
      Logger.warn("Runner is already executing. Call await runner.run() once.");
      return this.records;
    }

    this.isRunning = true;
    Logger.info(`Starting task queue — ${this.queue.length} task(s) to run.`);
    console.log("─".repeat(60));

    for (const task of this.queue) {
      const canRun = await this.checkDependencies(task);
      if (!canRun) {
        this.records.get(task.id)!.status = "skipped";
        Logger.warn(
          `Skipping "${task.name}" — one or more dependencies failed.`
        );
        continue;
      }

      await this.executeTask(task);

      // ★ Hard gate: do NOT proceed if task failed and has dependants
      const record = this.records.get(task.id)!;
      if (record.status === "failed") {
        const blocked = this.queue.filter(
          (t) => t.dependsOn?.includes(task.id) && t.id !== task.id
        );
        if (blocked.length) {
          Logger.warn(
            `"${task.name}" failed — ${blocked.length} dependent task(s) will be skipped.`
          );
        }
      }
    }

    this.isRunning = false;
    this.printSummary();
    return this.records;
  }

  // ── Private helpers ──────────────────────

  private async checkDependencies(task: Task): Promise<boolean> {
    if (!task.dependsOn?.length) return true;

    for (const depId of task.dependsOn) {
      const dep = this.records.get(depId);
      if (!dep || dep.status !== "completed") {
        return false;
      }
    }
    return true;
  }

  private async executeTask(task: Task): Promise<void> {
    const record = this.records.get(task.id)!;
    const complexity = ComplexityDetector.detect(task);
    const maxRetries = task.maxRetries ?? (complexity === "simple" ? 2 : 1);
    const timeout = task.timeout ?? 15000;

    Logger.task(
      `Running "${task.name}" [${complexity}] (max retries: ${maxRetries})`
    );
    record.status = "running";
    record.startedAt = new Date();

    // ── Complexity gate for very complex tasks ──
    if (complexity === "complex") {
      Logger.warn(
        `"${task.name}" is flagged as COMPLEX. Proceeding with caution…`
      );
    }

    // ── Retry loop ──────────────────────
    for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
      record.attempts = attempt;

      try {
        const result = await this.withTimeout(task.action(), timeout);
        record.result = result;

        if (!result.success) {
          throw new Error(result.error ?? "Action returned success=false");
        }

        // ── Self-verification step ──────────────
        const verified = await this.verify(task);
        if (!verified) {
          throw new Error(
            "Post-task verification failed — task may not have completed correctly."
          );
        }

        record.status = "completed";
        record.completedAt = new Date();
        const duration = record.completedAt.getTime() - record.startedAt!.getTime();
        Logger.success(`"${task.name}" completed in ${duration}ms.`);
        return;
      } catch (err: any) {
        const msg = err?.message ?? String(err);

        if (attempt <= maxRetries) {
          const delay = (task.retryDelay ?? 1000) * attempt; // exponential back-off
          Logger.warn(
            `"${task.name}" attempt ${attempt} failed: ${msg}. Retrying in ${delay}ms…`
          );
          await this.sleep(delay);
        } else {
          record.status = "failed";
          record.completedAt = new Date();
          record.result = { success: false, error: msg };

          // ── User-friendly message ──────────────
          if (complexity === "complex") {
            Logger.error(
              `"${task.name}" failed after ${attempt} attempt(s).\n` +
              `  This is a COMPLEX task. Please:\n` +
              `  1. Check you have required permissions.\n` +
              `  2. Run this step manually, then re-run the agent.\n` +
              `  Error: ${msg}`
            );
          } else if (complexity === "moderate") {
            Logger.error(
              `"${task.name}" failed after ${attempt} attempt(s).\n` +
              `  Tip: Check that the target app / file is accessible.\n` +
              `  Error: ${msg}`
            );
          } else {
            Logger.error(
              `"${task.name}" failed unexpectedly on a simple task: ${msg}\n` +
              `  This might be a bug — please report it.`
            );
          }
          return;
        }
      }
    }
  }

  /** Run the task's verify() function, or default to true */
  private async verify(task: Task): Promise<boolean> {
    if (!task.verify) return true;
    try {
      const ok = await this.withTimeout(task.verify(), 5000);
      if (!ok) Logger.warn(`Verification step failed for "${task.name}".`);
      return ok;
    } catch (e: any) {
      Logger.warn(`Verification threw an error for "${task.name}": ${e.message}`);
      return false;
    }
  }

  /** Wrap any promise in a timeout */
  private withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
    return new Promise((resolve, reject) => {
      const id = setTimeout(
        () => reject(new Error(`Timed out after ${ms}ms`)),
        ms
      );
      promise.then(
        (v) => { clearTimeout(id); resolve(v); },
        (e) => { clearTimeout(id); reject(e); }
      );
    });
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((r) => setTimeout(r, ms));
  }

  private printSummary(): void {
    console.log("\n" + "═".repeat(60));
    console.log("  TASK SUMMARY");
    console.log("═".repeat(60));

    let completed = 0, failed = 0, skipped = 0;
    for (const [, rec] of this.records) {
      const icon =
        rec.status === "completed" ? "✅" :
        rec.status === "failed"    ? "❌" :
        rec.status === "skipped"   ? "⏭" : "❓";
      const dur =
        rec.startedAt && rec.completedAt
          ? `${rec.completedAt.getTime() - rec.startedAt.getTime()}ms`
          : "—";
      console.log(
        `  ${icon}  ${rec.task.name.padEnd(30)} [${rec.status.padEnd(9)}]  ${dur}`
      );
      if (rec.status === "completed") completed++;
      else if (rec.status === "failed") failed++;
      else if (rec.status === "skipped") skipped++;
    }

    console.log("─".repeat(60));
    console.log(
      `  Total: ${this.queue.length}  ✅ ${completed}  ❌ ${failed}  ⏭ ${skipped}`
    );
    console.log("═".repeat(60) + "\n");
  }
}

// ─────────────────────────────────────
//  BUILT-IN TASK FACTORIES
//  Ready-to-use tasks you can drop into the runner
// ─────────────────────────────────────

export const Tasks = {

  /** Open a desktop application */
  openApp(appName: string, appPath: string): Task {
    return {
      id: `open-${appName.toLowerCase().replace(/\s/g, "-")}`,
      name: `Open ${appName}`,
      description: `open application ${appName}`,
      type: "app",
      timeout: 10000,
      action: async () => {
        try {
          const cmd =
            process.platform === "win32"
              ? `start "" "${appPath}"`
              : process.platform === "darwin"
              ? `open "${appPath}"`
              : `xdg-open "${appPath}"`;
          await execAsync(cmd);
          // Wait a moment so OS can start the process
          await new Promise((r) => setTimeout(r, 2000));
          return { success: true, output: `${appName} launched.` };
        } catch (e: any) {
          return { success: false, error: e.message };
        }
      },
      verify: TaskVerifier.processRunning(appName),
    };
  },

  /** Run a shell command and capture output */
  shell(id: string, name: string, command: string, verifyCmd?: string): Task {
    return {
      id,
      name,
      description: `run shell command: ${command}`,
      type: "shell",
      timeout: 20000,
      action: async () => {
        try {
          const { stdout, stderr } = await execAsync(command);
          return {
            success: true,
            output: stdout || stderr,
          };
        } catch (e: any) {
          return { success: false, error: e.message };
        }
      },
      verify: verifyCmd
        ? async () => {
            try {
              await execAsync(verifyCmd);
              return true;
            } catch {
              return false;
            }
          }
        : undefined,
    };
  },

  /** Create a file with content */
  createFile(filePath: string, content: string): Task {
    return {
      id: `create-file-${path.basename(filePath)}`,
      name: `Create ${path.basename(filePath)}`,
      description: `create file ${filePath}`,
      type: "file",
      action: async () => {
        try {
          fs.mkdirSync(path.dirname(filePath), { recursive: true });
          fs.writeFileSync(filePath, content, "utf8");
          return { success: true, output: `File written to ${filePath}` };
        } catch (e: any) {
          return { success: false, error: e.message };
        }
      },
      verify: TaskVerifier.fileExists(filePath),
    };
  },

  /** Search web (requires a search API / function you plug in) */
  webSearch(
    query: string,
    searchFn: (q: string) => Promise<string>
  ): Task {
    return {
      id: `search-${Date.now()}`,
      name: `Search: "${query}"`,
      description: `search for ${query}`,
      type: "search",
      complexity: "simple",
      timeout: 15000,
      action: async () => {
        try {
          const result = await searchFn(query);
          return { success: true, output: result };
        } catch (e: any) {
          return { success: false, error: e.message };
        }
      },
    };
  },
};

// ─────────────────────────────────────
//  EXAMPLE USAGE
// ─────────────────────────────────────

async function main() {
  const runner = new AgentTaskRunner();

  runner
    .addTask(
      // Task 1 — simple file creation
      Tasks.createFile(
        "./agent-output/hello.txt",
        "Hello from Smart Agent!\n"
      )
    )
    .addTask(
      // Task 2 — depends on task 1
      {
        id: "read-hello",
        name: "Read hello.txt",
        description: "read file",
        type: "file",
        dependsOn: ["create-file-hello.txt"], // won't run until task 1 is done ✅
        action: async () => {
          try {
            const content = fs.readFileSync(
              "./agent-output/hello.txt",
              "utf8"
            );
            console.log("  File contents:", content.trim());
            return { success: true, output: content };
          } catch (e: any) {
            return { success: false, error: e.message };
          }
        },
        verify: TaskVerifier.fileExists("./agent-output/hello.txt"),
      }
    )
    .addTask(
      // Task 3 — moderate shell command
      Tasks.shell(
        "list-files",
        "List agent-output folder",
        "ls ./agent-output",
        "test -d ./agent-output" // verify command
      )
    )
    .addTask(
      // Task 4 — complex system operation
      {
        id: "complex-install",
        name: "Install Docker",
        description: "install Docker using package manager",
        type: "shell",
        complexity: "complex", // will trigger special warnings
        action: async () => {
          try {
            const cmd = process.platform === "win32"
              ? "choco install docker -y"
              : process.platform === "darwin"
              ? "brew install docker"
              : "curl -fsSL https://get.docker.com | sh";
            const { stdout, stderr } = await execAsync(cmd);
            return { success: true, output: stdout || stderr };
          } catch (e: any) {
            return { success: false, error: e.message };
          }
        },
        verify: TaskVerifier.commandExists("docker"),
      }
    );

  await runner.run();
}

main().catch(console.error);
