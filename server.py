from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import uvicorn

app = FastAPI()

# Add CORS middleware to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory VIP context
VIP_CONTEXT = {
    "itinerary": ["HYD", "DEL", "LHR"],
    "current_leg_index": 0,
    "journey_type": "DEPARTURE",
    "current_location": "OUTSIDE",
    "flight_state": "SCHEDULED",
    "baggage_state": "CHECKED",
    "transport_state": "PENDING",
    "lounge_state": "PENDING",
    "overall_state": "ACTIVE",
    "gate_state": "WAITING",
    "connection_risk_score": 0
}

# Dummy boarding time variable
boarding_time = 60  # minutes

# List to manage connected WebSocket clients
connected_clients: list[WebSocket] = []


class EventRequest(BaseModel):
    event: str


async def broadcast_state():
    """Broadcast VIP_CONTEXT to all connected WebSocket clients."""
    message = json.dumps(VIP_CONTEXT)
    for client in connected_clients:
        try:
            await client.send_text(message)
        except:
            pass


def reconcile(context: dict, event: str):
    """State machine reconciliation function."""
    global boarding_time

    if event == "RESET":
        context["current_leg_index"] = 0
        context["journey_type"] = "DEPARTURE"
        context["current_location"] = "OUTSIDE"
        context["flight_state"] = "SCHEDULED"
        context["baggage_state"] = "CHECKED"
        context["transport_state"] = "PENDING"
        context["lounge_state"] = "PENDING"
        context["overall_state"] = "ACTIVE"
        context["gate_state"] = "WAITING"
        context["connection_risk_score"] = 0

    elif event == "VIP_ENTERED_TERMINAL":
        context["current_location"] = "CHECKIN"
        context["transport_state"] = "COMPLETED"
        context["lounge_state"] = "RESERVED"

    elif event == "FACE_VERIFIED":
        if context["lounge_state"] == "RESERVED":
            context["current_location"] = "LOUNGE"
            context["lounge_state"] = "ACTIVE"

    elif event == "FLIGHT_DELAYED":
        boarding_time += 30  # Extend boarding time
        print("Lounge extended")
        
        # Predictive Risk Engine: increase connection risk by 35%
        context["connection_risk_score"] = min(100, context["connection_risk_score"] + 35)
        
        # Auto-escalate to CRITICAL_RISK if risk exceeds 70%
        if context["connection_risk_score"] > 70:
            context["overall_state"] = "CRITICAL_RISK"
            context["transport_state"] = "ESCORT_BUGGY_REQUIRED"
            print(f"CRITICAL RISK: Connection risk at {context['connection_risk_score']}% - Escort buggy dispatched")

    elif event == "FLIGHT_CANCELLED":
        if context["current_location"] == "LOUNGE":
            # lounge remains 'ACTIVE'
            context["overall_state"] = "REBOOKING_PENDING"
            context["transport_state"] = "HOLD"

    elif event == "BOARDING_STARTED":
        context["lounge_state"] = "COMPLETED"
        context["current_location"] = "MOVING_TO_GATE"
        context["gate_state"] = "BOARDING"
        context["overall_state"] = "ACTIVE"  # Clear any previous rebooking/escalated states

    elif event == "VIP_ARRIVED_AT_GATE":
        context["current_location"] = "GATE"
        context["gate_state"] = "WAITING_TO_BOARD"

    elif event == "FLIGHT_LANDED":
        # Only increment if not at the last leg
        if context["current_leg_index"] < len(context["itinerary"]) - 1:
            context["current_leg_index"] += 1
            if context["current_leg_index"] == 1:
                context["journey_type"] = "TRANSIT"
                context["current_location"] = "TRANSIT_AREA"
            elif context["current_leg_index"] == 2:
                context["journey_type"] = "ARRIVAL"
                context["current_location"] = "BAGGAGE_CLAIM"

    elif event == "VIP_LATE_TO_LOUNGE":
        context["lounge_state"] = "DENIED_TIME_PRIORITY"
        context["current_location"] = "DIRECT_TO_GATE"

    elif event == "BAGGAGE_TRANSFERRED":
        context["baggage_state"] = "TRANSFERRED_TO_NEXT_LEG"

    elif event == "BAGGAGE_CLAIMED":
        context["baggage_state"] = "CLAIMED"

    elif event == "VIP_EXITED_TERMINAL":
        if context["journey_type"] == "ARRIVAL" and context["baggage_state"] == "CLAIMED":
            context["transport_state"] = "DRIVER_ASSIGNED"

    elif event == "VIP_NO_SHOW":
        context["transport_state"] = "CANCELLED"
        context["overall_state"] = "ESCALATED"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint to manage connected clients."""
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        # Send current state on connection
        await websocket.send_text(json.dumps(VIP_CONTEXT))
        while True:
            # Keep connection alive, wait for messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)


@app.post("/event")
async def handle_event(request: EventRequest):
    """REST POST endpoint to handle events."""
    reconcile(VIP_CONTEXT, request.event)
    await broadcast_state()
    return {"status": "ok", "context": VIP_CONTEXT}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
