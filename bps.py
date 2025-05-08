# Structure UTXO + SVM with Convergence Speed Metrics and Block Time

import math
import hashlib
import time
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
        self.locked = False

    def __repr__(self):
        return f"<ψ-{self.id} | δ={self.delta:.4f} | H={self.entropy:.2f}>"


# --- Structure Contract ---
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
        passed, reason = self.check(utxos)
        if passed:
            self.activation_count += 1
            for u in utxos:
                u.locked = True
            return self.action(utxos)
        return f"Skipped: {reason}"


# --- Structure Virtual Machine ---
class StructureVM:
    def __init__(self):
        self.contracts: List[StructureContract] = []
        self.history = []
        self.reward_pool = 0
        self.events = []
        self.executed_contracts = set()
        self.first_trigger_rounds = []
        self.block_times = []

    def add_contract(self, contract: StructureContract):
        self.contracts.append(contract)
        self.contracts.sort(key=lambda c: (-c.layer, -c.priority))

    def run(self, dag: Dict[str, StructureUTXO], round_number: int):
        results = []
        paths = self.find_paths(dag)
        first_trigger_round = None
        round_start_time = time.time()

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
                    self.executed_contracts.add(contract.name)
                    if first_trigger_round is None:
                        first_trigger_round = round_number
                        block_time = time.time() - round_start_time
                        self.block_times.append(block_time)
                    self.events.append(f"[Layer {contract.layer}] Reward triggered by {[u.id for u in path]}")
                elif isinstance(result, str) and result.startswith("Skipped"):
                    self.events.append(f"[Layer {contract.layer}] Contract skipped on {[u.id for u in path]} — {result}")
                else:
                    self.executed_contracts.add(contract.name)
                    self.events.append(f"[Layer {contract.layer}] Executed {contract.name} on {[u.id for u in path]}")
                results.append((contract.name, path, result))

        self.first_trigger_rounds.append(first_trigger_round or -1)
        return results

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

    def print_summary(self):
        print("\n--- Convergence Summary ---")
        valid_rounds = [r for r in self.first_trigger_rounds if r != -1]
        if valid_rounds:
            avg = sum(valid_rounds) / len(valid_rounds)
            print(f"Average convergence round over {len(valid_rounds)} runs: {avg:.2f}")
        else:
            print("No convergence occurred in any round.")
        print(f"Total Reward Pool: {self.reward_pool} tokens")

        if self.block_times:
            avg_block_time = sum(self.block_times) / len(self.block_times)
            print(f"Average BLOCK PER SPEED: {avg_block_time:.4f} seconds")


# --- Test Multiple Runs ---
if __name__ == "__main__":
    def reward_action(utxos):
        return f"Reward granted to {[u.id for u in utxos]}"

    contract = StructureContract(
        name="ConvergenceReward",
        delta_thresh=0.35,
        entropy_thresh=0.65,
        action=reward_action,
        priority=10,
        layer=1
    )

    vm = StructureVM()
    vm.add_contract(contract)

    for round_num in range(10):
        base_delta = 0.5
        base_entropy = 0.3
        dag = {}
        prev_id = None
        for i in range(10):
            delta = base_delta - i * 0.05 + (round_num * 0.01)
            entropy = base_entropy + i * 0.12
            utxo = StructureUTXO(x=i, phi_val=0.5 - i * 0.01, delta=delta, entropy=entropy, refs=[prev_id] if prev_id else [])
            dag[utxo.id] = utxo
            prev_id = utxo.id
        vm.run(dag, round_num + 1)

    vm.print_summary()
