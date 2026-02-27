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
    "gate_state": "WAITING"
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

    if event == "VIP_ENTERED_TERMINAL":
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

    elif event == "FLIGHT_CANCELLED":
        if context["current_location"] == "LOUNGE":
            # lounge remains 'ACTIVE'
            context["overall_state"] = "REBOOKING_PENDING"
            context["transport_state"] = "HOLD"

    elif event == "BOARDING_STARTED":
        context["lounge_state"] = "COMPLETED"
        context["current_location"] = "GATE"
        context["gate_state"] = "BOARDING"

    elif event == "FLIGHT_LANDED":
        context["current_leg_index"] += 1
        if context["current_leg_index"] == 1:
            context["journey_type"] = "TRANSIT"
            context["current_location"] = "TRANSIT_AREA"

    elif event == "VIP_LATE_TO_LOUNGE":
        context["lounge_state"] = "DENIED_TIME_PRIORITY"
        context["current_location"] = "DIRECT_TO_GATE"

    elif event == "BAGGAGE_CLAIMED":
        context["baggage_state"] = "CLAIMED"

    elif event == "VIP_EXITED_TERMINAL":
        if context["baggage_state"] == "CLAIMED":
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
