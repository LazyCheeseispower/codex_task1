# C 盘与系统资源治理计划

> 状态：低风险与中风险治理已执行，卸载与 MCP 接入待确认。日期：2026-08-08

## 1. 诊断结论

- CPU：Intel Core i5-7300HQ，4 核 4 线程。整机没有单个异常进程，但 ChatGPT 客户端自启动以来累计 CPU 623 秒，约合单核 11.5% 持续占用；`DingTalkCheck` 出现过单核约 59% 的瞬时尖峰，二次采样已消失，属于钉钉定期自检，非持续异常。
- 内存：物理内存 8GB，常驻占用约 7.9GB，长期满载是卡顿主因。
- 磁盘：C 盘剩余 13.98GB / 117.86GB；D 盘剩余 673GB / 931GB。
- 自启项（HKLM Run，精确清单）：
  - `SunloginClient`（向日葵）：建议禁用
  - `MIUI+`：建议禁用
  - `GamingBox`（腾讯电竞盒子）：建议禁用
  - `Launch LCore`（Logitech）：建议禁用
  - `RTHDVCPL` / `RtHDVBg_Dolby`（Realtek 音频）：按需保留
  - `SecurityHealth`（Defender）：保留

结论：问题叠加，包括常驻软件多、内存满载、C 盘紧张、ChatGPT 客户端后台持续占用，以及钉钉等软件的周期性自检尖峰。

## 2. C 盘空间分布（深度盘点）

### 可安全清理（预计释放 6GB 以上）

- 剪映 `JianyingPro\User Data\Cache`：3.77GB，纯缓存。
- WPS 旧版本 `kingsoft\WPS Office`：12.1.0.26895 与 12.1.0.28043 两个版本目录共 2.7GB，保留当前版本后可删旧版。
- WPS 插件池 `kingsoft\wps\addons\pool`：2.05GB，删除后会按需重新下载，不影响文档。
- WPS `download` 目录：0.39GB。
- 钉钉日志 `Roaming\DingTalk\log`：0.79GB。
- `Temp` 0.28GB + `npm-cache` 0.87GB + Chrome 缓存 0.19GB + Edge 缓存 0.04GB + Windows 更新缓存 0.04GB：合计约 1.5GB。

### 需要用户确认

- `hiberfil.sys`：3.16GB，关闭休眠可释放，但会失去休眠功能（睡眠不受影响）。
- `pagefile.sys`：8.71GB，不建议直接删；若加内存条可降低依赖。
- 钉钉账号数据 `Roaming\DingTalk\3609736397_v2`：2.47GB，可能是聊天图片/文件，保留。
- 腾讯系数据：QQ 1.1GB、微信 1.02GB、腾讯会议 0.92GB，属于用户数据，保留。
- WPS 云文档/用户数据：保留。
- 剪映 `Cloud files` 0.38GB：保留。

### 软件卸载候选

- NI/LabVIEW 2018 组件：几十条，确认不再做 NI 硬件开发后整组卸载。
- 游戏类：Steam、WeGame、LOL、PUBG、怪物猎人、MuMu 模拟器12、中国式家长、英雄黄昏、德州扑克、Unnamed Space Idle。
- 小米全家桶：MIUI+、小米同步、小米游戏盒子、MiService、MiLanCenter。
- 其他：360压缩、迅雷、迅雷影音、ToDesk、向日葵、Allavsoft、外星仔加速器、HI-TECH C 编译器、uVision2。

## 3. 分阶段执行计划

### 阶段 1：低风险清理（预计释放 6GB 左右）

1. 剪映缓存 3.77GB。
2. WPS 旧版本目录 2.7GB（保留当前版本）。
3. TEMP + npm-cache + 浏览器缓存 + Windows 更新缓存 + 钉钉日志，约 1.5GB。

### 阶段 2：中风险治理

1. 禁用自启项：向日葵、MIUI+、GamingBox、Logitech。
2. 关闭休眠释放 3.16GB（若同意）。
3. 卸载确认不用的软件（见软件卸载候选）。
4. Downloads 约 3GB 大文件删除或迁移到 D 盘。

### 阶段 3：开源工具接入

MCP：

- `CursorTouch/Windows-MCP`（6.7k star，MIT）：Windows 控制与监控。
- `seekrays/mcp-monitor`（91 star，Apache-2.0）：CPU/内存/磁盘指标。

软件：

- `BCUninstaller/Bulk-Crap-Uninstaller`（20.6k star）：批量卸载残留。
- `bleachbit/bleachbit`（6.5k star）：系统清理。
- `windirstat/windirstat`（3.8k star）：磁盘占用可视化。
- `henrypp/memreduct`（10.1k star）：内存监控与自动释放。
- `tbillington/kondo`（2.4k star）：项目依赖与构建产物清理。

接入原则：MCP 按需启用，避免进一步占满 8GB 内存。

### 阶段 4：验证与固化

- 清理前后各跑一次 `system-monitor.ps1` 对比 CPU/内存。
- 记录 C 盘剩余空间前后对比。
- 将最终方案、常用命令和资源基线更新到 `AGENTS.md`。

## 4. 待确认清单

- [x] 阶段 1 低风险清理（剪映缓存、WPS 旧版、TEMP/npm/浏览器缓存）：已执行，C 盘 +9.82GB
- [x] 关闭休眠释放 3.16GB：已执行，`powercfg /h off`
- [x] Downloads 大文件迁移：已迁移 2.55GB 到 `D:\Downloads_archive\2026-08-08`，未删除
- [x] 禁用向日葵、MIUI+、GamingBox、Logitech 自启：已执行，备份在 `.codex/outputs/*.reg`
- [ ] 是否确认不再做 NI 硬件开发，允许卸载 LabVIEW 2018 组件？
- [ ] 游戏与小米全家桶中，哪些保留？
- [ ] 是否接入 Windows-MCP / mcp-monitor？哪些工具需要安装？

## 5. 执行记录（2026-08-08 20:23）

- 阶段 1 清理：C 盘 12.52 -> 22.34 GB（+9.82GB），含剪映缓存 3.86GB、WPS 旧版 1.39GB、WPS 插件池 2.10GB、钉钉日志 0.81GB、TEMP 0.29GB、npm-cache 0.89GB、浏览器缓存 0.26GB、Windows 更新缓存 0.04GB。
- 关闭休眠：hiberfil.sys（约 3.16GB）已移除。
- Downloads 迁移：17 项共 2.55GB 移至 `D:\Downloads_archive\2026-08-08`，文档与存档文件保留在 Downloads。
- 自启项：向日葵、MIUI+、GamingBox、Logitech 已禁用；Run 键仅剩 SecurityHealth、Realtek 音频。
- 清理后：C 盘 32.77GB，D 盘 670GB；内存采样约 7.15GB（371 进程）。
- 软件清单：完整 414 项已导出到 `.codex/outputs/installed-apps.csv`；卸载候选重点为 英雄联盟 8.37GB、NI/LabVIEW 组件约几十条、QQ 1GB、小米同步 197MB、Allavsoft 130MB、迅雷/ToDesk/360压缩/游戏类等。

## 6. 卸载执行记录（2026-08-08 20:57）

- 已确认计划 13 项（用户要求保留 Steam 客户端、德州扑克、QQ、ToDesk、360压缩 后生成）。
- 执行前 C 盘 34.67GB / D 盘 670.46GB；执行后 C 盘 34.95GB / D 盘 687.08GB。
- 卸载成功并清理注册表：Allavsoft、Logitech 游戏软件、MuMu 模拟器 12、外星仔加速器、迅雷影音。
- 卸载器返回成功但注册表残留，目录已归档至 `D:\uninstall-backup\2026-08-08`：WeGame（193MB）、腾讯会议（1.3MB，仍被占用待重试）、MuMu Player 12、迅雷影音、ETAlien Booster。
- Steam 游戏需在 Steam 客户端内点击确认：Monster Hunter: World、Unnamed Space Idle、英雄黄昏（英雄黄昏 manifest 已消失）。
- 英雄联盟目录已删除，但注册表卸载项仍存在（残留）；小米同步 msiexec 返回 1619（安装包缺失），注册表项保留。
- 保留项确认：Steam 客户端、德州扑克 Pokerist、QQ、ToDesk、360压缩、PUBG（未列入卸载计划）。
- 复查：C 盘 35.27GB / D 盘 708.58GB；可用内存约 1.2GB，CPU 无单点异常进程（ChatGPT 客户端累计 CPU 最高，约 1338s）。
