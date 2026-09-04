# AVL Summer Cohort 2026: Final Deliverables

**Due:** Friday, August 7, 2026, 11:59 PM  
**Email To:** mghasemi@cpp.edu  
**CC:** rmsimpson@cpp.edu, kbraga@cpp.edu  
**From:** Team lead (Ryan Simpson)

---

## Pack contents

Markdown sources stay as-is. Office exports (same content) are in [`office/`](office/):

| # | Required deliverable | Markdown (source) | Office export |
|---|----------------------|-------------------|---------------|
| 1 | Written Technical Report | [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md) | [office/TECHNICAL_REPORT.docx](office/TECHNICAL_REPORT.docx) |
| 2 | Slide Deck (16 slides) | [SLIDE_DECK.md](SLIDE_DECK.md) · [slide_deck.html](slide_deck.html) | [office/SLIDE_DECK.pptx](office/SLIDE_DECK.pptx) |
| 3 | Demo Video script | [DEMO_VIDEO_SCRIPT.md](DEMO_VIDEO_SCRIPT.md) | [office/DEMO_VIDEO_SCRIPT.docx](office/DEMO_VIDEO_SCRIPT.docx) + **record** `DEMO_VIDEO.mp4` |
| 4 | Codebase & Handoff | [HANDOFF_PACKAGE.md](HANDOFF_PACKAGE.md) | [office/HANDOFF_PACKAGE.docx](office/HANDOFF_PACKAGE.docx) |

Re-export after editing MD: `python docs\deliverables\export_office.py`

Related section briefs (optional extras): [`../deck/`](../deck/)

---

## How to export for email

### Technical report → PDF
1. Open `TECHNICAL_REPORT.md` in Word, Google Docs, or VS Code Markdown PDF  
2. Set ~11 pt body, 1-inch margins  
3. Save as `AVL_Summer2026_Marvin_SimChair_Technical_Report.pdf`

### Slide deck → PDF or PPTX
1. **Easiest:** open `slide_deck.html` in Chrome → present with arrow keys  
2. **PDF:** Chrome Print → Save as PDF (landscape) while advancing, or use a screen-to-PDF tool  
3. **Marp:** if Marp CLI/extension installed: `marp SLIDE_DECK.md --pptx` or `--pdf`

### Demo video
1. Follow [DEMO_VIDEO_SCRIPT.md](DEMO_VIDEO_SCRIPT.md)  
2. Export MP4 1080p  
3. Name: `AVL_Summer2026_Marvin_SimChair_Demo.mp4`  
4. If too large for email, upload Drive/OneDrive and paste link in the email body

### Handoff
Attach `HANDOFF_PACKAGE.md` (or PDF export) and/or zip of `docs/` + point to workspace structure.

---

## Suggested email body

```
Subject: AVL Summer Cohort 2026 Final Deliverables: Marvin Sim Chair Teleoperation

Hi Dr. Ghasemi,

Please find attached the AVL Summer Cohort 2026 final deliverables for the
Marvin Sim Chair teleoperation project (team lead: Ryan Simpson).

1. Written Technical Report (PDF)
2. Slide Deck (PDF / HTML)
3. Demo Video (MP4 or Drive link)
4. Codebase & Handoff Documentation

Team: Ryan Simpson, Tyler Carrasco, Yi-Szen Tang, Kevin Xu, Justin Dang
Mentor: Dr. Behnam Bahr

Thank you,
Ryan Simpson
```

---

## Pre-send checklist

- [ ] Technical report exported to PDF (≥8 pages when formatted)  
- [ ] Slide deck has ≥12 slides (HTML pack has 16)  
- [ ] Demo video recorded 3-8 min showing real operation  
- [ ] Handoff doc attached  
- [ ] Email To + both CCs  
- [ ] Lab-accurate claims (UDP JPEG primary; IMU E2E only if filmed) 

---

## Open HTML slides now

Double-click or:

```powershell
start "" "C:\Users\VRX 226\cursor-test\docs\deliverables\slide_deck.html"
```
