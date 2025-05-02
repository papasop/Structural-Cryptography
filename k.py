# Re-imports after environment reset
import hashlib
import hmac
import math
import os
import random
from typing import List, Tuple
import matplotlib.pyplot as plt

# === Structure Function Utilities ===

def derive_parameters(seed: bytes) -> Tuple[List[float], List[float], List[float]]:
    key = b'structkey'
    raw = b''.join([hmac.new(key, seed + bytes([i]), hashlib.sha256).digest() for i in range(3)])
    floats = [float.fromhex(hex(int.from_bytes(raw[i:i+4], 'big'))) for i in range(0, 48, 4)]
    A = [1 + abs(floats[i]) % 2 for i in range(3)]
    t = [0.5 + abs(floats[i]) % 20 for i in range(3, 6)]
    theta = [abs(floats[i]) % (2 * math.pi) for i in range(6, 9)]
    return A, t, theta

def phi(x: int, A: List[float], t: List[float], theta: List[float]) -> float:
    return sum(A[i] * math.cos(t[i] * math.log(x + 1) + theta[i]) for i in range(3))

def structure_hash(message: bytes) -> int:
    return int.from_bytes(hashlib.sha256(message).digest(), 'big')

# === Signature Generation and Verification ===

def generate_signature(message: str, A: List[float], t: List[float], theta: List[float], D: int = 2**24) -> Tuple[str, float, int, float]:
    m_bytes = message.encode()
    xm = structure_hash(m_bytes) % D
    phi_xm = phi(xm, A, t, theta)
    challenge_xs = [101, 211, 307]
    phi_values = [phi(x, A, t, theta) for x in challenge_xs]
    tau = sorted(phi_values)[1]
    delta = abs(phi_xm - tau)
    data = f"{xm}|{phi_xm}|{delta}".encode()
    sig = hashlib.sha256(data).hexdigest()
    return sig, delta, xm, tau

def verify_signature(message: str, signature: str, A: List[float], t: List[float], theta: List[float], D: int = 2**24, alpha: float = 0.1) -> Tuple[bool, float]:
    m_bytes = message.encode()
    xm = structure_hash(m_bytes) % D
    phi_xm = phi(xm, A, t, theta)
    challenge_xs = [101, 211, 307]
    phi_values = [phi(x, A, t, theta) for x in challenge_xs]
    tau = sorted(phi_values)[1]
    sigma_phi = math.sqrt(sum((v - tau)**2 for v in phi_values) / 3)
    epsilon = alpha * sigma_phi
    delta = abs(phi_xm - tau)
    data = f"{xm}|{phi_xm}|{delta}".encode()
    expected_sig = hashlib.sha256(data).hexdigest()
    return (delta < epsilon and expected_sig == signature), delta

# === Combined Test Runner ===

def run_combined_test(message: str, trials: int = 50):
    D = 2**24
    alpha = 0.1
    fixed_seed = b'\x01' * 16
    A_fixed, t_fixed, theta_fixed = derive_parameters(fixed_seed)
    sig_fixed, delta_fixed, xm_fixed, tau_fixed = generate_signature(message, A_fixed, t_fixed, theta_fixed)
    valid_fixed, _ = verify_signature(message, sig_fixed, A_fixed, t_fixed, theta_fixed)

    print("=== Fixed Seed Signature ===")
    print(f"Delta: {delta_fixed:.6f}")
    print(f"Signature: {sig_fixed}")
    print(f"Verification: {'VALID ✅' if valid_fixed else 'INVALID ❌'}")

    deltas_random = []
    best_delta = float("inf")
    best_result = {}

    for i in range(trials):
        seed = os.urandom(16)
        A, t, theta = derive_parameters(seed)
        sig, delta, xm, tau = generate_signature(message, A, t, theta)
        deltas_random.append(delta)
        if delta < best_delta:
            best_delta = delta
            best_result = {"seed": seed.hex(), "delta": delta, "signature": sig, "A": A, "t": t, "theta": theta}

    valid_best, _ = verify_signature(message, best_result["signature"], best_result["A"], best_result["t"], best_result["theta"])

    print("\n=== Best Random Signature (out of 50) ===")
    print(f"Delta: {best_result['delta']:.6f}")
    print(f"Signature: {best_result['signature']}")
    print(f"Verification: {'VALID ✅' if valid_best else 'INVALID ❌'}")

    # Plotting
    plt.figure(figsize=(10, 5))
    plt.plot(range(trials), deltas_random, marker='o', label="Random Seeds")
    plt.axhline(delta_fixed, color='green', linestyle='--', label='Fixed Seed Delta')
    plt.axhline(0.2, color='red', linestyle=':', label='ε = 0.2')
    plt.title("Delta Values Across Random Seeds vs Fixed Seed")
    plt.xlabel("Trial")
    plt.ylabel("Delta")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("combined_signature_test.png")

    return sig_fixed, delta_fixed, best_result

# Run the test
run_combined_test("Test 123")
