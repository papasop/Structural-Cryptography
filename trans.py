# Structure UTXO + SVM with Spendable Tokens and Provenance

import math
import hashlib
import time
from typing import List, Dict, Optional
from collections import defaultdict

# --- Structure UTXO Definition ---
class StructureUTXO:
    def __init__(self, x, phi_val, delta, entropy, refs, owner):
        self.x = x
        self.phi = phi_val
        self.delta = delta
        self.entropy = entropy
        self.refs = refs
        self.owner = owner
        self.id = hashlib.sha256(f"{x}{phi_val}".encode()).hexdigest()[:8]
        self.locked = False
        self.value = 10
        self.spent = False  # NEW: prevent reuse
        self.provenance = []  # NEW: track history of transfers

    def __repr__(self):
        return f"<ψ-{self.id} | δ={self.delta:.4f} | H={self.entropy:.2f} | owner={self.owner} | value={self.value} | spent={self.spent}>"


wallet_balances = defaultdict(int)
total_supply = 0


class StructureContract:
    def __init__(self, name, delta_thresh, entropy_thresh, action,
                 priority=0, layer=0, depends_on: Optional[str] = None, ttl: int = -1):
        self.name = name
        self.delta_thresh = delta_thresh
        self.entropy_thresh = entropy_thresh
        self.action = action
        self.priority = priority
        self.layer = layer
        self.depends_on = depends_on
        self.ttl = ttl
        self.activation_count = 0

    def match(self, utxos: List[StructureUTXO]) -> bool:
        if len(utxos) < 2:
            return False
        avg_delta = sum(u.delta for u in utxos) / len(utxos)
        avg_entropy = sum(u.entropy for u in utxos) / len(utxos)
        return avg_delta < self.delta_thresh and avg_entropy > self.entropy_thresh

    def check(self, utxos: List[StructureUTXO]) -> (bool, str):
        if not self.match(utxos):
            return False, "ψ-path does not match avg(δ)/avg(H) condition"
        return True, "OK"

    def execute(self, utxos):
        time.sleep(0.01)
        passed, reason = self.check(utxos)
        if passed:
            self.activation_count += 1
            for u in utxos:
                u.locked = True
            return self.action(utxos)
        return f"Skipped: {reason}"


# --- Token Transfer Logic with UTXO spend and provenance ---
def transfer_action(utxos):
    sender_utxo = utxos[0]
    sender = sender_utxo.owner
    receiver = "b"
    value = sender_utxo.value

    if sender_utxo.spent:
        return f"Transfer failed: UTXO {sender_utxo.id} already spent"

    if wallet_balances[sender] >= value:
        wallet_balances[sender] -= value
        wallet_balances[receiver] += value
        sender_utxo.spent = True

        new_utxo = StructureUTXO(
            x=sender_utxo.x + 0.1,
            phi_val=sender_utxo.phi,
            delta=sender_utxo.delta,
            entropy=sender_utxo.entropy,
            refs=[sender_utxo.id],
            owner=receiver
        )
        new_utxo.provenance = sender_utxo.provenance + [sender_utxo.id]
        dag[new_utxo.id] = new_utxo

        return f"Transferred {value} from {sender} to {receiver}, created new UTXO {new_utxo.id}"
    else:
        return f"Transfer failed: insufficient balance in {sender}"


class StructureVM:
    def __init__(self):
        self.contracts: List[StructureContract] = []

    def add_contract(self, contract: StructureContract):
        self.contracts.append(contract)
        self.contracts.sort(key=lambda c: (-c.layer, -c.priority))

    def run(self, dag: Dict[str, StructureUTXO]):
        paths = self.find_paths(dag)
        for path in paths:
            for contract in self.contracts:
                result = contract.execute(path)
                print(f"[{contract.name}] {path} => {result}")

    def find_paths(self, dag):
        paths = []

        def dfs(current_path, visited):
            last = current_path[-1]
            paths.append(current_path[:])
            for utxo in dag.values():
                if utxo.id in visited:
                    continue
                if last.id in utxo.refs:
                    dfs(current_path + [utxo], visited | {utxo.id})

        for utxo in dag.values():
            if not utxo.refs:
                dfs([utxo], {utxo.id})

        return paths


# --- Test Wallet Transfer with Provenance ---
if __name__ == "__main__":
    contract = StructureContract(
        name="TokenTransfer",
        delta_thresh=0.35,
        entropy_thresh=0.65,
        action=transfer_action
    )

    vm = StructureVM()
    vm.add_contract(contract)

    dag = {}
    prev_id = None
    for i in range(5):
        delta = 0.2 - i * 0.01
        entropy = 0.8 + i * 0.02
        owner = "a" if i < 4 else "b"
        utxo = StructureUTXO(x=i, phi_val=0.5 - i * 0.01, delta=delta, entropy=entropy, refs=[prev_id] if prev_id else [], owner=owner)
        dag[utxo.id] = utxo
        prev_id = utxo.id
        wallet_balances[owner] += utxo.value
        total_supply += utxo.value

    print("Initial Balances:", dict(wallet_balances))
    print("Total Supply:", total_supply)
    vm.run(dag)
    print("Final Balances:", dict(wallet_balances))
    print("Total Supply (should remain constant):", sum(wallet_balances.values()))

    print("\n--- Provenance Trace ---")
    for utxo in dag.values():
        if utxo.owner == "b":
            print(f"UTXO {utxo.id} provenance: {utxo.provenance}")
