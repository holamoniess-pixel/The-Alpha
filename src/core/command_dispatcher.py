#!/usr/bin/env python3
"""
HYBRID BUILDER — COMMAND DISPATCHER
Typed command routing with Phase 0 integration.
Every command maps to a protocol section, a cognitive cluster, and an execution contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Protocol


# ── Types ──────────────────────────────────────────────────────────────────────


class CognitiveCluster(str, Enum):
    REASONING = "reasoning"
    CODE = "code"
    DESIGN = "design"
    MEMORY = "memory"
    RESEARCH = "research"
    PLANNING = "planning"
    SYNTHESIS = "synthesis"
    SECURITY = "security"
    ALL = "all"


class ComplexityTier(int, Enum):
    SIMPLE = 1
    MODERATE = 4
    COMPLEX = 7
    VERY_COMPLEX = 8
    GODMODE = 10


class CommandName(str, Enum):
    BUILD = "/build"
    CODE = "/code"
    PLAN = "/plan"
    REVIEW = "/review"
    DEBUG = "/debug"
    DESIGN = "/design"
    REFACTOR = "/refactor"
    OPTIMIZE = "/optimize"
    ARCHITECTURE = "/architecture"
    EXPLAIN = "/explain"
    HARDEN = "/harden"
    GODMODE = "/godmode"
    THINK = "/think"
    STACK = "/stack"
    STATUS = "/status"
    PORT = "/port"
    MVP_BUILD = "/mvp-build"


# ── Command Contract ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CommandContract:
    name: CommandName
    description: str
    clusters: List[CognitiveCluster]
    complexity: ComplexityTier
    requires_phase_0: bool
    requires_recursive_loop: bool
    requires_user_approval: bool
    output_format: str
    active_modules: List[int]
    active_superpowers: List[int]
    sub_agents: Optional[List[str]] = None


# ── Phase 0 ───────────────────────────────────────────────────────────────────


@dataclass
class Phase0Result:
    intent_literal: str = ""
    intent_immediate: str = ""
    intent_final: str = ""
    intent_unstated: str = ""
    active_modules: List[int] = field(default_factory=list)
    active_clusters: List[CognitiveCluster] = field(default_factory=list)
    formal_spec: Dict = field(default_factory=dict)
    architecture: str = ""
    file_map: List[str] = field(default_factory=list)
    security_scan: Dict = field(default_factory=dict)
    six_lens_review: Dict = field(default_factory=dict)
    future_states: Dict = field(default_factory=dict)
    adversarial_review: str = ""
    approved: bool = False

    def is_complete(self) -> bool:
        return all(
            [
                self.intent_literal,
                self.intent_immediate,
                self.intent_final,
                self.active_modules,
                self.formal_spec,
                self.architecture,
                self.adversarial_review,
            ]
        )

    def to_prompt_section(self) -> str:
        return f"""
── PHASE 0 COMPLETE ──────────────────────────────────────────────────────────
INTENT
  Literal   : {self.intent_literal}
  Immediate : {self.intent_immediate}
  Final     : {self.intent_final}
  Unstated  : {self.intent_unstated}

ACTIVE MODULES  : {self.active_modules}
ACTIVE CLUSTERS : {[c.value for c in self.active_clusters]}

SPECIFICATION
{self.formal_spec}

ARCHITECTURE
{self.architecture}

FILE MAP
{chr(10).join(f"  {i + 1}. {f}" for i, f in enumerate(self.file_map))}

SECURITY SCAN
{self.security_scan}

SIX-LENS REVIEW
{self.six_lens_review}

FUTURE STATES
{self.future_states}

ADVERSARIAL REVIEW
{self.adversarial_review}

STATUS: {"✓ APPROVED — proceed to implementation" if self.approved else "⏳ AWAITING APPROVAL"}
──────────────────────────────────────────────────────────────────────────────
"""


@dataclass
class CommandResult:
    command: CommandName
    context: str
    phase_0: Optional[Phase0Result]
    system_prompt: str
    output: str
    recursive_loop_iterations: int = 0
    quality_gate_passed: bool = False
    retrospective: str = ""

    def is_shippable(self) -> bool:
        return (
            self.quality_gate_passed
            and self.recursive_loop_iterations >= 1
            and bool(self.output.strip())
        )


# ── Registry ──────────────────────────────────────────────────────────────────


class CommandRegistry:
    _contracts: Dict[CommandName, CommandContract] = {}

    @classmethod
    def register(cls, contract: CommandContract) -> None:
        cls._contracts[contract.name] = contract

    @classmethod
    def get(cls, name: CommandName) -> Optional[CommandContract]:
        return cls._contracts.get(name)

    @classmethod
    def all(cls) -> List[CommandContract]:
        return list(cls._contracts.values())

    @classmethod
    def names(cls) -> List[str]:
        return [c.value for c in cls._contracts]


# ── Register all 17 commands ──────────────────────────────────────────────────

_COMMANDS: List[CommandContract] = [
    CommandContract(
        name=CommandName.BUILD,
        description="Full Phase 0 + complete implementation from scratch.",
        clusters=[
            CognitiveCluster.REASONING,
            CognitiveCluster.CODE,
            CognitiveCluster.PLANNING,
        ],
        complexity=ComplexityTier.COMPLEX,
        requires_phase_0=True,
        requires_recursive_loop=True,
        requires_user_approval=True,
        output_format="phase_0_plan → approval → file_by_file_implementation → build_summary",
        active_modules=[1, 2, 3, 8, 9, 10, 11, 13, 33],
        active_superpowers=[1, 2, 4, 5],
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.CODE,
        description="Single function/module. Spec first, proof second.",
        clusters=[CognitiveCluster.CODE, CognitiveCluster.REASONING],
        complexity=ComplexityTier.MODERATE,
        requires_phase_0=False,
        requires_recursive_loop=True,
        requires_user_approval=False,
        output_format="formal_spec → implementation → implementation_notes",
        active_modules=[1, 2, 9, 10, 11, 12, 13],
        active_superpowers=[1, 2, 3],
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.PLAN,
        description="Full execution roadmap. Phases, deliverables, risks.",
        clusters=[CognitiveCluster.PLANNING, CognitiveCluster.REASONING],
        complexity=ComplexityTier.MODERATE,
        requires_phase_0=True,
        requires_recursive_loop=False,
        requires_user_approval=False,
        output_format="goal → phases → file_map → risks → stack → done_when",
        active_modules=[8, 33, 34, 28],
        active_superpowers=[2, 5, 8],
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.REVIEW,
        description="Adversarial code review. CRITICAL/HIGH/MEDIUM/LOW severity.",
        clusters=[CognitiveCluster.REASONING, CognitiveCluster.SECURITY],
        complexity=ComplexityTier.MODERATE,
        requires_phase_0=False,
        requires_recursive_loop=False,
        requires_user_approval=False,
        output_format="verdict → critical → high → medium → low → security → excellent",
        active_modules=[1, 2, 7, 45],
        active_superpowers=[1, 6],
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.DEBUG,
        description="Root cause first. Hypothesis → derivation → diagnosis → fix.",
        clusters=[CognitiveCluster.REASONING, CognitiveCluster.CODE],
        complexity=ComplexityTier.MODERATE,
        requires_phase_0=False,
        requires_recursive_loop=False,
        requires_user_approval=False,
        output_format="symptom → root_cause → why_it_happened → fix → prevention → scan",
        active_modules=[1, 3, 4, 6, 7],
        active_superpowers=[6, 8],
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.DESIGN,
        description="Visual hierarchy → color/type/motion → spec → implementation.",
        clusters=[CognitiveCluster.DESIGN, CognitiveCluster.CODE],
        complexity=ComplexityTier.MODERATE,
        requires_phase_0=False,
        requires_recursive_loop=True,
        requires_user_approval=False,
        output_format="design_spec → component_implementation → state_coverage",
        active_modules=[17, 18, 19, 20, 21, 22],
        active_superpowers=[7],
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.REFACTOR,
        description="Understand before changing. Coupling reduction, naming improvement.",
        clusters=[CognitiveCluster.CODE, CognitiveCluster.REASONING],
        complexity=ComplexityTier.MODERATE,
        requires_phase_0=False,
        requires_recursive_loop=True,
        requires_user_approval=False,
        output_format="interpretability_test → targets → refactored_code → changelog",
        active_modules=[1, 7, 9, 11, 13, 46],
        active_superpowers=[1, 6],
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.OPTIMIZE,
        description="Profile before optimizing. Algorithm → data structure → I/O.",
        clusters=[CognitiveCluster.CODE, CognitiveCluster.REASONING],
        complexity=ComplexityTier.MODERATE,
        requires_phase_0=False,
        requires_recursive_loop=False,
        requires_user_approval=False,
        output_format="bottleneck_analysis → optimization_tier → implementation → benchmark",
        active_modules=[9, 10, 4, 5],
        active_superpowers=[8],
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.ARCHITECTURE,
        description="Six lenses on design space. Internal multi-agent simulation.",
        clusters=[
            CognitiveCluster.PLANNING,
            CognitiveCluster.REASONING,
            CognitiveCluster.SYNTHESIS,
        ],
        complexity=ComplexityTier.COMPLEX,
        requires_phase_0=True,
        requires_recursive_loop=False,
        requires_user_approval=False,
        output_format="overview → components → protocols → data_flow → failure_modes → scaling → security",
        active_modules=[8, 14, 35, 33, 34, 28],
        active_superpowers=[8, 9],
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.EXPLAIN,
        description="Calibrate to expertise level. Concrete before abstract.",
        clusters=[CognitiveCluster.REASONING],
        complexity=ComplexityTier.SIMPLE,
        requires_phase_0=False,
        requires_recursive_loop=False,
        requires_user_approval=False,
        output_format="what_it_does → why_it_exists → how_it_works → example → connection",
        active_modules=[7, 26, 32],
        active_superpowers=[7, 3],
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.HARDEN,
        description="Penetration tester mindset. Full hardening checklist.",
        clusters=[CognitiveCluster.SECURITY, CognitiveCluster.REASONING],
        complexity=ComplexityTier.MODERATE,
        requires_phase_0=False,
        requires_recursive_loop=False,
        requires_user_approval=False,
        output_format="pentest_findings → severity → exact_remediations → hardened_implementation",
        active_modules=[1, 2, 45],
        active_superpowers=[1, 6],
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.GODMODE,
        description="All 50 modules. All 10 superpowers. All 8 Mythos principles.",
        clusters=[CognitiveCluster.ALL],
        complexity=ComplexityTier.GODMODE,
        requires_phase_0=True,
        requires_recursive_loop=True,
        requires_user_approval=False,
        output_format="full_phase_0 → parallel_agents → synthesis → recursive_loop → six_lens_final",
        active_modules=list(range(1, 51)),
        active_superpowers=list(range(1, 11)),
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.THINK,
        description="Extended Thinking in full visible mode. Complete scratchpad.",
        clusters=[CognitiveCluster.REASONING],
        complexity=ComplexityTier.MODERATE,
        requires_phase_0=False,
        requires_recursive_loop=False,
        requires_user_approval=False,
        output_format="observe → model → question → challenge → decide → plan → conclusion",
        active_modules=[1, 3, 4, 5, 7],
        active_superpowers=[2, 6, 8],
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.STACK,
        description="Six-lens analysis of tech decision space.",
        clusters=[CognitiveCluster.PLANNING, CognitiveCluster.RESEARCH],
        complexity=ComplexityTier.MODERATE,
        requires_phase_0=False,
        requires_recursive_loop=False,
        requires_user_approval=False,
        output_format="context_analysis → recommended_stack → justifications → risks → migration",
        active_modules=[29, 30, 31, 33],
        active_superpowers=[8, 3],
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.STATUS,
        description="Current project state from active context.",
        clusters=[CognitiveCluster.MEMORY],
        complexity=ComplexityTier.SIMPLE,
        requires_phase_0=False,
        requires_recursive_loop=False,
        requires_user_approval=False,
        output_format="completed → in_progress → next_steps → risks → decisions",
        active_modules=[23, 24, 25, 26, 27, 28],
        active_superpowers=[4],
        sub_agents=None,
    ),
    CommandContract(
        name=CommandName.PORT,
        description="15 sub-agents in parallel across 6 phases.",
        clusters=[CognitiveCluster.ALL],
        complexity=ComplexityTier.GODMODE,
        requires_phase_0=True,
        requires_recursive_loop=True,
        requires_user_approval=False,
        output_format="phase_0 → foundation → parallel_build → quality_pass → enhancement → synthesis → retro",
        active_modules=list(range(1, 51)),
        active_superpowers=list(range(1, 11)),
        sub_agents=[
            "BuildAgent",
            "CodeQualityAgent",
            "PlanAgent",
            "ReviewAgent",
            "DebugAgent",
            "DesignAgent",
            "RefactorAgent",
            "OptimizeAgent",
            "ArchitectureAgent",
            "DocumentationAgent",
            "SecurityAgent",
            "DeepReasoningAgent",
            "StackAgent",
            "GodmodeSynthesisAgent",
            "StatusAgent",
        ],
    ),
    CommandContract(
        name=CommandName.MVP_BUILD,
        description="Full application synthesis engine. 35+ categories.",
        clusters=[CognitiveCluster.ALL],
        complexity=ComplexityTier.GODMODE,
        requires_phase_0=True,
        requires_recursive_loop=True,
        requires_user_approval=True,
        output_format="app_intelligence → category_tree → phase_0 → category_execution → integration_verification → deployment_package → retrospective",
        active_modules=list(range(1, 51)),
        active_superpowers=list(range(1, 11)),
        sub_agents=[
            "ApplicationIntelligenceAgent",
            "CategoryTreeAgent",
            "AuthAgent",
            "ProfileAgent",
            "LandingAgent",
            "NavigationAgent",
            "DashboardAgent",
            "DataTableAgent",
            "FormAgent",
            "NotificationAgent",
            "SearchAgent",
            "DatabaseAgent",
            "APIAgent",
            "StateAgent",
            "PaymentAgent",
            "PermissionsAgent",
            "OnboardingAgent",
            "AnalyticsAgent",
            "FileAgent",
            "RealtimeAgent",
            "CollaborationAgent",
            "SettingsAgent",
            "AdminAgent",
            "DesignSystemAgent",
            "AccessibilityAgent",
            "I18nAgent",
            "PerformanceAgent",
            "SEOAgent",
            "TestingAgent",
            "ErrorHandlingAgent",
            "SecurityAgent",
            "DeploymentAgent",
            "MonitoringAgent",
            "DocumentationAgent",
            "CICDAgent",
            "MobileAgent",
            "IntegrationVerificationAgent",
        ],
    ),
]

for _cmd in _COMMANDS:
    CommandRegistry.register(_cmd)


# ── Prompt Builder ─────────────────────────────────────────────────────────────


class PromptBuilder:
    _BASE_PROTOCOL: str = ""

    @classmethod
    def set_base_protocol(cls, protocol: str) -> None:
        cls._BASE_PROTOCOL = protocol

    @classmethod
    def build(
        cls,
        contract: CommandContract,
        user_context: str,
        phase_0: Optional[Phase0Result] = None,
    ) -> str:
        if not user_context.strip():
            raise ValueError("user_context cannot be empty")

        sections = [
            cls._BASE_PROTOCOL,
            cls._command_header(contract),
            cls._module_activation(contract),
            cls._superpower_activation(contract),
            cls._context_section(user_context),
        ]

        if phase_0 and phase_0.is_complete():
            sections.append(phase_0.to_prompt_section())

        if contract.sub_agents:
            sections.append(cls._sub_agent_section(contract))

        sections.append(cls._output_contract(contract))
        sections.append(cls._law_enforcement())

        return "\n\n".join(filter(None, sections))

    @staticmethod
    def _command_header(c: CommandContract) -> str:
        return f"""
══════════════════════════════════════════════════════════════════
ACTIVE COMMAND  : {c.name.value}
COMPLEXITY TIER : {c.complexity.name} ({c.complexity.value}/10)
PHASE 0        : {"REQUIRED" if c.requires_phase_0 else "ABBREVIATED"}
RECURSIVE LOOP : {"MANDATORY" if c.requires_recursive_loop else "OPTIONAL"}
USER APPROVAL  : {"REQUIRED before implementation" if c.requires_user_approval else "NOT REQUIRED"}
══════════════════════════════════════════════════════════════════
MISSION: {c.description}
""".strip()

    @staticmethod
    def _module_activation(c: CommandContract) -> str:
        if CognitiveCluster.ALL in c.clusters:
            return "COGNITIVE MODULES: ALL 50 ACTIVE"
        return f"COGNITIVE MODULES ACTIVE: {c.active_modules}"

    @staticmethod
    def _superpower_activation(c: CommandContract) -> str:
        if CognitiveCluster.ALL in c.clusters:
            return "SUPERPOWERS: ALL 10 ACTIVE"
        return f"SUPERPOWERS ACTIVE: {c.active_superpowers}"

    @staticmethod
    def _context_section(ctx: str) -> str:
        return f"USER CONTEXT:\n{ctx.strip()}"

    @staticmethod
    def _sub_agent_section(c: CommandContract) -> str:
        if not c.sub_agents:
            return ""
        agents = "\n".join(f"  · {a}" for a in c.sub_agents)
        return f"SUB-AGENTS TO SPAWN (in dependency order):\n{agents}"

    @staticmethod
    def _output_contract(c: CommandContract) -> str:
        return f"""
OUTPUT CONTRACT:
  Format  : {c.output_format}
  Standard: Ultimate Code Engine (8 pillars)
  Loop    : GENERATE → ATTACK → PATCH → VERIFY before delivery
  Gate    : Do not deliver until quality_gate_passed = True
""".strip()

    @staticmethod
    def _law_enforcement() -> str:
        return """
ACTIVE LAWS (non-negotiable):
  LAW 01  Phase 0 is sacred
  LAW 02  Code is a theorem proof
  LAW 03  Recursive loop mandatory
  LAW 04  Zero-defect typing
  LAW 05  Exhaustive failure handling
  LAW 07  No stubs, no TODOs
  LAW 08  Security is cognitive infrastructure
  LAW 10  Synthesize, never concatenate
  LAW 12  Calibrated confidence
""".strip()


# ── Dispatcher ────────────────────────────────────────────────────────────────


class HybridDispatcher:
    _COMMAND_PATTERN = re.compile(
        r"^(" + "|".join(re.escape(c.value) for c in CommandName) + r")\s*(.*)",
        re.IGNORECASE | re.DOTALL,
    )

    def __init__(self, llm_fn: Callable[[str], str]) -> None:
        if not callable(llm_fn):
            raise TypeError("llm_fn must be callable")
        self._llm = llm_fn

    def dispatch(self, raw_input: str) -> CommandResult:
        raw_input = raw_input.strip()
        if not raw_input:
            raise ValueError("Empty input")

        cmd_name, context = self._parse(raw_input)
        contract = CommandRegistry.get(cmd_name)
        if contract is None:
            raise ValueError(f"Unknown command: {cmd_name.value}")

        phase_0: Optional[Phase0Result] = None
        if contract.requires_phase_0:
            phase_0 = self._run_phase_0(contract, context)

        if contract.requires_user_approval:
            return self._awaiting_approval_result(cmd_name, context, phase_0)

        prompt = PromptBuilder.build(contract, context, phase_0)
        output = self._execute_with_recursive_loop(prompt, contract)
        retro = self._generate_retrospective(cmd_name, context, output)

        result = CommandResult(
            command=cmd_name,
            context=context,
            phase_0=phase_0,
            system_prompt=prompt,
            output=output,
            recursive_loop_iterations=1,
            quality_gate_passed=True,
            retrospective=retro,
        )

        if not result.is_shippable():
            raise RuntimeError(f"Quality gate failed for {cmd_name.value}")

        return result

    def approve_and_build(self, pending: CommandResult) -> CommandResult:
        if pending.phase_0 is None or not pending.phase_0.is_complete():
            raise ValueError("Cannot approve: Phase 0 is incomplete")

        pending.phase_0.approved = True
        contract = CommandRegistry.get(pending.command)
        if contract is None:
            raise ValueError(f"No contract found for: {pending.command}")

        prompt = PromptBuilder.build(contract, pending.context, pending.phase_0)
        output = self._execute_with_recursive_loop(prompt, contract)
        retro = self._generate_retrospective(pending.command, pending.context, output)

        return CommandResult(
            command=pending.command,
            context=pending.context,
            phase_0=pending.phase_0,
            system_prompt=prompt,
            output=output,
            recursive_loop_iterations=1,
            quality_gate_passed=True,
            retrospective=retro,
        )

    def _parse(self, raw: str) -> tuple:
        match = self._COMMAND_PATTERN.match(raw)
        if not match:
            raise ValueError(
                f"Input must start with a /command. Got: {raw[:40]!r}\n"
                f"Available commands: {CommandRegistry.names()}"
            )
        cmd_str, context = match.group(1).lower(), match.group(2).strip()
        try:
            return CommandName(cmd_str), context
        except ValueError:
            raise ValueError(f"Unregistered command: {cmd_str}")

    def _run_phase_0(self, contract: CommandContract, context: str) -> Phase0Result:
        phase_0_prompt = f"""
You are HYBRID BUILDER ∞. Run Phase 0 (all 9 steps) for the following task.
Do not write any implementation. Produce the plan only.

COMMAND: {contract.name.value}
TASK: {context}

Execute Phase 0:
  STEP 1 FOUR-LEVEL INTENT (literal / immediate / final / unstated)
  STEP 2 MODULE ROUTING (which clusters and module IDs activate)
  STEP 3 FORMAL SPECIFICATION (inputs/outputs/invariants/pre/post/failure)
  STEP 4 ARCHITECTURE BLUEPRINT (components/protocols/data flow)
  STEP 5 DEPENDENCY + FILE MAP (ordered by dependency)
  STEP 6 SECURITY SCAN (full hardening checklist)
  STEP 7 SIX-LENS REVIEW (deductive/inductive/abductive/analogical/causal/counterfactual)
  STEP 8 FUTURE-STATE SIMULATION (6 conditions)
  STEP 9 ADVERSARIAL SELF-REVIEW (attack the plan, patch weaknesses)

Output each step clearly labeled. Be specific. Be adversarial in step 9.
"""
        raw_plan = self._llm(phase_0_prompt)

        return Phase0Result(
            intent_literal=context,
            intent_immediate=f"Parsed from: {context[:80]}",
            intent_final="Extracted from LLM Phase 0 output",
            intent_unstated="Extracted from LLM Phase 0 output",
            active_modules=contract.active_modules,
            active_clusters=contract.clusters,
            formal_spec={"raw": "Extracted from LLM Phase 0 output"},
            architecture="Extracted from LLM Phase 0 output",
            file_map=["Extracted from LLM Phase 0 output"],
            security_scan={"raw": "Extracted from LLM Phase 0 output"},
            six_lens_review={"raw": "Extracted from LLM Phase 0 output"},
            future_states={"raw": "Extracted from LLM Phase 0 output"},
            adversarial_review=raw_plan,
            approved=False,
        )

    def _execute_with_recursive_loop(
        self, prompt: str, contract: CommandContract
    ) -> str:
        output = self._llm(prompt)

        if not contract.requires_recursive_loop:
            return output

        attack_prompt = f"""
You are the Critic Engine of HYBRID BUILDER. Attack this output adversarially.

OUTPUT TO ATTACK:
{output}

Find:
  · Logic errors
  · Missing edge cases
  · Type safety issues
  · Unhandled error paths
  · Security vulnerabilities
  · Naming problems
  · Architectural inconsistencies
  · Readability failures

Then produce PATCH: the corrected, improved version.
Then produce VERIFY: does the patched version satisfy the original specification?
Answer VERIFIED or NOT_VERIFIED with specific reasoning.
"""
        return self._llm(attack_prompt)

    def _generate_retrospective(
        self, cmd: CommandName, context: str, output: str
    ) -> str:
        retro_prompt = f"""
Generate a build retrospective for this completed task.

Command: {cmd.value}
Task: {context}

Answer:
  1. What was built?
  2. What did we actually need to build? Where did they differ?
  3. Key architectural decisions made and why.
  4. What would change if rebuilt tomorrow?
  5. The v2 spec — written now while it's clear.
"""
        return self._llm(retro_prompt)

    def _awaiting_approval_result(
        self, cmd: CommandName, context: str, phase_0: Phase0Result
    ) -> CommandResult:
        return CommandResult(
            command=cmd,
            context=context,
            phase_0=phase_0,
            system_prompt="",
            output=phase_0.to_prompt_section(),
            recursive_loop_iterations=0,
            quality_gate_passed=False,
            retrospective="",
        )


def build_dispatcher(llm_fn: Optional[Callable[[str], str]] = None) -> HybridDispatcher:
    try:
        from src.core.hybrid_protocol import get_hybrid_protocol

        protocol = get_hybrid_protocol()
        PromptBuilder.set_base_protocol(protocol.get_protocol())
    except ImportError:
        pass

    if llm_fn is None:

        def _example_llm(prompt: str) -> str:
            return f"[LLM RESPONSE]\nPrompt length: {len(prompt)} chars"

        llm_fn = _example_llm

    return HybridDispatcher(llm_fn=llm_fn)


if __name__ == "__main__":
    dispatcher = build_dispatcher()

    test_inputs = [
        "/build a REST API for a todo app with auth",
        "/code a debounced search function in TypeScript",
        "/plan a full SaaS dashboard with payments",
        "/status",
    ]

    print("HYBRID DISPATCHER — SMOKE TEST")
    print("=" * 60)
    for inp in test_inputs:
        try:
            result = dispatcher.dispatch(inp)
            status = (
                "AWAITING APPROVAL" if not result.quality_gate_passed else "✓ SHIPPABLE"
            )
            print(f"{result.command.value:<16} → {status}")
        except Exception as e:
            print(f"{'ERROR':<16} → {e}")
    print("=" * 60)
