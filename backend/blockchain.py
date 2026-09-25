"""
NEXUS Blockchain Threat Ledger — Immutable Security Audit Log
=============================================================

CORE PRINCIPLE: Mathematically Tamper-Proof Security Auditing

Every critical security event (prompt injection, SQLi, sensitive data block,
privilege escalation) is hashed and mined into an immutable local hash-chain
using SHA-256 Proof-of-Work.

Features:
1. Block data structure with index, timestamp, event_type, data, prev_hash, nonce, hash
2. Proof-of-Work mining (difficulty=2 for instant demo speed <50ms)
3. Cryptographic chain integrity validation
4. Real-time tamper simulation (the "wow" moment for hackathon judges)
5. Tamper restoration
"""

import hashlib
import json
import time
from typing import List, Dict, Any, Tuple, Optional


class Block:
    """Represents a single block in the NEXUS Threat Ledger."""

    def __init__(
        self,
        index: int,
        timestamp: float,
        event_type: str,
        event_data: Dict[str, Any],
        previous_hash: str,
        nonce: int = 0,
        hash_val: Optional[str] = None,
    ):
        self.index = index
        self.timestamp = timestamp
        self.event_type = event_type
        self.event_data = event_data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = hash_val or self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calculates SHA-256 hash of block contents."""
        block_string = (
            f"{self.index}"
            f"{self.timestamp:.4f}"
            f"{self.event_type}"
            f"{json.dumps(self.event_data, sort_keys=True)}"
            f"{self.previous_hash}"
            f"{self.nonce}"
        )
        return hashlib.sha256(block_string.encode("utf-8")).hexdigest()

    def mine_block(self, difficulty: int = 2) -> None:
        """Simple Proof-of-Work: finds nonce such that hash starts with '0' * difficulty."""
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "event_data": self.event_data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }


class ThreatBlockchain:
    """
    Immutable Blockchain Audit Ledger.
    Tracks all security events with cryptographic chaining.
    """

    def __init__(self, difficulty: int = 2):
        self.difficulty = difficulty
        self.chain: List[Block] = []
        self._original_state_backup: Optional[List[Dict[str, Any]]] = None
        self._is_tampered = False
        self.create_genesis_block()

    def create_genesis_block(self) -> None:
        """Initializes the genesis block of the threat ledger."""
        genesis_block = Block(
            index=0,
            timestamp=time.time(),
            event_type="GENESIS",
            event_data={
                "message": "NEXUS Threat Ledger Genesis Block Initialized",
                "consensus": "Proof-of-Work (SHA-256)",
                "security_protocol": "Zero-Trust Data Diode",
            },
            previous_hash="0" * 64,
        )
        genesis_block.mine_block(self.difficulty)
        self.chain = [genesis_block]

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_security_block(self, event_type: str, event_data: Dict[str, Any]) -> Block:
        """Mines and appends a new block for a security event."""
        # Clean event data to ensure no non-serializable objects
        safe_data = {
            "threat_type": event_data.get("threat_type", "SECURITY_EVENT"),
            "risk_score": event_data.get("risk_score", 0),
            "risk_level": event_data.get("risk_level", "LOW"),
            "decision": event_data.get("decision", "RECORDED"),
            "reason": event_data.get("reason", "")[:120],
            "query_snippet": event_data.get("query_snippet", "")[:60],
        }

        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            event_type=event_type,
            event_data=safe_data,
            previous_hash=self.get_latest_block().hash,
        )
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        return new_block

    def validate_chain(self) -> Tuple[bool, Optional[int], str]:
        """
        Verifies that every block's hash is valid and matches previous_hash.
        Returns: (is_valid, invalid_index, message)
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # 1. Recalculate hash to verify data was not modified
            if current.hash != current.calculate_hash():
                return False, i, f"Block #{current.index} data has been modified! Hash mismatch."

            # 2. Verify previous_hash linkage
            if current.previous_hash != previous.hash:
                return (
                    False,
                    i,
                    f"Block #{current.index} previous_hash does not match Block #{previous.index} hash! Chain link broken.",
                )

        return True, None, "Blockchain integrity verified. All cryptographic hashes match."

    def simulate_tamper(self, block_index: int = 1) -> Dict[str, Any]:
        """
        DEMO MOMENT: Simulates a rogue administrator modifying historical audit logs.
        Alters data without re-mining, causing immediate cryptographic chain invalidation.
        """
        if len(self.chain) <= 1:
            # Need at least 2 blocks to demonstrate tamper cascade
            self.add_security_block(
                "SENSITIVE_DATA_ACCESS",
                {
                    "threat_type": "SENSITIVE_DATA_ACCESS",
                    "risk_score": 75,
                    "risk_level": "HIGH",
                    "decision": "BLOCKED",
                    "reason": "Protected field 'phone' requested.",
                    "query_snippet": "Show everyone's phone numbers",
                },
            )

        target_idx = min(block_index, len(self.chain) - 1)
        if target_idx == 0 and len(self.chain) > 1:
            target_idx = 1

        # Deep copy backup for accurate restoration
        if not self._is_tampered:
            self._original_state_backup = json.loads(json.dumps([b.to_dict() for b in self.chain]))

        # Malicious modification: change decision from BLOCKED to ALLOWED (rogue admin covering tracks)
        self.chain[target_idx].event_data["decision"] = "ALLOWED"
        self.chain[target_idx].event_data["modified_by"] = "ROGUE_ADMIN_SIMULATION"
        self.chain[target_idx].event_data["reason"] = "[TAMPERED] Log modified to conceal unauthorized query."
        # Notice: we DO NOT recalculate the hash. This causes the validation to fail!
        self._is_tampered = True

        is_valid, inv_idx, msg = self.validate_chain()
        return {
            "status": "TAMPERED",
            "tampered_block_index": target_idx,
            "chain_valid": is_valid,
            "invalid_block_index": inv_idx,
            "message": msg,
        }

    def restore_chain(self) -> Dict[str, Any]:
        """Restores the blockchain to pristine valid state."""
        if self._original_state_backup:
            self.chain = [
                Block(
                    index=d["index"],
                    timestamp=d["timestamp"],
                    event_type=d["event_type"],
                    event_data=d["event_data"],
                    previous_hash=d["previous_hash"],
                    nonce=d["nonce"],
                    hash_val=d["hash"],
                )
                for d in self._original_state_backup
            ]
            self._original_state_backup = None

        self._is_tampered = False
        is_valid, _, msg = self.validate_chain()
        return {
            "status": "RESTORED",
            "chain_valid": is_valid,
            "message": msg,
        }

    def get_summary(self) -> Dict[str, Any]:
        is_valid, inv_idx, msg = self.validate_chain()
        return {
            "total_blocks": len(self.chain),
            "difficulty": self.difficulty,
            "chain_valid": is_valid,
            "is_tampered": self._is_tampered,
            "invalid_block_index": inv_idx,
            "status_message": msg,
            "blocks": [b.to_dict() for b in self.chain],
        }


# Global singleton threat ledger
threat_ledger = ThreatBlockchain(difficulty=2)
