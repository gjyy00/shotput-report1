
import math
import os

# 列索引定义 (基于 process_data.py)
# 右手食指基部 (速度参考)
COL_HAND_R_V = 416

# 关节坐标索引
# shoulder_r: 121
COL_SHOULDER_R_X = 121
COL_SHOULDER_R_Y = 122
COL_SHOULDER_R_Z = 123

# elbow_r: 133
COL_ELBOW_R_X = 133
COL_ELBOW_R_Y = 134
COL_ELBOW_R_Z = 135

# wrist_r: 145
COL_WRIST_R_X = 145
COL_WRIST_R_Y = 146
COL_WRIST_R_Z = 147

# hand_index_r: 409 (作为铁饼/铅球位置)
COL_HAND_R_X = 409
COL_HAND_R_Y = 410
COL_HAND_R_Z = 411

def calculate_angle(p1, p2, p3):
    """
    计算三点形成的角度 (p1-p2-p3)，p2为顶点
    返回角度（度），180度表示完全伸直
    """
    # 向量 v1: p2 -> p1 (大臂，指向肩)
    v1 = [p1[0]-p2[0], p1[1]-p2[1], p1[2]-p2[2]]
    # 向量 v2: p2 -> p3 (小臂，指向腕)
    v2 = [p3[0]-p2[0], p3[1]-p2[1], p3[2]-p2[2]]
    
    # 计算点积
    dot_product = v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
    
    # 计算模长
    norm1 = math.sqrt(v1[0]**2 + v1[1]**2 + v1[2]**2)
    norm2 = math.sqrt(v2[0]**2 + v2[1]**2 + v2[2]**2)
    
    if norm1 == 0 or norm2 == 0:
        return 0
    
    # 计算夹角余弦
    cos_angle = dot_product / (norm1 * norm2)
    # 限制范围 [-1, 1] 避免计算误差导致越界
    cos_angle = max(-1.0, min(1.0, cos_angle))
    
    # 计算弧度
    rad = math.acos(cos_angle)
    
    # 这里的角度是 p1-p2 和 p2-p3 的夹角。
    # 如果手臂伸直，shoulder->elbow 和 elbow->wrist 是同向的。
    # 但是我们构造的向量是 p2->p1 (elbow->shoulder) 和 p2->p3 (elbow->wrist)。
    # 如果伸直，这两个向量方向相反，夹角应该是 180度。
    # 如果完全折叠，这两个向量方向相同，夹角是 0度。
    # 所以直接返回这个角度即可表示“伸直程度”，越接近180度越伸直。
    
    return math.degrees(rad)

def analyze_shot_put():
    filepath = '1.txt'
    if not os.path.exists(filepath):
        print(f"File {filepath} not found.")
        return

    print(f"Analyzing {filepath}...")
    
    data_points = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # 跳过头部
        for i, line in enumerate(lines[2:], start=2):
            parts = line.strip().split('\t')
            if len(parts) > 420:
                try:
                    vals = [float(x) if x else 0.0 for x in parts]
                    if vals[0] <= 0: continue
                    
                    # 提取关节点
                    shoulder = [vals[COL_SHOULDER_R_X], vals[COL_SHOULDER_R_Y], vals[COL_SHOULDER_R_Z]]
                    elbow = [vals[COL_ELBOW_R_X], vals[COL_ELBOW_R_Y], vals[COL_ELBOW_R_Z]]
                    wrist = [vals[COL_WRIST_R_X], vals[COL_WRIST_R_Y], vals[COL_WRIST_R_Z]]
                    
                    # 提取手部位置和速度
                    hand_pos = [vals[COL_HAND_R_X], vals[COL_HAND_R_Y], vals[COL_HAND_R_Z]]
                    speed = vals[COL_HAND_R_V]
                    
                    # 计算肘关节角度
                    angle = calculate_angle(shoulder, elbow, wrist)
                    
                    data_points.append({
                        'frame': i,
                        'time': vals[0],
                        'speed': speed,
                        'height': hand_pos[2],
                        'angle': angle
                    })
                except ValueError:
                    continue

    # 找出最大速度点
    max_speed_point = max(data_points, key=lambda x: x['speed'])
    print(f"Global Max Speed: Frame {max_speed_point['frame']}, Time {max_speed_point['time']:.3f}, Speed {max_speed_point['speed']:.2f} m/s, Height {max_speed_point['height']:.2f} m, Angle {max_speed_point['angle']:.1f}°")

    # 打印 Frame 300-360 的数据
    print("\nData around Frame 300-360:")
    print("Frame | Time  | Speed | Height | Angle ")
    print("-" * 60)
    
    for p in data_points:
        if 300 <= p['frame'] <= 360:
            print(f"{p['frame']:5d} | {p['time']:.3f} | {p['speed']:5.2f} | {p['height']:6.2f} | {p['angle']:5.1f}")

    # 尝试寻找新的最佳释放点
    # 规则：速度较大（例如 > 80% Max），且角度最大（最接近伸直）
    # 或者：在满足角度 > 150度的情况下，找速度最大的点
    
    print("\nSearching for optimized release point (Angle > 140°)...")
    valid_points = [p for p in data_points if p['angle'] > 140 and p['height'] > 1.6]
    
    if valid_points:
        # 在伸直的阶段找速度最大的
        best_release = max(valid_points, key=lambda x: x['speed'])
        print(f"Optimized Release: Frame {best_release['frame']}, Time {best_release['time']:.3f}, Speed {best_release['speed']:.2f}, Height {best_release['height']:.2f}, Angle {best_release['angle']:.1f}°")
        
        # 对比一下之前的检测结果（假设之前检测的是最大速度点或者早于它）
        if best_release['frame'] > max_speed_point['frame']:
             print("Result: Optimized point is LATER than max speed point.")
        elif best_release['frame'] < max_speed_point['frame']:
             print("Result: Optimized point is EARLIER than max speed point.")
        else:
             print("Result: Same as max speed point.")
    else:
        print("No points found with Angle > 140° and Height > 1.6m")

if __name__ == "__main__":
    analyze_shot_put()
