import os
import math
import sys

# 右手食指基部数据
COL_HAND_R_X = 409
COL_HAND_R_Y = 410
COL_HAND_R_Z = 411
COL_HAND_R_VX = 413
COL_HAND_R_VY = 414
COL_HAND_R_VZ = 415
COL_HAND_R_V = 416
COL_TIME = 0

def load_data(filepath):
    """加载数据"""
    data = []
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return []
        
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[2:]:
            parts = line.strip().split('\t')
            if len(parts) > 420:
                try:
                    values = [float(x) if x else 0.0 for x in parts]
                    if values[0] > 0:
                        data.append(values)
                except ValueError:
                    continue
    return data

def get_biomechanics_at_time(data, target_time):
    """获取指定时间点的生物力学指标"""
    # 找到最接近的时间点
    best_idx = -1
    min_diff = float('inf')
    
    for i, row in enumerate(data):
        diff = abs(row[COL_TIME] - target_time)
        if diff < min_diff:
            min_diff = diff
            best_idx = i
            
    if best_idx == -1:
        return None
        
    row = data[best_idx]
    actual_time = row[COL_TIME]
    
    # 位置
    x = row[COL_HAND_R_X]
    y = row[COL_HAND_R_Y]
    z = row[COL_HAND_R_Z]
    
    # 速度向量
    vx = row[COL_HAND_R_VX]
    vy = row[COL_HAND_R_VY]
    vz = row[COL_HAND_R_VZ]
    
    # 计算指标
    # 1. 速度 (m/s)
    speed = math.sqrt(vx**2 + vy**2 + vz**2)
    
    # 2. 高度 (m)
    height = z
    
    # 3. 角度 (度)
    v_horiz = math.sqrt(vx**2 + vy**2)
    angle = math.degrees(math.atan2(vz, v_horiz)) if v_horiz > 0 else 0
    
    # 4. 预估距离 (抛体公式)
    # R = (v² * cosθ / g) * [sinθ + √(sin²θ + 2gh/v²)]
    g = 9.81
    dist = 0
    if speed > 0 and angle > 0:  # 只有角度为正才能计算抛体距离
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        
        term1 = (speed**2 * cos_a) / g
        term2 = sin_a + math.sqrt(sin_a**2 + 2 * g * height / speed**2)
        dist = term1 * term2
    
    return {
        'target_time': target_time,
        'actual_time': actual_time,
        'diff': min_diff,
        'height': height,
        'speed': speed,
        'angle': angle,
        'distance': dist
    }

def main():
    base_dir = '/Users/jiahongxiang/shotput_report_demo'
    
    tasks = [
        {'file': '2.txt', 'time': 2.28},
        {'file': '3.txt', 'time': 3.11},
        {'file': '4.txt', 'time': 2.92}
    ]
    
    print(f"{'File':<10} | {'Target (s)':<10} | {'Actual (s)':<10} | {'Height (m)':<10} | {'Speed (m/s)':<12} | {'Angle (deg)':<12} | {'Est. Dist (m)':<12}")
    print("-" * 90)
    
    for task in tasks:
        fname = task['file']
        target_t = task['time']
        fpath = os.path.join(base_dir, fname)
        
        data = load_data(fpath)
        if not data:
            print(f"{fname:<10} | {'Error':<10}")
            continue
            
        res = get_biomechanics_at_time(data, target_t)
        
        if res:
            dist_str = f"{res['distance']:.2f}" if res['distance'] > 0 else "N/A"
            print(f"{fname:<10} | {res['target_time']:<10.3f} | {res['actual_time']:<10.3f} | {res['height']:<10.2f} | {res['speed']:<12.2f} | {res['angle']:<12.1f} | {dist_str:<12}")

if __name__ == '__main__':
    main()
