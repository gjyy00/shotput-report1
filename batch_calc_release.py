
import os
import math
import sys

# 引入 process_data.py 中的函数
# 由于 process_data.py 是直接执行的脚本，我们这里简单复制需要的逻辑，或者尝试 import
# 考虑到依赖关系，我将直接复制核心逻辑到这个脚本中，以确保独立运行

# === 复制自 process_data.py 的配置 ===
# 右手食指基部数据 (更接近铁饼释放点)
COL_HAND_R_X = 409
COL_HAND_R_Y = 410
COL_HAND_R_Z = 411
COL_HAND_R_VX = 413
COL_HAND_R_VY = 414
COL_HAND_R_VZ = 415
COL_HAND_R_V = 416

# 骨架关节点 (用于铅球优化)
SKELETON_JOINTS = {
    'shoulder_r': 121,
    'elbow_r': 133,
    'wrist_r': 145,
}

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

def extract_skeleton_frames(data):
    """提取简单的骨架帧数据(仅用于计算角度)"""
    frames = []
    for row in data:
        frame = {}
        for name, idx in SKELETON_JOINTS.items():
            try:
                frame[name] = [row[idx], row[idx+1], row[idx+2]]
            except IndexError:
                pass
        frames.append(frame)
    return frames

def calculate_angle(p1, p2, p3):
    """计算三点角度"""
    v1 = [p1[0]-p2[0], p1[1]-p2[1], p1[2]-p2[2]]
    v2 = [p3[0]-p2[0], p3[1]-p2[1], p3[2]-p2[2]]
    
    dot = v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
    norm1 = math.sqrt(sum(x*x for x in v1))
    norm2 = math.sqrt(sum(x*x for x in v2))
    
    if norm1 == 0 or norm2 == 0: return 0
    
    cos_angle = dot / (norm1 * norm2)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.degrees(math.acos(cos_angle))

def find_release_point_v2(data):
    """
    使用优化后的逻辑寻找释放点
    """
    speeds = [row[COL_HAND_R_V] for row in data]
    positions = [[row[COL_HAND_R_X], row[COL_HAND_R_Y], row[COL_HAND_R_Z]] for row in data]
    times = [row[COL_TIME] for row in data]
    frames = extract_skeleton_frames(data)
    
    n = len(speeds)
    skip_start = max(5, int(n * 0.10))
    search_end = n - max(3, int(n * 0.02))
    
    # 找全局最大速度
    global_max_speed = 0
    for i in range(skip_start, search_end):
        if speeds[i] > global_max_speed:
            global_max_speed = speeds[i]
            
    is_shot_put = global_max_speed < 18.0
    
    release_idx = -1
    
    # 铅球逻辑
    if is_shot_put:
        candidates = []
        for i in range(skip_start, search_end):
            frame = frames[i]
            # 获取速度向量
            vx = data[i][COL_HAND_R_VX]
            vy = data[i][COL_HAND_R_VY]
            vz = data[i][COL_HAND_R_VZ]
            
            if 'shoulder_r' in frame and 'elbow_r' in frame and 'wrist_r' in frame:
                angle = calculate_angle(frame['shoulder_r'], frame['elbow_r'], frame['wrist_r'])
                height = positions[i][2]
                speed = speeds[i]
                
                # 增加条件：垂直速度 vz > 0 (确保出手角度为正)
                if height > 1.6 and angle > 130 and vz > 0:
                    candidates.append({
                        'idx': i,
                        'speed': speed,
                        'height': height,
                        'angle': angle
                    })
        
        if candidates:
            best = max(candidates, key=lambda x: x['speed'])
            release_idx = best['idx']
    
    # 如果没找到或者不是铅球，用通用逻辑
    if release_idx == -1:
        # 简单平滑
        smoothed = []
        for i in range(n):
            s = 0
            c = 0
            for j in range(max(0, i-2), min(n, i+3)):
                s += speeds[j]
                c += 1
            smoothed.append(s/c)
            
        min_h = 1.6 if is_shot_put else 1.2
        peaks = []
        
        for i in range(skip_start+1, search_end-1):
            if smoothed[i] > smoothed[i-1] and smoothed[i] >= smoothed[i+1]:
                if positions[i][2] > min_h:
                    peaks.append({'idx': i, 'speed': speeds[i], 'smooth': smoothed[i]})
        
        # 筛选
        min_peak = global_max_speed * 0.4
        for p in peaks:
            if p['speed'] < min_peak: continue
            
            # 检查下降
            min_after = p['speed']
            for j in range(p['idx']+1, min(p['idx']+10, search_end)):
                if smoothed[j] < min_after: min_after = smoothed[j]
            
            drop = (p['speed'] - min_after) / p['speed']
            if drop > 0.05:
                release_idx = p['idx']
                break
                
    # 保底
    if release_idx == -1:
        max_v = -1
        best_i = -1
        min_h = 1.6 if is_shot_put else 1.2
        for i in range(skip_start, search_end):
            if positions[i][2] > min_h and speeds[i] > max_v:
                max_v = speeds[i]
                best_i = i
        if best_i != -1:
            release_idx = best_i
        else:
            # 绝对保底
            max_v = -1
            for i in range(skip_start, search_end):
                if speeds[i] > max_v:
                    max_v = speeds[i]
                    release_idx = i

    # 计算三要素
    r_pos = positions[release_idx]
    r_vel = [data[release_idx][COL_HAND_R_VX], data[release_idx][COL_HAND_R_VY], data[release_idx][COL_HAND_R_VZ]]
    
    # 速度
    v_val = math.sqrt(r_vel[0]**2 + r_vel[1]**2 + r_vel[2]**2)
    
    # 角度
    v_horiz = math.sqrt(r_vel[0]**2 + r_vel[1]**2)
    angle_val = math.degrees(math.atan2(r_vel[2], v_horiz)) if v_horiz > 0 else 0
    
    # 高度
    h_val = r_pos[2]
    
    return {
        'time': times[release_idx],
        'height': h_val,
        'speed': v_val,
        'angle': angle_val
    }

def main():
    files = ['1.txt', '2.txt', '3.txt', '4.txt']
    base_dir = '/Users/jiahongxiang/shotput_report_demo'
    
    print(f"{'File':<10} | {'Time (s)':<10} | {'Height (m)':<10} | {'Speed (m/s)':<12} | {'Angle (deg)':<10}")
    print("-" * 65)
    
    for fname in files:
        fpath = os.path.join(base_dir, fname)
        data = load_data(fpath)
        if not data:
            print(f"{fname:<10} | {'Error':<10}")
            continue
            
        res = find_release_point_v2(data)
        
        print(f"{fname:<10} | {res['time']:<10.3f} | {res['height']:<10.2f} | {res['speed']:<12.2f} | {res['angle']:<10.1f}")

if __name__ == '__main__':
    main()
