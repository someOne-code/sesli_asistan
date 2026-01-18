# 🧪 UAT Checklist (User Acceptance Testing)

Please check off these items as you perform the manual testing using `interactive_uat.py` and the web interface.

## Prerequisite
- [ ] Backend Server is running (`python -m uvicorn app.main:app`)
- [ ] `index.html` is open in the browser
- [ ] `interactive_uat.py` is running (optional, for log verification)

## 🎬 Scenario 1: Basic Call Flow
- [ ] **Action**: Click Green 'Call' (📞) button.
- [ ] **Verify**: "🎤 Dinliyorum..." text appears.
- [ ] **Verify**: Timer starts counting.
- [ ] **Verify**: Microphone permission is granted and active.

## 🎬 Scenario 2: Music Intent
- [ ] **Action**: Say "Metallica çal" clearly.
- [ ] **Verify**: Audio response is heard (e.g., "Metallica çalınıyor...").
- [ ] **Verify**: "Dinliyorum..." state resumes after response (or similar active state).
- [ ] **Verify (DB)**: `interactive_uat.py` confirms log entry found with "Metallica".
- [ ] **Verify (DB)**: Intent is correctly identified as "music".

## 🎬 Scenario 3: End Call
- [ ] **Action**: Click Red 'Hang Up' (❌) button.
- [ ] **Verify**: Page resets or reloads.
- [ ] **Verify**: "Notlar kaydedildi" alert (or similar notification) appears.
- [ ] **Verify (DB)**: Call duration and final status logged correctly.

## 🐛 Issues Found
- [ ] (Add notes here if something fails)
