# Reverse1999Roster 项目实例

这是本 Skill 的来源项目实例，核实于 2026-10-29。通用流程见其他 reference；新任务的实际源码与状态文档优先于此快照。

## 产品与架构

五个 STS2 原生职业下选择《重返未来：1999》角色形象，保留职业牌组、数值、伤害、RNG、动作顺序和原生存档格式。角色归属按机制 50%、战斗方式 30%、主题气质 20% 比较；这是该项目设计选择。

1.5.2 已交付 78 位，其中原作当时配置的六星共 74 位。未锈铠与苏芙比内置完整模板，其余 76 位走公共档案与表现系统；八位 Spine 动态立绘、68 位 Cubism、2642 段英文语音。角色 ID、数量和排序每轮以 `config/characters.json` 为准。

| 权威路径 | 内容 |
| --- | --- |
| `src/Reverse1999/Reverse1999Roster.json` | Mod ID、版本、最低游戏版本、依赖 |
| `src/Reverse1999/Bridge/` | C#／Harmony 原生桥接 |
| `src/Reverse1999/Resources/R1999/` | 模型、档案、语音、字幕及场景 GDScript |
| `config/characters.json` | 角色目录源，职业字段为 `classes` |
| `config/*sources.json`、`assets.lock.json` | 来源、ID、Git blob、哈希 |
| `patches/` | 两套固定模板的演出／生命周期修复 |
| `dist/build.json`、`work/acceptance-<version>.json` | 构建文件哈希与对应版本验收 |
| `docs/PROJECT.md`、`DEVELOPMENT.md`、`STATUS.md` | 架构、操作、当前交付状态 |

表现设置为 `reverse1999_roster.cfg`，逐局／逐玩家快照为 `reverse1999_runs.json`；不是原生对局文件。`RunCosmetics`／`SkinLedger` 冻结外观，`SkinNetwork` 用 RitsuLib Sidecar 和传输层确认的发送者。

正式战斗、`VisualOnly` 过场、商店、篝火、续局、最终结算分别管理演员。商店使用正常比例立绘，篝火／战斗使用既有 Q 版；退出清理不能互相抢演员。两模板、Spine 和 Cubism 的加载与绘制策略按实际资源保留。

选人卡 132×195。字幕复用模板的 `ScreenSubtitle`，中文上、英文下，32／24 号字体、遮罩和逻辑画布缩放；不要为新角色另造一套视觉系统。档案五页为封面、语音、单品、文化、启程。

选人最多缓存最近六套公共档案；Spine 为 12 项／128 MiB 估计贴图预算，单实例语音为 8 段／8 MiB 压缩数据预算。活跃资源引用与缓存引用分离。

## 工具与构建

当前实测基线：macOS ARM64、public-beta v0.111.0、.NET 9.0.319、Godot 4.5.1，gd_cubism v0.9.1 与 Cubism Native 5 R1。本地 `tools/build.py` 内含平台路径，迁移机器前核对。

在项目根目录：

```sh
.tools/py/bin/python tools/fetch_assets.py
.tools/py/bin/python tools/prepare_fidelity.py
.tools/py/bin/python tools/build_native.py
.tools/py/bin/python tools/build.py
```

前三步用于首次准备或输入变化；普通代码修改通常从 build.py 开始。`.tools/`、`vendor/`、下载素材、`work/`、`dist/` 和 `backups/` 默认不入 Git；它们也不是独立源码项目。

`config/legacy_sources.json` 固定未锈铠 0.5.15、苏芙比 0.6.9 的 PCK／DLL／manifest 输入。构建从 `vendor/legacy/` 读这些输入并按补丁整合，不直接读取或改写当前工坊原包。

外部运行前置仅 `STS2-RitsuLib >= 0.6.10`，其数字工坊 ID 为 **3747602295**。原工坊未锈铠 **3825224241**、苏芙比 **3823298265** 已被内置，应在整合包运行时禁用，不列为新的 Required Items。

## 验证入口

```sh
.tools/py/bin/python tools/run_qa.py
DOTNET_ROOT="$PWD/.tools/dotnet" .tools/dotnet/dotnet run --project tests/State/StateTests.csproj -- work/state-qa-results.json
.tools/py/bin/python tools/render_qa.py
.tools/py/bin/python tools/render_battle_qa.py
.tools/py/bin/python tools/render_merchant_qa.py
.tools/py/bin/python tools/render_merchant_qa.py --renderer mobile
.tools/py/bin/python tools/render_resume_qa.py
.tools/py/bin/python tools/render_refraction_qa.py
.tools/py/bin/python tools/render_refraction_qa.py --renderer mobile
```

其他按改动选取的入口见项目开发指南，包括档案／头像／字幕、选人窗口组合、眼部、苏芙比投毒、公共角色黑块和原生桥接。`run_runtime_qa.py` 会临时安装 QA Mod 并启动真实游戏，正常退出用户游戏并采集最新数据基线后才能执行。

1.5.2 的原生专项 48 项、完整 2080 项，16 状态和全目录独立引擎通过；11 个安装文件逐项一致。转场优化复用原生资源队列，让职业加载与淡出重叠，并冻结选人表现。该性能 fixture 在建局前拦截，完整手动流程、双机器 Steam 联机／重连和完整通关分别按实测记录。

## 打包与安装

1.5.2 原始交付 ZIP 的 SHA-256 为 `d36ed6b22361c2caf28ff877f09d6047ca323f556303627255dc8e43593d73c7`，含 11 个 runtime 文件。本轮增加发行说明的发布 ZIP 使用新的校验值，DLL／PCK 保持上述验收版本。

打包从 build.json 的精确清单取文件；目录里可能有同步产生的 `Reverse1999Roster 2.pck` 等副本，不删除也不纳入新包。

安装使用 `.tools/py/bin/python tools/install.py`，门槛为与本次文件哈希绑定的独立引擎、状态、战斗和两条折射检查。安装前正常退出游戏，备份旧 Mod／相关设置，禁用原两工坊模板，逐文件读回。原生存档快照单独保存。

1.5.2 安装前的 1.5.1 备份是 `backups/20261029-080433`，恢复入口是 `tools/install.py --restore <核实后的备份目录>`。未来版本不能照抄该备份作为当前回退对象。

2026-10-29 本次发布范围：原创 Skill 与脚本公开 GitHub，素材 Mod 成品放私有 GitHub Release；Steam 工坊仅生成发布准备材料。完整 Unity 粒子／镜头还原、跨平台包、真实双机和完整通关不由本次打包自动取得验收。
