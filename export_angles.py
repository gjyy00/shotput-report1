
import os
import math
import sys
import json

# 关节点列索引
SKELETON_JOINTS = {
    'shoulder_r': 121,
    'elbow_r': 133,
    'wrist_r': 145,
    'hip_r': 25,
    'knee_r': 37,
    'ankle_r': 49,
    'shoulder_l': 157,
    'elbow_l': 169,
    'wrist_l': 181,
    'hip_l': 61,
    'knee_l': 73,
    'ankle_l': 85,
    'torso': 109,
    'neck': 193
}

COL_TIME = 0

def load_data(filepath):
    data = []
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return []
        
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[2:]:
            parts = line.strip().split('\t')
            if len(parts) > 200:
                try:
                    values = [float(x) if x else 0.0 for x in parts]
                    if values[0] > 0:
                        data.append(values)
                except ValueError:
                    continue
    return data

def calculate_angle_3d(p1, p2, p3):
    """计算三点角度 p1-p2-p3, p2为顶点"""
    v1 = [p1[0]-p2[0], p1[1]-p2[1], p1[2]-p2[2]]
    v2 = [p3[0]-p2[0], p3[1]-p2[1], p3[2]-p2[2]]
    
    dot = v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
    norm1 = math.sqrt(sum(x*x for x in v1))
    norm2 = math.sqrt(sum(x*x for x in v2))
    
    if norm1 == 0 or norm2 == 0: return 0
    
    cos_angle = dot / (norm1 * norm2)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.degrees(math.acos(cos_angle))

def extract_angles(data):
    times = []
    elbow_r = []
    knee_r = []
    knee_l = []
    shoulder_r = []
    trunk_inc = []
    hip_shoulder = []
    
    for row in data:
        t = row[COL_TIME]
        times.append(t)
        
        # Helper to get point
        def get_p(name):
            idx = SKELETON_JOINTS[name]
            return [row[idx], row[idx+1], row[idx+2]]
            
        # Right Elbow (Shoulder-Elbow-Wrist)
        try:
            angle = calculate_angle_3d(get_p('shoulder_r'), get_p('elbow_r'), get_p('wrist_r'))
            elbow_r.append(angle)
        except:
            elbow_r.append(0)
            
        # Right Knee (Hip-Knee-Ankle)
        try:
            angle = calculate_angle_3d(get_p('hip_r'), get_p('knee_r'), get_p('ankle_r'))
            knee_r.append(angle)
        except:
            knee_r.append(0)
            
        # Left Knee (Hip-Knee-Ankle)
        try:
            angle = calculate_angle_3d(get_p('hip_l'), get_p('knee_l'), get_p('ankle_l'))
            knee_l.append(angle)
        except:
            knee_l.append(0)
            
        # Right Shoulder (Torso-Shoulder-Elbow) - 这里的定义可能需要根据实际需求调整，暂时用这个链
        try:
            angle = calculate_angle_3d(get_p('torso'), get_p('shoulder_r'), get_p('elbow_r'))
            shoulder_r.append(angle)
        except:
            shoulder_r.append(0)

        # Trunk Inclination (MidHip-Neck vs Vertical Z)
        try:
            hip_r = get_p('hip_r')
            hip_l = get_p('hip_l')
            neck = get_p('neck')
            mid_hip = [(hip_r[0]+hip_l[0])/2, (hip_r[1]+hip_l[1])/2, (hip_r[2]+hip_l[2])/2]
            
            # Vector from MidHip to Neck
            trunk_vec = [neck[0]-mid_hip[0], neck[1]-mid_hip[1], neck[2]-mid_hip[2]]
            
            # Angle with vertical (0,0,1)
            # dot product is just trunk_vec[2]
            norm = math.sqrt(sum(x*x for x in trunk_vec))
            if norm > 0:
                cos_a = trunk_vec[2] / norm
                cos_a = max(-1.0, min(1.0, cos_a))
                trunk_angle = math.degrees(math.acos(cos_a))
            else:
                trunk_angle = 0
            trunk_inc.append(trunk_angle)
        except:
            trunk_inc.append(0)

        # Hip-Shoulder Separation
        try:
            # 投影到 XY 平面 (忽略 Z)
            hr = get_p('hip_r'); hl = get_p('hip_l')
            sr = get_p('shoulder_r'); sl = get_p('shoulder_l')
            
            # 髋向量 (左->右)
            hip_vec = [hr[0]-hl[0], hr[1]-hl[1]]
            # 肩向量 (左->右)
            sh_vec = [sr[0]-sl[0], sr[1]-sl[1]]
            
            # 计算二维向量夹角
            norm_h = math.sqrt(hip_vec[0]**2 + hip_vec[1]**2)
            norm_s = math.sqrt(sh_vec[0]**2 + sh_vec[1]**2)
            
            if norm_h > 0 and norm_s > 0:
                dot = hip_vec[0]*sh_vec[0] + hip_vec[1]*sh_vec[1]
                cos_a = dot / (norm_h * norm_s)
                cos_a = max(-1.0, min(1.0, cos_a))
                sep_angle = math.degrees(math.acos(cos_a))
            else:
                sep_angle = 0
            hip_shoulder.append(sep_angle)
        except:
            hip_shoulder.append(0)

    # 计算球速 (右手腕/手部速度)
    ball_speed = []
    COL_HAND_R_V = 416 # V
    
    for row in data:
        try:
            # 优先使用手部速度，如果没有则使用手腕速度
            speed = row[COL_HAND_R_V] if len(row) > 416 else 0
            if speed == 0 and len(row) > 152:
                speed = row[152] # Wrist V
            ball_speed.append(speed)
        except:
            ball_speed.append(0)
            
    return {
        'times': times,
        'elbow_r': elbow_r,
        'knee_r': knee_r,
        'knee_l': knee_l,
        'shoulder_r': shoulder_r,
        'ball_speed': ball_speed,
        'trunk_inc': trunk_inc,
        'hip_shoulder': hip_shoulder
    }

def process_file(filepath, label):
    data = load_data(filepath)
    if not data: return None
    
    angles = extract_angles(data)
    
    # 降采样以减少数据量 (约500点)
    step = max(1, len(angles['times']) // 500)
    
    return {
        'label': label,
        'times': angles['times'][::step],
        'elbow_r': angles['elbow_r'][::step],
        'knee_r': angles['knee_r'][::step],
        'knee_l': angles['knee_l'][::step],
        'shoulder_r': angles['shoulder_r'][::step],
        'ball_speed': angles['ball_speed'][::step],
        'trunk_inc': angles['trunk_inc'][::step],
        'hip_shoulder': angles['hip_shoulder'][::step]
    }

def main():
    files = [
        ('/Users/jiahongxiang/shotput_report_demo/2.txt', 'No.2'),
        ('/Users/jiahongxiang/shotput_report_demo/3.txt', 'No.3'),
        ('/Users/jiahongxiang/shotput_report_demo/4.txt', 'No.4')
    ]
    
    results = []
    for fpath, label in files:
        res = process_file(fpath, label)
        if res:
            results.append(res)
            
    # 输出为 JSON 格式供前端使用
    print("const angleData = " + json.dumps(results) + ";")

if __name__ == '__main__':
    main()
