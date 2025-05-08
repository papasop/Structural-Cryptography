# Structure UTXO + SVM with Recursive Paths, Advanced Matching, and DAG Mutation

import math
import hashlib
from typing import List, Dict, Optional
from collections import defaultdict

# --- Structure UTXO Definition ---
class StructureUTXO:
    def __init__(self, x, phi_val, delta, entropy, refs):
        self.x = x
        self.phi = phi_val
        self.delta = delta
        self.entropy = entropy
        self.refs = refs
        self.id = hashlib.sha256(f"{x}{phi_val}".encode()).hexdigest()[:8]
        self.locked = False  # example DAG-mutated flag

    def __repr__(self):
        return f"<ψ-{self.id} | δ={self.delta:.4f} | H={self.entropy:.2f}>"


# --- Structure Contract with Pattern Matching and DAG Mutation ---
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
        head = utxos[0]
        tail = utxos[-1]
        return head.delta < self.delta_thresh and tail.entropy > self.entropy_thresh

    def check(self, utxos: List[StructureUTXO]) -> (bool, str):
        if not self.match(utxos):
            return False, "ψ-path does not match pattern"
        return True, "OK"

    def execute(self, utxos):
        passed, reason = self.check(utxos)
        if passed:
            self.activation_count += 1
            for u in utxos:
                u.locked = True  # example DAG mutation
            return self.action(utxos)
        return f"Skipped: {reason}"


# --- Structure Virtual Machine ---
class StructureVM:
    def __init__(self, dag: Dict[str, StructureUTXO]):
        self.dag = dag
        self.contracts: List[StructureContract] = []
        self.history = []
        self.reward_pool = 0
        self.events = []
        self.executed_contracts = set()
        self.round = 0

    def add_contract(self, contract: StructureContract):
        self.contracts.append(contract)
        self.contracts.sort(key=lambda c: (-c.layer, -c.priority))

    def run(self):
        results = []
        paths = self.find_paths()
        self.round += 1

        for path in paths:
            for contract in self.contracts:
                if contract.ttl != -1 and contract.activation_count >= contract.ttl:
                    self.events.append(f"[EXPIRED] Contract {contract.name} has reached TTL")
                    continue
                if contract.depends_on and contract.depends_on not in self.executed_contracts:
                    self.events.append(f"[WAIT] Contract {contract.name} waits on {contract.depends_on}")
                    continue
                result = contract.execute(path)
                self.history.append((contract.name, [u.id for u in path], result))
                if isinstance(result, str) and result.startswith("Reward"):
                    self.reward_pool += 10
                    self.events.append(f"[Layer {contract.layer}] Reward triggered by {[u.id for u in path]}")
                    self.executed_contracts.add(contract.name)
                elif isinstance(result, str) and result.startswith("Skipped"):
                    self.events.append(f"[Layer {contract.layer}] Contract skipped on {[u.id for u in path]} — {result}")
                else:
                    self.events.append(f"[Layer {contract.layer}] Executed {contract.name} on {[u.id for u in path]}")
                    self.executed_contracts.add(contract.name)
                results.append((contract.name, path, result))

        return results

    def find_paths(self):
        paths = []

        def dfs(current_path, visited):
            last = current_path[-1]
            paths.append(current_path[:])
            for utxo in self.dag.values():
                if utxo.id in visited:
                    continue
                if last.id in utxo.refs:
                    dfs(current_path + [utxo], visited | {utxo.id})

        for utxo in self.dag.values():
            if not utxo.refs:
                dfs([utxo], {utxo.id})

        return paths

    def print_history(self):
        print(f"\n--- Contract Execution History (Round {self.round}) ---")
        for record in self.history:
            print(f"[{record[0]}] Path: {record[1]} => Result: {record[2]}")
        print(f"Total Reward Pool: {self.reward_pool} tokens")

        print("\n--- Events ---")
        for event in self.events:
            print(event)


# --- Test Example ---
if __name__ == "__main__":
    utxo1 = StructureUTXO(x=1, phi_val=0.5, delta=0.2, entropy=0.95, refs=[])
    utxo2 = StructureUTXO(x=2, phi_val=0.3, delta=0.1, entropy=0.96, refs=[utxo1.id])
    utxo3 = StructureUTXO(x=3, phi_val=0.7, delta=0.4, entropy=0.97, refs=[utxo2.id])
    dag = {u.id: u for u in [utxo1, utxo2, utxo3]}

    def reward_action(utxos):
        return f"Reward granted to {[u.id for u in utxos]}"

    def audit_action(utxos):
        return f"Audit log created for {[u.id for u in utxos]}"

    reward_contract = StructureContract(
        name="ResonanceReward",
        delta_thresh=0.3,
        entropy_thresh=0.9,
        action=reward_action,
        priority=10,
        layer=1
    )

    audit_contract = StructureContract(
        name="ComplianceAudit",
        delta_thresh=0.4,
        entropy_thresh=0.6,
        action=audit_action,
        priority=5,
        layer=0,
        depends_on="ResonanceReward",
        ttl=3
    )

    vm = StructureVM(dag)
    vm.add_contract(reward_contract)
    vm.add_contract(audit_contract)
    vm.run()
    vm.print_history()
