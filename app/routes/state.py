from fastapi import APIRouter, Form
from app.core.config import logger
from app.main import get_memory

router = APIRouter()

@router.post("/set-state")
async def set_state(
    session_id: str = Form("global_demo"),
    state: str = Form(...)
):
    """
    Frontend endpoint to update backend state.
    Called when:
    - startCall() → LISTENING
    - TTS starts → SPEAKING
    - TTS ends → LISTENING
    """
    memory = get_memory(session_id)
    
    # Special handling for LISTENING - can be set from any state (recovery)
    if state == "LISTENING":
        memory.force_listening()
        logger.info(f"[STATE] Force set to LISTENING from frontend")
        return {"status": "ok", "state": state}
    
    # For other states, use normal transition validation
    success = memory.set_state(state)
    if not success:
        logger.warning(f"[STATE] Frontend tried invalid transition to {state}")
        return {"status": "rejected", "current_state": memory.get_state()}
    
    return {"status": "ok", "state": state}
