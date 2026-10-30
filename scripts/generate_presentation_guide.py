"""
OpsPilot Presentation Guide Generator
Creates OpsPilot_Presentation_Guide.docx and OpsPilot_Presentation_Guide.pdf
containing complete presentation points, demo scripts, architecture, and defense Q&A.
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

def set_cell_margins(cell, top=120, bottom=120, left=180, right=180):
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

def create_presentation_document():
    doc = docx.Document()

    # Set 1-inch margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

    # Color Palette
    PRIMARY_EMERALD = RGBColor(16, 185, 129)   # #10B981
    DARK_NAVY = RGBColor(15, 23, 42)           # #0F172A
    ACCENT_BLUE = RGBColor(37, 99, 235)        # #2563EB
    TEXT_BODY = RGBColor(51, 65, 85)           # #334155
    MUTED_GRAY = RGBColor(100, 116, 139)       # #64748B
    SPEAKER_NOTE_BG = "F0FDF4"                 # Light emerald
    CALLOUT_BG = "F1F5F9"                      # Light slate
    BORDER_GREEN = "10B981"

    # Helper formatters
    def add_title(text, subtitle_text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = p.add_run(text + "\n")
        r1.font.name = "Segoe UI"
        r1.font.size = Pt(26)
        r1.font.bold = True
        r1.font.color.rgb = PRIMARY_EMERALD

        r2 = p.add_run(subtitle_text)
        r2.font.name = "Segoe UI"
        r2.font.size = Pt(13)
        r2.font.color.rgb = DARK_NAVY
        p.paragraph_format.space_after = Pt(14)

    def add_h1(text):
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.font.name = "Segoe UI"
        r.font.size = Pt(16)
        r.font.bold = True
        r.font.color.rgb = PRIMARY_EMERALD
        p.paragraph_format.space_before = Pt(16)
        p.paragraph_format.space_after = Pt(4)

    def add_h2(text):
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.font.name = "Segoe UI"
        r.font.size = Pt(12.5)
        r.font.bold = True
        r.font.color.rgb = DARK_NAVY
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)

    def add_p(text, bold_prefix=None):
        p = doc.add_paragraph()
        if bold_prefix:
            rb = p.add_run(bold_prefix + " ")
            rb.font.name = "Segoe UI"
            rb.font.size = Pt(10)
            rb.font.bold = True
            rb.font.color.rgb = DARK_NAVY
        r = p.add_run(text)
        r.font.name = "Segoe UI"
        r.font.size = Pt(10)
        r.font.color.rgb = TEXT_BODY
        p.paragraph_format.space_after = Pt(3)
        return p

    def add_bullet(text, bold_prefix=None):
        p = doc.add_paragraph(style='List Bullet')
        if bold_prefix:
            rb = p.add_run(bold_prefix + " ")
            rb.font.name = "Segoe UI"
            rb.font.size = Pt(10)
            rb.font.bold = True
            rb.font.color.rgb = DARK_NAVY
        r = p.add_run(text)
        r.font.name = "Segoe UI"
        r.font.size = Pt(10)
        r.font.color.rgb = TEXT_BODY
        p.paragraph_format.space_after = Pt(2)
        return p

    def add_speech_box(spoken_text, action_note=None):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.rows[0].cells[0]
        cell.width = Inches(6.7)
        set_cell_background(cell, SPEAKER_NOTE_BG)
        set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
        
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(2)
        r_lbl = p.add_run("🎙️ What to Say (Speaking Script):\n")
        r_lbl.font.name = "Segoe UI"
        r_lbl.font.size = Pt(9.5)
        r_lbl.font.bold = True
        r_lbl.font.color.rgb = PRIMARY_EMERALD

        r_speech = p.add_run(f'"{spoken_text}"\n')
        r_speech.font.name = "Segoe UI"
        r_speech.font.size = Pt(9.5)
        r_speech.font.italic = True
        r_speech.font.color.rgb = DARK_NAVY

        if action_note:
            r_act = p.add_run(f"👉 Action on Screen: {action_note}")
            r_act.font.name = "Segoe UI"
            r_act.font.size = Pt(9)
            r_act.font.bold = True
            r_act.font.color.rgb = ACCENT_BLUE

        p_after = doc.add_paragraph()
        p_after.paragraph_format.space_after = Pt(4)

    # -------------------------------------------------------------
    # Title & Metadata
    # -------------------------------------------------------------
    add_title("OPSPILOT ENTERPRISE AI PLATFORM", "Project Presentation Guide, Live Demo Scripts & Examiner Defense Notes")

    meta_tbl = doc.add_table(rows=4, cols=2)
    meta_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_info = [
        ("Platform", "OpsPilot: Autonomous AI Operations Assistant & FastMCP Governance Engine"),
        ("Key Architecture", "LangGraph Stateful Agent + 33 FastMCP Tools + Cryptographic HITL + React 18 UI"),
        ("Live Integrations", "GitHub REST API v3 (Multi-Profile), Neon PostgreSQL Cloud, Gmail Live SMTP (Port 587)"),
        ("Test & Verification Status", "31/31 Automated Tests Passing (100%), 0 TypeScript Compilation Errors")
    ]
    for idx, (label, val) in enumerate(meta_info):
        row = meta_tbl.rows[idx]
        c0, c1 = row.cells[0], row.cells[1]
        c0.width, c1.width = Inches(2.0), Inches(4.7)
        c0.text, c1.text = label, val
        c0.paragraphs[0].runs[0].font.name = "Segoe UI"
        c0.paragraphs[0].runs[0].font.size = Pt(9.5)
        c0.paragraphs[0].runs[0].font.bold = True
        c0.paragraphs[0].runs[0].font.color.rgb = DARK_NAVY
        c1.paragraphs[0].runs[0].font.name = "Segoe UI"
        c1.paragraphs[0].runs[0].font.size = Pt(9.5)
        c1.paragraphs[0].runs[0].font.color.rgb = TEXT_BODY
        set_cell_background(c0, "F8FAFC")
        set_cell_background(c1, "FFFFFF")
        set_cell_margins(c0, 60, 60, 80, 80)
        set_cell_margins(c1, 60, 60, 80, 80)

    p_space = doc.add_paragraph()
    p_space.paragraph_format.space_after = Pt(6)

    # -------------------------------------------------------------
    # 1. 30-Second Elevator Pitch
    # -------------------------------------------------------------
    add_h1("1. The 30-Second Elevator Pitch (Opening Statement)")
    add_p(
        "Start your presentation with confidence using this exact pitch. It immediately tells the audience what problem OpsPilot solves and why it stands out from ordinary AI bots."
    )
    add_speech_box(
        "Good morning / afternoon everyone. Today I am excited to present OpsPilot — an enterprise-grade Autonomous AI Operations Assistant designed for DevOps, SRE, and Platform Engineering teams.\n\n"
        "Most AI assistants today are simple chat wrappers that either hallucinate operational data or blindly execute dangerous commands on production servers. OpsPilot solves this by combining stateful LangGraph multi-turn reasoning with FastMCP microservices, backed by a strict cryptographic Human-in-the-Loop security gate.\n\n"
        "OpsPilot can safely inspect live Cloud databases, manage GitHub repositories across multiple profiles, and dispatch real-time incident emails via SMTP — without ever executing a destructive action without explicit, tamper-proof human authorization.",
        action_note="Have the OpsPilot Dashboard (http://localhost:5173) open in dark mode on the projector."
    )

    # -------------------------------------------------------------
    # 2. Core Architectural Pillars
    # -------------------------------------------------------------
    add_h1("2. Core Architectural Pillars (The Technical Foundation)")
    add_p(
        "If the jury or professors ask 'What did you actually build?', present these 5 architectural pillars:"
    )

    add_bullet(
        "OpsPilot decouples tool execution into three independent FastMCP microservices (PostgreSQL Operations, GitHub REST API, and Productivity/Email/Calendar), hosting a total of 33 standardized, type-safe tools. Each tool returns a unified MCPEnvelope containing status, execution time, and error telemetry.",
        "Pillar 1: FastMCP Microservice Mesh (33 Tools):"
    )
    add_bullet(
        "The AI agent has zero autonomous write permissions on production infrastructure. Any write operation (creating issues, sending emails, mutating database records) automatically halts the agent and triggers a cryptographic proposal. Execution requires an unbypassable, single-use, HMAC-SHA256 signed capability token with replay prevention.",
        "Pillar 2: Cryptographic Human-in-the-Loop (HITL) Boundary:"
    )
    add_bullet(
        "Features a complete ChatGPT-like sidebar experience with past conversation history, dynamic real-time search, inline conversation renaming, deletion, and a 'New Chat' button. Multi-turn context is persisted via thread checkpointing, allowing seamless context retention across turns.",
        "Pillar 3: Stateful Multi-Turn Memory & ChatGPT-Style UI:"
    )
    add_bullet(
        "Connected to both local storage and live Neon Cloud PostgreSQL (AWS us-east-2) for real-time table discovery, incident inspection, and SLA tracking. Includes real-time GitHub multi-profile switching with instant credential validation via GitHub's REST API.",
        "Pillar 4: Live Enterprise Integrations (GitHub & Neon PostgreSQL):"
    )
    add_bullet(
        "Directly integrated with Google SMTP on port 587 with TLS encryption. Features verified timezone-drift normalization (Indian Standard Time UTC+05:30) and 100% auditable tamper-evident logging for every dispatch.",
        "Pillar 5: Live Gmail SMTP Delivery & Operational Auditing:"
    )

    # -------------------------------------------------------------
    # 3. 5-Minute Live Demo Script
    # -------------------------------------------------------------
    add_h1("3. Step-by-Step 5-Minute Live Demo Flow")
    add_p(
        "Follow this exact step-by-step sequence during your live presentation. It covers every major component within 5 minutes without getting stuck."
    )

    # Demo Step 1
    add_h2("Step 1: Dashboard & System Health Inspection (1 Minute)")
    add_bullet("Navigate to the Dashboard (http://localhost:5173).")
    add_bullet("Show the metric cards: Total Incidents, Pending Approvals, Consumed Tokens, and Active Integrations.")
    add_bullet("Click on 'Integrations' in the top navbar: highlight GitHub, PostgreSQL (Neon Cloud), and Email/Calendar status badges.")
    add_speech_box(
        "Here is the OpsPilot Control Center. As you can see, our system integrates seamlessly with PostgreSQL, GitHub, and corporate productivity channels. The dashboard provides real-time visibility into open incidents, system health, and pending approvals awaiting human authorization.",
        action_note="Hover over the Live Integration badges (GitHub, PostgreSQL, SMTP)."
    )

    # Demo Step 2
    add_h2("Step 2: ChatGPT-Style Multi-Turn Memory & New Chat (1 Minute)")
    add_bullet("Click on 'AI Assistant' in the navigation bar.")
    add_bullet("Show the left-hand sidebar with previous conversation history.")
    add_bullet("Demonstrate the search box filtering past chats.")
    add_bullet("Click '+ New chat' — the interface refreshes into the clean starter hero state with 4 scenario cards.")
    add_speech_box(
        "We designed OpsPilot with an intuitive ChatGPT-style workflow. Operators can access past incident threads, search conversation history, and start clean operational sessions. The assistant retains stateful context across multiple turns using LangGraph checkpointing.",
        action_note="Click '+ New chat' and highlight the 4 starter scenario cards."
    )

    # Demo Step 3
    add_h2("Step 3: Live Neon PostgreSQL Cloud Inspection (1 Minute)")
    add_bullet("In the chat input, type or click: 'Show open critical incidents and operational summary'.")
    add_bullet("Watch OpsPilot invoke the FastMCP `list_incidents` and `get_operations_summary` tools in real time.")
    add_bullet("OpsPilot displays the active critical incident (INC-101 in auth-service) in a clean markdown table.")
    add_speech_box(
        "I will now ask OpsPilot to inspect our operational environment. Notice that OpsPilot invokes our FastMCP PostgreSQL server, queries the database safely in read-only mode, and formats the findings with exact timestamps and severity levels.",
        action_note="Show the agent executing FastMCP read tools and displaying grounded data."
    )

    # Demo Step 4
    add_h2("Step 4: GitHub DevOps Real-Time Multi-Profile Switch (1 Minute)")
    add_bullet("Navigate to 'GitHub DevOps' tab in the navbar.")
    add_bullet("Point out the connected profile (`@adityabhagwat001` with repository `SafeHer`).")
    add_bullet("Click 'Switch / Connect Profile' — show the secure modal with real-time token validation and show/hide token toggle.")
    add_bullet("Explain that OpsPilot validates credentials against GitHub API before switching profiles.")
    add_speech_box(
        "In modern engineering teams, engineers work across multiple GitHub organizations. OpsPilot features live multi-profile switching. When an operator connects a new token, OpsPilot verifies credentials directly with GitHub's REST API and dynamically scopes repository tracking to that verified profile.",
        action_note="Open the 'Switch / Connect Profile' modal and show the verification fields."
    )

    # Demo Step 5
    add_h2("Step 5: Cryptographic Approval Boundary & Live Gmail SMTP Dispatch (1 Minute)")
    add_bullet("Return to 'AI Assistant' and type: 'Send an email to adityabhagwat2181@gmail.com with subject INC-101 Incident Mitigated and body All services restored.'")
    add_bullet("Point out the immediate execution halt: The AI DOES NOT send the email automatically.")
    add_bullet("A glowing 'Human Approval Required' card appears with exact recipient, subject, and body.")
    add_bullet("Navigate to 'Approval Center' (or click Approve right in the chat): Show the proposed parameters.")
    add_bullet("Click 'Approve' — the backend generates the 4-part cryptographic token (`nonce.timestamp.hash.signature`), executes `send_email` through Gmail SMTP (port 587), and logs the event.")
    add_bullet("Click 'Audit Logs' tab: Show the tamper-evident record with tool name, actor, timestamp, and payload.")
    add_speech_box(
        "This is OpsPilot's crowning security feature — the Cryptographic Human-in-the-Loop Boundary. When I requested to send an email, OpsPilot halted execution. It proposed the action and awaited human approval.\n\n"
        "Once approved by an authorized operator, a single-use HMAC-SHA256 signed capability token is generated. The email was dispatched live through Google SMTP, and the nonce was consumed to guarantee replay immunity. Every single action is permanently recorded in our tamper-evident audit log.",
        action_note="Click 'Approve', observe success toast, and show the entry in 'Audit Logs'."
    )

    # -------------------------------------------------------------
    # 4. Metrics & Technical Proof Table
    # -------------------------------------------------------------
    add_h1("4. Key Technical Metrics & Proof Points")
    add_p(
        "Display this summary table or reference these numbers to demonstrate the project's engineering maturity:"
    )

    metrics_tbl = doc.add_table(rows=1, cols=3)
    metrics_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    m_hdr = metrics_tbl.rows[0].cells
    m_hdr[0].text, m_hdr[1].text, m_hdr[2].text = "Dimension", "Specification / Metric", "Technical Benefit"
    for c in m_hdr:
        c.paragraphs[0].runs[0].font.name = "Segoe UI"
        c.paragraphs[0].runs[0].font.size = Pt(9.5)
        c.paragraphs[0].runs[0].font.bold = True
        set_cell_background(c, "E2E8F0")

    metrics_data = [
        ("FastMCP Architecture", "33 Standardized Tools across 3 Servers", "Modular isolation; zero tool bloat in the core agent."),
        ("Security Boundary", "4-part HMAC-SHA256 Token with Nonce", "Prevents unauthorized writes, tampering, and replay attacks."),
        ("Token Freshness", "60-Second Replay & Expiry Window", "Guarantees approved actions cannot be intercepted or delayed."),
        ("Multi-Turn Memory", "LangGraph Thread Checkpointing + SQLite", "Preserves incident context across complex troubleshooting workflows."),
        ("Database Backend", "Neon Cloud PostgreSQL + Local SQLite fallback", "True cloud operational sync with zero-downtime offline resilience."),
        ("Test Verification", "31/31 Pytest Suites Passing (100%)", "Rigorous automated test coverage across RBAC, crypto, and MCP."),
        ("Frontend Build", "React 18 + Vite + TypeScript (0 errors)", "Lightning-fast client bundle, sub-second Hot Module Reload.")
    ]

    for dim, spec, ben in metrics_data:
        row = metrics_tbl.add_row()
        c0, c1, c2 = row.cells
        c0.width, c1.width, c2.width = Inches(1.8), Inches(2.5), Inches(2.4)
        c0.text, c1.text, c2.text = dim, spec, ben
        c0.paragraphs[0].runs[0].font.name = "Segoe UI"
        c0.paragraphs[0].runs[0].font.size = Pt(9)
        c0.paragraphs[0].runs[0].font.bold = True
        c0.paragraphs[0].runs[0].font.color.rgb = DARK_NAVY
        c1.paragraphs[0].runs[0].font.name = "Segoe UI"
        c1.paragraphs[0].runs[0].font.size = Pt(9)
        c1.paragraphs[0].runs[0].font.color.rgb = TEXT_BODY
        c2.paragraphs[0].runs[0].font.name = "Segoe UI"
        c2.paragraphs[0].runs[0].font.size = Pt(9)
        c2.paragraphs[0].runs[0].font.color.rgb = TEXT_BODY
        for c in (c0, c1, c2):
            set_cell_margins(c, 50, 50, 70, 70)

    p_space2 = doc.add_paragraph()
    p_space2.paragraph_format.space_after = Pt(6)

    # -------------------------------------------------------------
    # 5. Examiner & Defense Q&A Cheat Sheet
    # -------------------------------------------------------------
    add_h1("5. Examiner & Defense Q&A Cheat Sheet")
    add_p(
        "Be prepared for these common technical defense questions. These concise answers highlight your deep understanding of security, distributed systems, and AI orchestration."
    )

    qas = [
        (
            "Q1: Why did you use FastMCP instead of standard LangChain tools or custom REST endpoints?",
            "FastMCP implements Anthropic's Model Context Protocol. It decouples tool definition, schema validation, and transport from the AI agent logic. This gives us microservice modularity: the database server, GitHub server, and productivity server run as isolated services with independent failure domains and standardized telemetry envelopes."
        ),
        (
            "Q2: How do you prevent Prompt Injection attacks from executing unauthorized changes?",
            "Prompt injection attacks rely on tricking the LLM into executing dangerous commands. In OpsPilot, even if an attacker tricks the LLM into wanting to delete a database or email a malicious link, the LLM has ZERO autonomous execution permissions. The tool call is intercepted by our code-level approval engine. Without a human clicking 'Approve' and generating an HMAC signature with the server's private secret, the write is cryptographically impossible."
        ),
        (
            "Q3: How does the Cryptographic Approval Token work?",
            "When an operator clicks Approve, the backend creates a token formatted as <nonce>.<timestamp>.<action_hash>.<signature>. The signature is an HMAC-SHA256 hash using an APPROVAL_SECRET over the tool name, workspace ID, nonce, timestamp, and a canonical SHA-256 hash of the exact parameters. If anyone tampers with the parameters or replays an old token, signature verification fails and the request is rejected."
        ),
        (
            "Q4: How do you handle Timezone Drift between local client machines and cloud servers?",
            "We normalized all timestamp generation across both backend and FastMCP servers to UTC using `datetime.datetime.now(datetime.timezone.utc)`. This eliminated naive datetime drift issues (such as IST UTC+05:30) and ensures token expiration windows are strictly and accurately enforced."
        ),
        (
            "Q5: What happens if Neon Cloud PostgreSQL or GitHub is temporarily down?",
            "OpsPilot is built with zero-setup fault tolerance. If live credentials are missing or the cloud network fails, the system automatically falls back to an internal seeded operational SQLite store. This guarantees the platform remains functional and testable under all network conditions."
        )
    ]

    for q, a in qas:
        add_h2(q)
        add_p(a)

    # -------------------------------------------------------------
    # Closing Advice
    # -------------------------------------------------------------
    add_h1("6. Final Presentation Tips")
    add_bullet("Confidence & Clarity: Speak slowly and deliberately. Emphasize that OpsPilot is a platform, not just a chatbot.", "Tip 1:")
    add_bullet("Highlight Safety: Emphasize 'Zero Autonomous Writes' and 'Cryptographic Capability Tokens' — professors love security-first engineering.", "Tip 2:")
    add_bullet("Show Real Code & Real Services: Show live GitHub integration, Neon DB connection, and Gmail SMTP delivery to prove it is a real-world working platform.", "Tip 3:")

    # Save Word Document
    docx_path = os.path.abspath("OpsPilot_Presentation_Guide.docx")
    doc.save(docx_path)
    print(f"Generated DOCX: {docx_path}")

    # Convert to PDF via MS Word COM
    pdf_path = os.path.abspath("OpsPilot_Presentation_Guide.pdf")
    try:
        import win32com.client
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        doc_obj = word.Documents.Open(docx_path)
        doc_obj.SaveAs(pdf_path, FileFormat=17) # 17 = wdFormatPDF
        doc_obj.Close()
        word.Quit()
        print(f"Generated PDF: {pdf_path}")
    except Exception as e:
        print(f"Could not convert to PDF via COM: {e}")

if __name__ == "__main__":
    create_presentation_document()
