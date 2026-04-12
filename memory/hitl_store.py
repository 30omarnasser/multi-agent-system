import os
import json
import redis
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class HITLStore:
    """
    Human-in-the-loop approval store using Redis.
    When an agent needs approval, it creates a pending request here.
    The API polls this store and blocks until approved or rejected.
    """

    def __init__(self, ttl_seconds: int = 300):
        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
        )
        self.ttl = ttl_seconds  # 5 min default — pending requests expire
        print(f"[HITLStore] Connected. TTL={ttl_seconds}s")

    # ─── Create & Manage Requests ─────────────────────────────

    def create_request(
        self,
        session_id: str,
        agent: str,
        action: str,
        details: dict,
        risk_level: str = "medium",
    ) -> str:
        """
        Create a new pending approval request.
        Returns the request_id.
        """
        request_id = f"hitl_{uuid.uuid4().hex[:12]}"
        request = {
            "request_id": request_id,
            "session_id": session_id,
            "agent": agent,
            "action": action,
            "details": details,
            "risk_level": risk_level,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "decided_at": None,
            "decision": None,
            "feedback": "",
        }
        key = f"hitl:{request_id}"
        self.client.setex(key, self.ttl, json.dumps(request))

        # Also add to session's pending list
        self.client.lpush(f"hitl:session:{session_id}", request_id)
        self.client.expire(f"hitl:session:{session_id}", self.ttl)

        # Add to global pending list
        self.client.lpush("hitl:pending", request_id)

        print(f"[HITLStore] Created request: {request_id} | "
              f"agent={agent} | action={action} | risk={risk_level}")
        return request_id

    def get_request(self, request_id: str) -> dict | None:
        """Get a request by ID."""
        key = f"hitl:{request_id}"
        raw = self.client.get(key)
        if raw:
            return json.loads(raw)
        return None

    def approve(self, request_id: str, feedback: str = "") -> bool:
        """Approve a pending request."""
        return self._decide(request_id, "approved", feedback)

    def reject(self, request_id: str, feedback: str = "") -> bool:
        """Reject a pending request."""
        return self._decide(request_id, "rejected", feedback)

    def _decide(self, request_id: str, decision: str, feedback: str) -> bool:
        key = f"hitl:{request_id}"
        raw = self.client.get(key)
        if not raw:
            return False

        request = json.loads(raw)
        request["status"] = decision
        request["decision"] = decision
        request["feedback"] = feedback
        request["decided_at"] = datetime.utcnow().isoformat()

        self.client.setex(key, self.ttl, json.dumps(request))

        # Remove from pending list
        self.client.lrem("hitl:pending", 0, request_id)

        print(f"[HITLStore] {decision.upper()}: {request_id} | feedback='{feedback}'")
        return True

    def wait_for_decision(
        self,
        request_id: str,
        timeout_seconds: int = 120,
        poll_interval: float = 1.0,
    ) -> str:
        """
        Block until the request is approved/rejected or times out.
        Returns: 'approved', 'rejected', or 'timeout'
        """
        import time
        elapsed = 0.0

        while elapsed < timeout_seconds:
            request = self.get_request(request_id)
            if not request:
                return "timeout"
            if request["status"] in ("approved", "rejected"):
                return request["status"]
            time.sleep(poll_interval)
            elapsed += poll_interval

        # Auto-approve on timeout to avoid blocking forever
        print(f"[HITLStore] TIMEOUT on {request_id} — auto-approving")
        self.approve(request_id, feedback="Auto-approved after timeout")
        return "timeout"

    # ─── Listing ──────────────────────────────────────────────

    def get_pending_requests(self) -> list[dict]:
        """Get all currently pending requests."""
        request_ids = self.client.lrange("hitl:pending", 0, -1)
        requests = []
        for rid in request_ids:
            req = self.get_request(rid)
            if req and req["status"] == "pending":
                requests.append(req)
        return requests

    def get_session_requests(self, session_id: str) -> list[dict]:
        """Get all requests for a session."""
        request_ids = self.client.lrange(
            f"hitl:session:{session_id}", 0, -1
        )
        requests = []
        for rid in request_ids:
            req = self.get_request(rid)
            if req:
                requests.append(req)
        return requests

    def get_request_count(self) -> dict:
        """Count requests by status."""
        pending_ids = self.client.lrange("hitl:pending", 0, -1)
        return {
            "pending": len([
                r for r in [self.get_request(rid) for rid in pending_ids]
                if r and r["status"] == "pending"
            ])
        }

    def clear_session(self, session_id: str):
        """Clear all requests for a session."""
        request_ids = self.client.lrange(
            f"hitl:session:{session_id}", 0, -1
        )
        for rid in request_ids:
            self.client.delete(f"hitl:{rid}")
            self.client.lrem("hitl:pending", 0, rid)
        self.client.delete(f"hitl:session:{session_id}")