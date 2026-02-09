
const fs = require('fs');
const path = require('path');

// 模拟 index.html 中的 findReleasePoint 函数 (更新后的版本)
function findReleasePoint(discusDataLocal) {
    const speeds = discusDataLocal.speeds;
    const positions = discusDataLocal.positions;
    const velocities = discusDataLocal.velocities;
    const times = discusDataLocal.times;
    const n = speeds.length;
    
    // 跳过开头的边界伪影帧
    const skipStart = Math.max(5, Math.floor(n * 0.10));
    const skipEnd = Math.max(3, Math.floor(n * 0.02));
    const searchEnd = n - skipEnd;

    // 在有效范围内找全局最大速度（用于阈值参考）
    let globalMaxSpeed = 0;
    for (let i = skipStart; i < searchEnd; i++) {
        if (speeds[i] > globalMaxSpeed) globalMaxSpeed = speeds[i];
    }
    
    // 智能判断项目类型：铅球速度通常 < 16m/s，铁饼通常 > 20m/s
    // 如果最大速度小于 18m/s，倾向于是铅球，要求更高的出手高度
    const isShotPut = globalMaxSpeed < 18.0;
    const MIN_RELEASE_HEIGHT = isShotPut ? 1.6 : 1.2;
    
    console.log(`项目类型推断: ${isShotPut ? '铅球(Shot Put)' : '铁饼(Discus)'}, 最大速度=${globalMaxSpeed.toFixed(2)}m/s, 最小高度阈值=${MIN_RELEASE_HEIGHT}m`);
    
    // ====== 核心策略：找第一个显著速度局部峰值 ======
    // 投掷项目中，器械出手时手速达到局部峰值，之后短暂下降（失去负载），
    // 然后空手随动阶段手速可能再次上升。第一个峰值才是真正的出手点。
    
    // 先做简单平滑（5帧窗口），避免噪声干扰
    const smoothed = [];
    const halfWin = 2;
    for (let i = 0; i < n; i++) {
        let sum = 0, cnt = 0;
        for (let j = Math.max(0, i - halfWin); j <= Math.min(n - 1, i + halfWin); j++) {
            sum += speeds[j]; cnt++;
        }
        smoothed.push(sum / cnt);
    }
    
    // 找所有局部速度峰值（平滑后）
    const peaks = [];
    for (let i = skipStart + 1; i < searchEnd - 1; i++) {
        // 必须是局部峰值
        if (smoothed[i] > smoothed[i - 1] && smoothed[i] >= smoothed[i + 1]) {
            // 增加高度过滤：只有高度足够才可能是释放点
            if (positions[i][2] > MIN_RELEASE_HEIGHT) {
                peaks.push({ idx: i, speed: speeds[i], smoothedSpeed: smoothed[i], height: positions[i][2] });
            }
        }
    }
    
    // 找第一个"显著"峰值：速度 >= 全局最大的40%，且之后有明显下降（至少10%）
    let releaseIdx = -1;
    const minPeakSpeed = globalMaxSpeed * 0.40;
    
    for (const peak of peaks) {
        if (peak.speed < minPeakSpeed) continue;
        
        // 检查峰值后是否有明显下降（在接下来10帧内速度下降至少10%）
        const lookAhead = Math.min(peak.idx + 10, searchEnd);
        let minAfter = peak.speed;
        for (let j = peak.idx + 1; j < lookAhead; j++) {
            if (smoothed[j] < minAfter) minAfter = smoothed[j];
        }
        
        const dropRatio = (peak.speed - minAfter) / peak.speed;
        // 对于铅球，速度下降可能不如铁饼剧烈，适当降低阈值到 5%
        if (dropRatio > 0.05) { 
            releaseIdx = peak.idx;
            console.log(`释放点检测(局部峰值法): 帧${peak.idx}, 速度=${peak.speed.toFixed(2)}m/s, 高度=${peak.height.toFixed(2)}m, 峰后下降${(dropRatio*100).toFixed(1)}%`);
            break;
        }
    }
    
    // 如果没找到合适的局部峰值，回退策略：
    // 在高度满足条件的点中，找速度最大的点
    if (releaseIdx === -1) {
        let bestIdx = -1;
        let maxVal = -1;
        
        for (let i = skipStart; i < searchEnd; i++) {
            if (positions[i][2] > MIN_RELEASE_HEIGHT) {
                if (speeds[i] > maxVal) {
                    maxVal = speeds[i];
                    bestIdx = i;
                }
            }
        }
        
        if (bestIdx !== -1) {
            releaseIdx = bestIdx;
            console.log(`释放点检测(高位最大速度法): 帧${bestIdx}, 速度=${maxVal.toFixed(2)}m/s`);
        } else {
            // 实在找不到高位点，只能回退到全局最大速度
            let maxSpeedIdx = skipStart;
            for (let i = skipStart; i < searchEnd; i++) {
                if (speeds[i] > speeds[maxSpeedIdx]) maxSpeedIdx = i;
            }
            releaseIdx = maxSpeedIdx;
            console.log(`释放点检测(保底全局最大): 帧${releaseIdx}, 高度=${positions[releaseIdx][2].toFixed(2)}m (未满足高度阈值)`);
        }
        
        // 尝试从选定点微调：寻找真正的速度峰值（在选定点附近）
        // 有时候最大速度点可能稍微偏一点
        const range = 5;
        let refinedIdx = releaseIdx;
        let currentMaxSpeed = speeds[releaseIdx];
        
        for (let i = Math.max(skipStart, releaseIdx - range); i <= Math.min(searchEnd, releaseIdx + range); i++) {
            // 微调时也要遵守高度限制，或者至少不能比原点低太多（例如允许降低 0.1m）
            if (speeds[i] > currentMaxSpeed && positions[i][2] > MIN_RELEASE_HEIGHT - 0.1) {
                refinedIdx = i;
                currentMaxSpeed = speeds[i];
            }
        }
        releaseIdx = refinedIdx;
    }
    
    // 计算出手角度供日志输出
    let angle = 0;
    if (velocities && releaseIdx < velocities.length) {
        const vel = velocities[releaseIdx];
        const hv = Math.sqrt(vel[0]**2 + vel[1]**2);
        angle = hv > 0 ? Math.atan2(vel[2], hv) * 180 / Math.PI : 0;
    }
    
    console.log(`释放点最终: 帧=${releaseIdx}, t=${times[releaseIdx].toFixed(3)}s, 速度=${speeds[releaseIdx].toFixed(2)}m/s, 高度=${positions[releaseIdx][2].toFixed(3)}m, 角度=${angle.toFixed(1)}°`);
    
    return {
        index: releaseIdx,
        position: positions[releaseIdx],
        speed: speeds[releaseIdx],
        time: times[releaseIdx]
    };
}

// 读取数据文件
const content = fs.readFileSync('1.txt', 'utf-8');
const lines = content.split('\n');

// 提取数据（简化版逻辑）
// 找到右手数据列
const header = lines[0].split('\t');
let xIdx = -1, yIdx = -1, zIdx = -1;
let vxIdx = -1, vyIdx = -1, vzIdx = -1, vIdx = -1;

// 使用之前检测到的列索引
xIdx = 409; yIdx = 410; zIdx = 411;
// 假设速度列在位置+7的位置（这是标准格式）
vxIdx = xIdx + 7;
vyIdx = yIdx + 7;
vzIdx = zIdx + 7;
vIdx = vxIdx + 3;

console.log(`Using indices: Pos(${xIdx},${yIdx},${zIdx}), Vel(${vxIdx},${vyIdx},${vzIdx}), V(${vIdx})`);

const speeds = [];
const positions = [];
const velocities = [];
const times = [];

for (let i = 2; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    const parts = line.split('\t');
    if (parts.length > 100) {
        const values = parts.map(x => x ? parseFloat(x) : 0.0);
        if (values[0] > 0) {
            // 跳过均匀行（简单判断）
            if (values.length > 50 && Math.abs(values[10] - values[11]) < 0.00001 && Math.abs(values[11] - values[12]) < 0.00001) continue;
            
            times.push(values[0]);
            positions.push([values[xIdx], values[yIdx], values[zIdx]]);
            velocities.push([values[vxIdx], values[vyIdx], values[vzIdx]]);
            speeds.push(values[vIdx]);
        }
    }
}

console.log(`Extracted ${speeds.length} frames.`);

// 运行测试
findReleasePoint({
    speeds,
    positions,
    velocities,
    times
});
