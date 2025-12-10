import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ========== 需要你自己确认 / 可以改的参数 ==========

CSV_FILE = "fc data.csv"      # 你的 Naio 导出的 csv 文件名

# 从 Naio 软件里 Measure Length 得到的 Width / Height（接触段直线）
WIDTH_NM  = 660.2             # 横轴 piezo 位移（nm）
HEIGHT_MV = 744.8             # 纵轴 detector 电压（mV）

SPRING_K_N_PER_M = 0.2        # 悬臂弹簧常数 k_c [N/m]

# 远离样品、没有相互作用的基线区间（索引范围）
BASELINE_RANGE = (0, 200)     # 你之前用大概前 200 个点是 OK 的

# 信号方向：
SIGN_DEFLECTION = 1           # 如果发现 F 整体上下翻转就改成 -1
SIGN_ZP = -1                  # 如果发现曲线左右翻转就改成 +1

# 接触段拟合阈值（只用力比较大的点来拟直线）
CONTACT_MIN_FORCE_NN = 10.0   # nN

# ==================================================


# 1) 读取原始数据：列名是 Z_p（单位 m），第一行是 detector 电压 V
raw = pd.read_csv(CSV_FILE, sep=';')

Zp_raw_m = raw.columns.astype(float)          # [m] piezo position Z_p (Naio 导出的)
V_raw = raw.iloc[0].astype(float).values      # [V] PSD / detector signal

# 2) 用 Naio 手册的做法算 deflection sensitivity（Butt: slope ΔI/ΔZ_p）
#    slope = ΔV / Δz  [V/m]           （接触段直线的斜率）
#    S = 1 / slope    [m/V]           （Z_c = S * V）
slope_V_per_m = (HEIGHT_MV / 1000.0) / (WIDTH_NM * 1e-9)   # [V/m]
S_m_per_V = 1.0 / slope_V_per_m                             # [m/V]
print(f"Deflection sensitivity S = {S_m_per_V * 1e9:.1f} nm/V")

# 3) 基线校正：在远离样品那段让平均电压 = 0，对应 Z_c = 0, F = 0
i0, i1 = BASELINE_RANGE
V0 = V_raw[i0:i1].mean()
V = V_raw - V0

# 4) 电压 -> 悬臂挠度 Z_c -> 力 F（Butt: F = k_c Z_c）
Zc_m = SIGN_DEFLECTION * S_m_per_V * V     # [m]
F_N  = SPRING_K_N_PER_M * Zc_m             # [N]
F_nN = F_N * 1e9                           # [nN]
Zc_nm = Zc_m * 1e9                         # [nm]

# 5) 按 Butt 3.1：用接触段 Z_c(Z_p) 的线性部分拟合，找 Z_c = 0 的交点 Z_p0
mask_contact = F_nN > CONTACT_MIN_FORCE_NN   # 判定“接触段”的点
coef = np.polyfit(Zp_raw_m[mask_contact], Zc_m[mask_contact], 1)
a1, a0 = coef                                # Z_c ≈ a1 * Z_p_raw + a0
Zp_cross_m = -a0 / a1                        # 令 Z_c = 0 时的 Z_p
print(f"Contact/non-contact crossing Zp0 = {Zp_cross_m * 1e6:.3f} µm")

# 6) 重新定义 Z_p：Z_p = 0 在交点；向下撤回（远离 tip）的方向为正
#    （这一点就是你发的 Butt 文里 “Here, Z_p is defined as zero at the point
#     where the two linear parts ... We count Z_p positive if it is retracted away ...”）
Zp_Butt_m = SIGN_ZP * (Zp_raw_m - Zp_cross_m)  # [m]

# 7) 真正的 tip–sample separation：D = Z_p + Z_c（完全照 Butt 的 D 定义）
D_m  = Zp_Butt_m + Zc_m      # [m]
D_nm = D_m * 1e9             # [nm]

# 为了画得顺一点，可以按 D 从小到大排序（物理上是同一条曲线，排序不改变 D=Zp+Zc）
order = np.argsort(D_nm)
D_nm_sorted = D_nm[order]
F_nN_sorted = F_nN[order]

# 8) 把结果存成一个新的 csv，方便你之后在 Origin / Igor 里再处理
out = pd.DataFrame({
    "Zp_raw_m": Zp_raw_m,
    "V_raw_V": V_raw,
    "Zc_nm": Zc_nm,
    "F_nN": F_nN,
    "D_nm": D_nm,
})
out.to_csv("force_vs_D_converted.csv", index=False)
print("Saved converted data to 'force_vs_D_converted.csv'")

# 9) 画出 F(D) 曲线
plt.figure(figsize=(6, 4))
plt.plot(D_nm, F_nN, '.', markersize=2)
plt.axhline(0, color="k", lw=0.5)
plt.xlabel("Tip–sample separation D (nm)")
plt.ylabel("Force F (nN)")
plt.title("Force–distance curve (approach)")
plt.tight_layout()
plt.show()
