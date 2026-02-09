
import math

def calculate_distance(height, speed, angle):
    g = 9.81
    rad = math.radians(angle)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    
    term1 = (speed**2 * cos_a) / g
    term2 = sin_a + math.sqrt(sin_a**2 + 2 * g * height / speed**2)
    dist = term1 * term2
    return dist

# 基础参数
h = 2.14
v = 12.8
base_angle = 30.7

print(f"Base Parameters: H={h}m, V={v}m/s")
print("-" * 35)
print(f"{'Angle':<10} | {'Dist (m)':<10} | {'Diff (m)':<10}")
print("-" * 35)

# 计算三个角度
angles = [base_angle - 5, base_angle, base_angle + 5]
base_dist = calculate_distance(h, v, base_angle)

for a in angles:
    d = calculate_distance(h, v, a)
    diff = d - base_dist
    diff_str = f"{diff:+.2f}" if abs(diff) > 0.001 else "-"
    print(f"{a:<10.1f} | {d:<10.2f} | {diff_str:<10}")
