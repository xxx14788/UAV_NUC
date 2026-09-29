#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2-WB4 bias 可观测性数值实验(合成部分, v3: 锚定+严格一致性)
一致性: a_meas = R^T(a_world - g), g=(0,0,-9.8); 世界真值 P+=Vh+0.5(R a_meas - G)h^2
锚定: P0/Q0 fixed (VINS problem.SetParameterBlockConstant(para_Pose[0]) 语义) ->
      J 删除 state0 P/Q 列再 Schur 掉其余位姿速度 -> bias 信息矩阵
产出: 三激励 x [eig 谱, 一致漂移(acc/gyr/all6)二次型, 零空间维数]
"""
import numpy as np, json

DT = 1.0 / 223.0
N = 10
G = np.array([0.0, 0.0, 9.8])

def rotq(q):
    x, y, z, w = q
    return np.array([
        [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])

def qmul(a, b):
    av, aw = a[:3], a[3]; bv, bw = b[:3], b[3]
    return np.r_[aw*bv + bw*av + np.cross(av, bv), aw*bw - np.dot(av, bv)]

def expq(w):
    th = np.linalg.norm(w)
    if th < 1e-14: return np.r_[0.5*w, 1.0]
    ax = w/th; return np.r_[ax*np.sin(0.5*th), np.cos(0.5*th)]

def qnorm(q): return q/np.linalg.norm(q)
def qconj(q): return np.r_[-q[:3], q[3]]

def step_integrate(ak, wk, h, dp, dv, dq, Qw, P, V):
    """one sub-step, preint(body) & world-truth simultaneously, VINS mid-point form"""
    q_half_b = qnorm(qmul(dq, expq(0.5*wk*h)))
    un_acc_b = rotq(q_half_b) @ ak
    dp = dp + dv*h + 0.5*un_acc_b*h*h
    dv = dv + un_acc_b*h
    dq = qnorm(qmul(expq(wk*h), dq))
    q_half_w = qnorm(qmul(Qw, expq(0.5*wk*h)))
    acc_w = rotq(q_half_w) @ ak - G
    P = P + V*h + 0.5*acc_w*h*h
    V = V + acc_w*h
    Qw = qnorm(qmul(Qw, expq(wk*h)))
    return dp, dv, dq, Qw, P, V

def scen(kind, n):
    t = np.arange(n)*DT
    if kind == "static":
        a = np.tile([0.0, 0.0, 9.8], (n, 1)); w = np.zeros((n, 3))
    elif kind == "const_acc":
        a = np.tile([1.5, 0.0, 9.8], (n, 1)); w = np.zeros((n, 3))
    elif kind == "maneuver":
        man = np.c_[3.0*np.sin(2*np.pi*0.5*t), 2.0*np.cos(2*np.pi*0.7*t), 1.0*np.sin(2*np.pi*1.1*t)]
        a = man + np.tile([0.0, 0.0, 9.8], (n, 1))
        w = np.c_[0.8*np.sin(2*np.pi*0.3*t+0.3), 0.6*np.cos(2*np.pi*0.45*t), 0.5*np.sin(2*np.pi*0.9*t+1.0)]
    return a, w

SUB = 2
def build(kind):
    a, w = scen(kind, 2*N+4)
    st = [dict(P=np.zeros(3), Q=np.array([0., 0., 0., 1.]), V=np.zeros(3),
               Ba=np.zeros(3), Bg=np.zeros(3))]
    pre = []
    for i in range(N):
        P, Q, V = st[-1]["P"].copy(), st[-1]["Q"].copy(), st[-1]["V"].copy()
        dp = np.zeros(3); dv = np.zeros(3); dq = np.array([0., 0., 0., 1.])
        h = DT/SUB
        for k in range(SUB):
            dp, dv, dq, Q, P, V = step_integrate(a[2*i+k], w[2*i+k], h, dp, dv, dq, Q, P, V)
        pre.append((dp, dv, dq))
        st.append(dict(P=P, Q=Q, V=V, Ba=np.zeros(3), Bg=np.zeros(3)))
    return st, pre

def residual(st, pre):
    r = []
    for i in range(N):
        si, sj, (dp, dv, dq) = st[i], st[i+1], pre[i]
        Ri = rotq(si["Q"]).T
        dp_dba = -0.5*DT*DT*np.eye(3); dv_dba = -DT*np.eye(3)
        cor_dp = dp + dp_dba@si["Ba"]
        cor_dv = dv + dv_dba@si["Ba"]
        r_p = Ri@(0.5*G*DT*DT + sj["P"] - si["P"]) - cor_dp
        r_v = Ri@(sj["V"] - si["V"]) + Ri@G*DT - cor_dv
        q_rel = qmul(qconj(dq), qmul(qconj(si["Q"]), sj["Q"]))
        s = 1.0 if q_rel[3] >= 0 else -1.0
        r.append(np.r_[r_p, r_v, 2*s*q_rel[:3]])
    return np.concatenate(r)

def pack(st):
    x = []
    for s in st:
        x += [s["P"], s["Q"][:3], s["V"], s["Ba"], s["Bg"]]
    return np.concatenate(x)

def unpack(x):
    st, k = [], 0
    for i in range(N+1):
        qv = x[k+3:k+6]
        st.append(dict(P=x[k:k+3].copy(),
                       Q=qnorm(np.r_[qv, np.sqrt(max(0.0, 1-np.dot(qv, qv)))]),
                       V=x[k+6:k+9].copy(), Ba=x[k+9:k+12].copy(), Bg=x[k+12:k+15].copy()))
        k += 15
    return st

print("=== T2-WB4 synthetic bias observability v3 (IMU window N=%d dt=%.5f, P0/Q0 anchored) ===" % (N, DT))
results = {}
for kind in ("static", "const_acc", "maneuver"):
    st, pre = build(kind)
    x0 = pack(st)
    r0 = residual(unpack(x0), pre)
    eps = 1e-6
    J = np.zeros((r0.size, x0.size))
    for j in range(x0.size):
        dx = np.zeros(x0.size); dx[j] = eps
        J[:, j] = (residual(unpack(x0+dx), pre) - residual(unpack(x0-dx), pre))/(2*eps)
    # anchor: drop state0 P/Q cols (SetParameterBlockConstant equivalent)
    anchored = set(range(0, 6))
    cols = [j for j in range(x0.size) if j not in anchored]
    J = J[:, cols]
    H = J.T @ J
    bias_local, other_local = [], []
    for cj, j in enumerate(cols):
        if 15*(j//15)+9 <= j <= 15*(j//15)+14:
            bias_local.append(cj)
        else:
            other_local.append(cj)
    Hbb = H[np.ix_(bias_local, bias_local)]
    Hbo = H[np.ix_(bias_local, other_local)]
    Hoo = H[np.ix_(other_local, other_local)]
    S = Hbb - Hbo @ np.linalg.pinv(Hoo, rcond=1e-9) @ Hbo.T
    S = 0.5*(S+S.T)
    ev = np.linalg.eigvalsh(S)[::-1]
    n_states_free = len([j for j in cols if 15*(j//15)+9 <= j <= 15*(j//15)+14]) // 6
    d_all = np.concatenate([np.ones(6) for _ in range(n_states_free)])
    d_acc = np.concatenate([np.r_[np.ones(3), np.zeros(3)] for _ in range(n_states_free)])
    d_gyr = np.concatenate([np.r_[np.zeros(3), np.ones(3)] for _ in range(n_states_free)])
    q = lambda d: float(d @ S @ d)
    nnull = int(np.sum(ev < 1e-9*max(ev[0], 1e-30)))
    print("\n[%s] |r0|=%.3g (should be ~0)" % (kind, np.linalg.norm(r0)))
    print("  Schur bias eig: max=%.4g min=%.4g  null-dim(<=1e-9*max)=%d/%d" % (ev[0], ev[-1], nnull, ev.size))
    print("  consistent-drift qd: all6=%.4g acc=%.4g gyr=%.4g (0 => free sink dir)" % (q(d_all), q(d_acc), q(d_gyr)))
    print("  6 smallest eigvals: %s" % " ".join("%.3g" % v for v in ev[-6:]))
    results[kind] = dict(eig=ev.tolist(), qd_all=q(d_all), qd_acc=q(d_acc), qd_gyr=q(d_gyr), nnull=nnull)

json.dump(results, open("/home/uav/sitl_sim/t2_results/wb4_bias_observability_synthetic.json", "w"), indent=1)
print("\nsaved -> ~/sitl_sim/t2_results/wb4_bias_observability_synthetic.json")

# ---- v4: vision-anchored variant (landmarks restore bias observability) ----
rng = np.random.default_rng(11)
LM = 10
LMS = np.c_[rng.uniform(-8, 8, (LM, 2)), rng.uniform(2, 30, LM)]  # world landmarks, forward 2-30m

def vis_residual(st, lm_obs):
    r = []
    for i, obs in enumerate(lm_obs):
        R = rotq(st[i]["Q"]); P = st[i]["P"]
        for lmi, uv in obs:
            Xb = R.T @ (LMS[lmi] - P)
            r.append(np.array([Xb[0]/Xb[2], Xb[1]/Xb[2]]) - uv)
    return np.concatenate(r)

def build_vis_obs(st):
    lm_obs = []
    for i in range(N+1):
        R = rotq(st[i]["Q"]); P = st[i]["P"]
        obs = []
        for lmi in range(LM):
            Xb = R.T @ (LMS[lmi] - P)
            if Xb[2] > 0.5:
                obs.append((lmi, np.array([Xb[0]/Xb[2], Xb[1]/Xb[2]])))
        lm_obs.append(obs)
    return lm_obs

print("\n=== v4: with vision anchors (%d landmarks) ===" % LM)
res_v = {}
for kind in ("static", "const_acc", "maneuver"):
    st, pre = build(kind)
    lm_obs = build_vis_obs(st)
    x0 = pack(st)
    def res_full(x):
        s = unpack(x)
        return np.concatenate([residual(s, pre), vis_residual(s, lm_obs)])
    r0 = res_full(x0)
    eps = 1e-6
    J = np.zeros((r0.size, x0.size))
    for j in range(x0.size):
        dx = np.zeros(x0.size); dx[j] = eps
        J[:, j] = (res_full(x0+dx) - res_full(x0-dx))/(2*eps)
    anchored = set(range(0, 6))
    cols = [j for j in range(x0.size) if j not in anchored]
    J = J[:, cols]
    H = J.T @ J
    bias_local, other_local = [], []
    for cj, j in enumerate(cols):
        if 15*(j//15)+9 <= j <= 15*(j//15)+14: bias_local.append(cj)
        else: other_local.append(cj)
    Hbb = H[np.ix_(bias_local, bias_local)]; Hbo = H[np.ix_(bias_local, other_local)]
    Hoo = H[np.ix_(other_local, other_local)]
    S = Hbb - Hbo @ np.linalg.pinv(Hoo, rcond=1e-9) @ Hbo.T
    S = 0.5*(S+S.T)
    ev = np.linalg.eigvalsh(S)[::-1]
    nst = len(bias_local)//6
    d_all = np.concatenate([np.ones(6) for _ in range(nst)])
    d_acc = np.concatenate([np.r_[np.ones(3), np.zeros(3)] for _ in range(nst)])
    d_gyr = np.concatenate([np.r_[np.zeros(3), np.ones(3)] for _ in range(nst)])
    q = lambda d: float(d @ S @ d)
    nnull = int(np.sum(ev < 1e-12*ev[0])) if ev[0] > 0 else ev.size
    print("\n[%s+vis] |r0|=%.3g  eig: max=%.4g min=%.4g null=%d/%d" % (kind, np.linalg.norm(r0), ev[0], ev[-1], nnull, ev.size))
    print("  consistent-drift qd: all6=%.4g acc=%.4g gyr=%.4g" % (q(d_all), q(d_acc), q(d_gyr)))
    print("  6 smallest: %s" % " ".join("%.3g" % v for v in ev[-6:]))
    res_v[kind] = dict(eig=ev.tolist(), qd_all=q(d_all), qd_acc=q(d_acc), qd_gyr=q(d_gyr), nnull=nnull)
json.dump(res_v, open("/home/uav/sitl_sim/t2_results/wb4_bias_observability_vision.json", "w"), indent=1)
print("\nsaved -> wb4_bias_observability_vision.json")
