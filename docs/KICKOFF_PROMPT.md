# Kickoff Prompt for the Sim Chair PC Claude Code Instance

Copy everything inside the block below, replace the folder path on the first
line with wherever these .md files live on the Windows PC, and send it as the
first message.

---

```
Read every .md file in this folder before doing anything else:
C:\<REPLACE-WITH-PATH-TO-THIS-FOLDER>

Start with HANDOFF_GUIDE.md — it is your mission brief and defines your
reading order, constraints, and safety rules. Then read the rest in the order
it specifies.

Context: I'm Ryan Simpson, team lead. You are running on the sim chair
Windows PC of the Marvin teleoperation system. We have ~2 weeks to take every
subsystem from "roughly works" to demo-grade before August 6 (CARS symposium
+ the university president touring our lab). The docs contain everything: the
current architecture, the researched target architecture, known issues, and a
phased plan with acceptance gates.

Hard rules, even though the docs repeat them:
- NEVER send drive-enable (mode=1) commands on your own initiative. I decide
  when the kart moves. Default assumption for motor tests: kart on stands.
- NEVER modify anything inside /home/dinosaur/IGVC/ on the Jetson.
- The D-BOX chair moves a human — new motion code stays clamped to 50% range
  and ramps (never snaps) until I approve the tuning.
- Don't delete or break the currently working JPEG video path until its
  replacement passes the Phase 1 gate. Build alongside, verify, then switch.

After reading, do these in order:
1. Give me a short summary of the system and the plan as you understand it,
   plus anything in the docs that seems contradictory or stale — the local
   code on this machine and the Jetson is the source of truth, the docs are
   the map. Flag mismatches; don't silently trust either side.
2. Inventory what's actually on this machine (`C:\Users\VRX 226\cursor-test\windows\`
   and `C:\Users\VRX 226\Test Workspace\`) and confirm you can reach the Jetson
   (ssh dinosaur@100.93.121.3, and verify `tailscale ping` says "direct").
3. Then start Phase 0 from HANDOFF_GUIDE.md (baseline measurements — create
   MEASUREMENTS.md). Do not start Phase 1 until I've seen the baselines.

Work one phase at a time, verify each gate before moving on, and keep
MEASUREMENTS.md and KNOWN_ISSUES_AND_HISTORY.md updated as you go.
```
