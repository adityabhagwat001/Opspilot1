"""
OpsPilot Complete Project Workflow, Architecture, and Presentation Guide Generator
Generates:
1. OpsPilot_Complete_Project_Workflow.docx
2. OpsPilot_Complete_Project_Workflow.pdf
"""

import os
import sys
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=140, bottom=140, left=180, right=180):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def generate_docx(output_path):
    doc = docx.Document()

    # Margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.85)
        section.right_margin = Inches(0.85)

    # Color Palette
    PRIMARY_EMERALD = RGBColor(16, 185, 129)   # #10B981 (Brand Green)
    DARK_NAVY = RGBColor(15, 23, 42)           # #0F172A (Primary Heading)
    ACCENT_BLUE = RGBColor(37, 99, 235)        # #2563EB (Subheadings)
    TEXT_BODY = RGBColor(51, 65, 85)           # #334155 (Body text)
    MUTED_GRAY = RGBColor(100, 116, 139)       # #64748B (Secondary info)
    
    CALLOUT_BG = "F8FAFC"                      # Slate light
    BORDER_EMERALD = "10B981"
    BORDER_BLUE = "2563EB"
    HEADER_BG = "0F172A"

    def add_header(title, subtitle):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(4)
        r1 = p.add_run(title + "\n")
        r1.font.name = "Segoe UI"
        r1.font.size = Pt(26)
        r1.font.bold = True
        r1.font.color.rgb = DARK_NAVY

        r2 = p.add_run(subtitle)
        r2.font.name = "Segoe UI"
        r2.font.size = Pt(13)
        r2.font.color.rgb = PRIMARY_EMERALD
        r2.font.bold = True

        p_meta = doc.add_paragraph()
        p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_meta.paragraph_format.space_after = Pt(24)
        rm = p_meta.add_run("Enterprise AI DevOps & Cloud Operations Copilot | Human-in-the-Loop Architecture")
        rm.font.name = "Segoe UI"
        rm.font.size = Pt(9.5)
        rm.font.color.rgb = MUTED_GRAY

    def add_heading_1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = "Segoe UI"
        run.font.size = Pt(16)
        run.font.bold = True
        run.font.color.rgb = DARK_NAVY

    def add_heading_2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = "Segoe UI"
        run.font.size = Pt(12.5)
        run.font.bold = True
        run.font.color.rgb = ACCENT_BLUE

    def add_body(text, bold_prefix=None, italic=False):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            rb = p.add_run(bold_prefix)
            rb.font.name = "Segoe UI"
            rb.font.size = Pt(10)
            rb.font.bold = True
            rb.font.color.rgb = DARK_NAVY
        r = p.add_run(text)
        r.font.name = "Segoe UI"
        r.font.size = Pt(10)
        r.font.color.rgb = TEXT_BODY
        r.font.italic = italic
        return p

    def add_bullet(text, bold_prefix=None):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            rb = p.add_run(bold_prefix)
            rb.font.name = "Segoe UI"
            rb.font.size = Pt(10)
            rb.font.bold = True
            rb.font.color.rgb = DARK_NAVY
        r = p.add_run(text)
        r.font.name = "Segoe UI"
        r.font.size = Pt(10)
        r.font.color.rgb = TEXT_BODY

    def add_callout(text, title=None, border_color=BORDER_EMERALD, bg_color=CALLOUT_BG):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        cell = tbl.cell(0, 0)
        cell.width = Inches(6.8)
        set_cell_background(cell, bg_color)
        set_cell_margins(cell, top=140, bottom=140, left=200, right=200)

        tcPr = cell._element.get_or_add_tcPr()
        borders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:left w:val="single" w:sz="36" w:space="0" w:color="{border_color}"/>'
            f'<w:top w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'<w:bottom w:val="none"/>'
            f'</w:tcBorders>'
        )
        tcPr.append(borders)

        cp = cell.paragraphs[0]
        cp.paragraph_format.space_after = Pt(2)
        if title:
            rt = cp.add_run(f"📌 {title}\n")
            rt.font.name = "Segoe UI"
            rt.font.size = Pt(10.5)
            rt.font.bold = True
            rt.font.color.rgb = DARK_NAVY

        rc = cp.add_run(text)
        rc.font.name = "Segoe UI"
        rc.font.size = Pt(9.5)
        rc.font.color.rgb = TEXT_BODY
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # ------------------ DOCUMENT CONTENT ------------------

    add_header("OPSPILOT SYSTEM OVERVIEW & WORKFLOW GUIDE", "Complete Architectural Blueprint, User Flows, Role RBAC & Presentation Script")

    # 1. Executive Summary
    add_heading_1("1. Executive Summary & The 30-Second Pitch")
    add_callout(
        "\"OpsPilot is an Enterprise AI Operations Copilot that connects directly to production infrastructure—"
        "including GitHub repositories, PostgreSQL databases, and operational productivity channels—using the open Model "
        "Context Protocol (FastMCP). It automatically investigates CI/CD failures, analyzes logs, and generates code patches. "
        "Crucially, it solves the enterprise safety problem with a Cryptographic Human-in-the-Loop (HITL) boundary: no destructive "
        "write operation (like merging PRs or modifying databases) can ever execute without explicit, signed human approval.\"",
        "The 30-Second Elevator Pitch"
    )

    # 2. Problem Statement
    add_heading_1("2. The Problem Statement: Why OpsPilot Was Built")
    add_body(
        "Modern cloud development and DevOps teams operate under severe operational friction caused by three fundamental challenges:"
    )
    add_bullet(
        "Engineers must constantly switch between GitHub Actions logs, database consoles (pgAdmin/psql), email alerts, "
        "and incident tracking systems just to diagnose a single outage or failed build.",
        "1. Extreme Tool Sprawl & Context Switching: "
    )
    add_bullet(
        "Developers spend hours manually downloading CI/CD raw terminal logs, sifting through thousands of lines of stack traces, "
        "identifying missing dependencies or failing tests, and crafting manual hotfixes under pressure.",
        "2. Slow Mean-Time-to-Resolution (MTTR) & Alert Fatigue: "
    )
    add_bullet(
        "While modern Large Language Models (LLMs) can generate code, giving an autonomous AI agent direct write access to "
        "production Git repos or databases is extremely risky. Traditional AI assistants either have zero execution ability "
        "(they just chat) or unchecked execution ability (they can drop tables or break main branches without oversight).",
        "3. The 'Unsafe Autonomous AI' Paradox: "
    )

    # 3. The OpsPilot Solution
    add_heading_1("3. The OpsPilot Solution")
    add_body(
        "OpsPilot bridges autonomous AI capability with strict enterprise safety through four pillars:"
    )
    add_bullet(
        "Integrates GitHub, PostgreSQL, and Communication channels under a standardized, modular RPC standard (FastMCP). "
        "Tools can be added or swapped without touching core agent logic.",
        "Modular Microservice Orchestration (FastMCP): "
    )
    add_bullet(
        "The AI agent automatically parses CI/CD failure logs, detects the root cause (syntax errors, missing packages, DB migration errors), "
        "and crafts a concrete diff/patch ready to apply.",
        "Intelligent Automated Triage & Root Cause Analysis: "
    )
    add_bullet(
        "Zero unvetted write actions. Read operations (inspecting logs, listing tables) run seamlessly, while all write operations "
        "(creating PRs, executing SQL migrations, sending triage emails) enter a cryptographic approval queue with HMAC-SHA256 signatures.",
        "Human-in-the-Loop (HITL) Governance: "
    )
    add_bullet(
        "Every single AI tool call, human approval, rejection, and patch generation is written to an immutable audit ledger "
        "for security, compliance, and post-incident reviews.",
        "Enterprise Auditability & RBAC: "
    )

    # 4. Two User Roles
    add_heading_1("4. The Two Login Roles: Admin vs. Operator Explained")
    add_body(
        "OpsPilot implements strict Role-Based Access Control (RBAC) to enforce separation of duties between operational investigation "
        "and administrative governance:"
    )

    # Table of Roles
    tbl_roles = doc.add_table(rows=6, cols=3)
    tbl_roles.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_roles.autofit = False

    headers = ["Feature / Dimension", "Lead DevOps Operator (operator123)", "Enterprise Administrator (admin123)"]
    for i, col_name in enumerate(headers):
        cell = tbl_roles.cell(0, i)
        set_cell_background(cell, HEADER_BG)
        set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
        p = cell.paragraphs[0]
        r = p.add_run(col_name)
        r.font.name = "Segoe UI"
        r.font.size = Pt(9.5)
        r.font.bold = True
        r.font.color.rgb = RGBColor(255, 255, 255)

    role_data = [
        ("Login Credentials", "operator@opspilot.internal / operator123\nUser ID: usr-operator-01", "admin@opspilot.internal / admin123\nUser ID: usr-admin-01"),
        ("Primary Responsibility", "Day-to-day triage, troubleshooting pipelines, debugging DB issues, chatting with AI copilot.", "Platform governance, security oversight, approving high-risk changes, compliance auditing."),
        ("AI Copilot Capabilities", "Full natural language conversation. Can ask AI to analyze logs, inspect schemas, and PROPOSE fixes.", "Full conversational access plus administrative overrides and system health diagnostics."),
        ("Approval Center Rights", "CANNOT approve high-risk actions. Can view status and trigger requests that wait for review.", "CAN APPROVE or REJECT pending write operations with cryptographic HMAC signature."),
        ("System Management", "Read-only access to integrations and workspace members.", "Full authority to configure integrations (GitHub/Postgres/SMTP), manage API tokens, and purge logs.")
    ]

    for row_idx, data in enumerate(role_data, start=1):
        bg = "F8FAFC" if row_idx % 2 == 0 else "FFFFFF"
        for col_idx, text in enumerate(data):
            cell = tbl_roles.cell(row_idx, col_idx)
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
            p = cell.paragraphs[0]
            r = p.add_run(text)
            r.font.name = "Segoe UI"
            r.font.size = Pt(9)
            if col_idx == 0:
                r.font.bold = True
                r.font.color.rgb = DARK_NAVY
            else:
                r.font.color.rgb = TEXT_BODY

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 5. End-to-End Workflow & Step-by-Step Incident Lifecycle
    add_heading_1("5. End-to-End Workflow: The 5-Step Incident Lifecycle")
    add_body(
        "Here is the exact lifecycle of how a production CI/CD failure is detected, diagnosed, and resolved inside OpsPilot:"
    )

    steps = [
        ("Step 1: Ingestion & Telemetry Aggregation",
         "A GitHub Actions build fails (e.g. failing pytest or broken dependency in a repo). GitHub webhooks or periodic pollers notify OpsPilot. "
         "OpsPilot syncs the run details, commit metadata, and failure logs into the local operational datastore."),

        ("Step 2: AI Diagnostic Triage (Operator Interaction)",
         "The DevOps Operator sees the failure on the Pipelines dashboard or asks the AI Copilot: 'What failed in our latest build?'. "
         "The AI invokes read-only FastMCP tools (`get_workflow_logs`, `analyze_error_trace`) to parse the log stack trace and isolate the bug."),

        ("Step 3: Automated Patch Proposal & Security Interception",
         "The Operator clicks 'Generate AI Fix' or instructs the AI: 'Propose a pull request to fix the dependency error'. "
         "The LangGraph agent identifies that `create_pull_request` is a HIGH-RISK WRITE tool. "
         "Instead of executing immediately, the system generates a cryptographic Nonce and locks the action in the Approval Center with status PENDING."),

        ("Step 4: Cryptographic Human Review (Admin Action)",
         "The Enterprise Admin logs in and opens the Approval Center. The Admin inspects the exact tool payload: target repo, branch, commit message, "
         "and file diff. If the patch is verified, the Admin clicks 'Approve Request'. OpsPilot generates an HMAC-SHA256 signature containing "
         "the timestamp, canonical request hash, and admin ID."),

        ("Step 5: Autonomous Execution & Immutable Audit Log",
         "With the cryptographic token verified, the GitHub FastMCP Server executes the pull request creation against the real GitHub repository. "
         "The audit log records the entire trace: who requested it, who approved it, the signature hash, and the resulting GitHub PR URL.")
    ]

    for title, desc in steps:
        add_bullet(desc, f"{title}: ")

    # 6. How Users Interact With Each Screen (UI Tour)
    add_heading_1("6. How Users Interact With the Platform (UI Walkthrough)")
    add_body(
        "The OpsPilot web interface is designed with a sleek, high-contrast dark theme, intuitive status badges, and responsive glassmorphic cards:"
    )

    add_bullet(
        "Displays real-time system metrics: Total Active Incidents, Pending Approvals, Connected MCP Servers, and Mean Time to Resolution (MTTR). "
        "Gives an instant pulse of infrastructure health.",
        "1. Operations Dashboard: "
    )
    add_bullet(
        "An interactive ChatGPT-style conversational console with streaming responses. Users can ask questions in plain English "
        "('Show me all slow queries on PostgreSQL', 'Why did commit 4f2a fail?'). The AI shows tool call chips as it fetches data.",
        "2. AI Ops Assistant (Chat): "
    )
    add_bullet(
        "Lists all recent CI/CD pipeline runs across connected repositories. Failed workflows are highlighted in red with badges. "
        "Clicking an incident displays the exact terminal error output and a 1-click 'Generate AI Fix' button.",
        "3. CI/CD Pipelines & Failure Triage: "
    )
    add_bullet(
        "The core safety cockpit. Shows all pending high-risk tool calls awaiting review. Each item displays the requesting user, timestamp, "
        "target system, and formatted JSON diff. Admins have 'Approve' and 'Reject' buttons with instant feedback.",
        "4. Approval Center (HITL Gating): "
    )
    add_bullet(
        "Manage connections to external systems: GitHub profile credentials/PAT, PostgreSQL database host & connection strings, "
        "and SMTP email relays. Features real-time connection test buttons.",
        "5. Integrations Center: "
    )
    add_bullet(
        "Provides a searchable, tamper-evident log of every single action performed by both humans and AI agents. "
        "Essential for enterprise compliance (SOC2/ISO27001).",
        "6. Audit Ledger: "
    )

    # 7. Presentation & Viva Defense Guide
    add_heading_1("7. How to Present This Project (Demo Script & Viva Defense)")
    add_callout(
        "Follow this exact 4-stage presentation script during your project viva or interview demo. "
        "It focuses on business value, architectural elegance, and practical execution.",
        "Recommended Presentation Flow"
    )

    add_heading_2("Stage 1: The Hook & Introduction (1 Minute)")
    add_body(
        "\"Good morning/afternoon. Today I am presenting OpsPilot, an Enterprise AI Operations Copilot. "
        "In modern cloud environments, when a deployment breaks at 2 AM, engineers are forced to switch between multiple tabs—"
        "reading raw GitHub logs, checking PostgreSQL connection pools, and emailing incident teams. "
        "OpsPilot automates this entire triage process using AI, but solves the critical safety risk: it guarantees that an AI model "
        "can never make destructive changes to production code or databases without human cryptographic authorization.\""
    )

    add_heading_2("Stage 2: Explaining the Architecture & MCP (1.5 Minutes)")
    add_body(
        "\"Under the hood, OpsPilot is built on Anthropic's Model Context Protocol (FastMCP). Instead of hardcoding API calls into prompts, "
        "OpsPilot runs three dedicated microservices: a GitHub MCP server, a PostgreSQL MCP server, and a Productivity MCP server. "
        "Our LangGraph AI agent parses engineer intent, selects the right tool dynamically, and fetches live context.\""
    )

    add_heading_2("Stage 3: The Live Demo Walkthrough (2.5 Minutes)")
    add_bullet(
        "\"Notice how the dashboard aggregates live metrics across our GitHub repositories and database clusters.\"",
        "Step 1 (Dashboard): "
    )
    add_bullet(
        "\"I'll ask the AI Copilot: 'Show me any failing workflows in our connected repos'. The AI queries our FastMCP GitHub server and returns the exact failure in seconds.\"",
        "Step 2 (AI Assistant): "
    )
    add_bullet(
        "\"We inspect the failed build, view the error trace, and click 'Generate AI Fix'. The AI analyzes the error and drafts a clean patch.\"",
        "Step 3 (Pipelines Triage): "
    )
    add_bullet(
        "\"Notice what happens when the AI tries to submit the fix: it is BLOCKED by our Human-in-the-Loop boundary. It does not blindly push to GitHub. "
        "It enters our Approval Center as a PENDING request.\"",
        "Step 4 (HITL Interception): "
    )
    add_bullet(
        "\"Now, switching to the Admin role, the Admin reviews the exact diff and clicks 'Approve'. An HMAC-SHA256 nonced token verifies the decision, "
        "and the GitHub PR is created live. Everything is logged in the Audit Trail.\"",
        "Step 5 (Admin Approval & PR Creation): "
    )

    add_heading_2("Stage 4: Defending Common Viva / Interview Questions")
    
    qa_list = [
        ("Q: Why did you use FastMCP instead of standard REST APIs?",
         "A: FastMCP (Model Context Protocol) provides a standardized, model-agnostic contract for exposing data and actions to LLMs. "
         "Instead of embedding custom API client code inside prompt templates, FastMCP standardizes tool schemas, input validation, "
         "and streaming. If we switch LLMs or add a Kubernetes cluster tomorrow, we only write a new MCP server without touching the AI agent."),

        ("Q: What prevents the AI from bypassing the approval center?",
         "A: The execution layer requires a cryptographically signed approval token (`nonce.timestamp.hash.signature`) generated by the backend "
         "using a server-side secret (`OPSPILOT_APPROVAL_SECRET`). The AI agent does not have access to this secret and cannot generate tokens. "
         "Any tool call categorized as 'write' will fail with an HTTP 403 / PermissionDenied unless this valid signature is present."),

        ("Q: What is the difference between the Admin and Operator logins?",
         "A: The Operator is the 'investigator' who interacts with the AI, inspects logs, and drafts solutions. The Admin is the 'gatekeeper' "
         "who manages integrations and cryptographically signs off on destructive actions. This implements the enterprise security principle of "
         "Separation of Duties (PoLP)."),

        ("Q: What happens if an external service like GitHub is down?",
         "A: OpsPilot implements a resilient graceful degradation pattern. If the live GitHub API or scraper fails, the MCP server returns "
         "cached or structured offline diagnostic information, alerting the user to connectivity issues without crashing the application.")
    ]

    for q, a in qa_list:
        add_bullet(a, f"{q} ")

    doc.save(output_path)
    print(f"DOCX successfully generated at: {output_path}")

if __name__ == "__main__":
    docx_path = r"d:\OpsPilot Project\OpsPilot_Complete_Project_Workflow.docx"
    generate_docx(docx_path)
